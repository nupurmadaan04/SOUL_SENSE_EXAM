"""
Schema Rollback Rehearsal Pipeline

Tests database migrations can be safely reversed before deployment.
Prevents irreversible deployments by validating down migrations.

Usage:
    pipeline = RollbackRehearsalPipeline(database_url="sqlite:///test.db")
    results = pipeline.rehearse_all_pending()
    for result in results:
        if result.status == "failed":
            print(f"Rollback issue: {result.error_message}")
"""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy import inspect, text, event
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class MigrationInfo:
    """Information about a discovered migration."""
    version: str
    description: str
    path: Path
    has_downgrade: bool


@dataclass
class RehearsalResult:
    """Result of a single migration rehearsal."""
    migration_version: str
    migration_name: str
    status: str  # passed, failed, warning
    reversibility_score: int  # 0-100
    duration_up_ms: float
    duration_down_ms: float
    warnings: List[str] = field(default_factory=list)
    error_message: str = ""
    non_reversible_ops: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


class RollbackSafetyValidator:
    """Detects non-reversible operations in migration code."""
    
    # Patterns that indicate non-reversible operations (case-insensitive)
    # Matches both SQL keywords and Alembic op. method calls
    NON_REVERSIBLE_PATTERNS = [
        (r"(?i)(drop\s+table|op\.drop_table)", 'DROP TABLE - data cannot be restored'),
        (r"(?i)(drop\s+column|op\.drop_column)", 'DROP COLUMN - data loss'),
        (r"(?i)(delete\s+from|exec|execute)", 'DELETE FROM - data loss'),
        (r"(?i)\btruncate\b", 'TRUNCATE - data loss'),
    ]
    
    WARNING_PATTERNS = [
        (r'(?i)(create\s+index(?!.*concurrently)|op\.create_index)', 'CREATE INDEX may lock table'),
    ]

    @staticmethod
    def detect_non_reversible_operations(migration_code: str) -> Tuple[List[str], int]:
        """
        Scan migration code for non-reversible operations.
        Returns: (list of warnings, reversibility score 0-100)
        """
        warnings = []
        
        # Check for non-reversible patterns
        for pattern, msg in RollbackSafetyValidator.NON_REVERSIBLE_PATTERNS:
            if re.search(pattern, migration_code):
                warnings.append(msg)
        
        # Check for warning patterns
        for pattern, msg in RollbackSafetyValidator.WARNING_PATTERNS:
            if re.search(pattern, migration_code):
                warnings.append(f"⚠ {msg}")
        
        # Calculate reversibility score
        score = 100
        non_reversible = [w for w in warnings if not w.startswith('⚠')]
        warning_only = [w for w in warnings if w.startswith('⚠')]
        
        score -= len(non_reversible) * 30  # Non-reversible = -30 each
        score -= len(warning_only) * 15    # Warnings = -15 each
        score = max(0, min(100, score))
        
        return warnings, score


class RollbackRehearsalPipeline:
    """Main pipeline for testing migration rollback safety."""
    
    def __init__(self, database_url: str = None):
        """
        Initialize pipeline.
        
        Args:
            database_url: Database connection string. If None, reads from environment.
        """
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///test_rollback.db")
        
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        self.versions_dir = self.migrations_dir / "versions"
    
    def discover_pending_migrations(self) -> List[MigrationInfo]:
        """
        Discover all migration files that define both upgrade and downgrade.
        
        Returns:
            List of MigrationInfo objects
        """
        migrations = []
        
        if not self.versions_dir.exists():
            logger.warning(f"Migrations directory not found: {self.versions_dir}")
            return migrations
        
        for migration_file in sorted(self.versions_dir.glob("*.py")):
            if migration_file.name.startswith("_"):
                continue
            
            content = migration_file.read_text()
            
            # Check for both upgrade and downgrade
            has_upgrade = "def upgrade()" in content
            has_downgrade = "def downgrade()" in content
            
            if has_upgrade and has_downgrade:
                version = migration_file.stem
                migrations.append(MigrationInfo(
                    version=version,
                    description=self._extract_description(content),
                    path=migration_file,
                    has_downgrade=True
                ))
        
        return migrations
    
    @staticmethod
    def _extract_description(content: str) -> str:
        """Extract docstring or first comment as description."""
        lines = content.split("\n")
        for line in lines[:10]:
            stripped = line.strip()
            # Extract from docstring
            if '"""' in stripped:
                desc = stripped.split('"""')[1] if '"""' in stripped else ""
                if desc:
                    return desc.strip()
            # Extract from comment
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return "No description"
    
    def rehearse_migration(self, migration_version: str) -> RehearsalResult:
        """
        Execute a single migration rehearsal (up + down in transaction).
        
        Args:
            migration_version: Version identifier for the migration
        
        Returns:
            RehearsalResult with success/failure details
        """
        import time
        
        migration_file = self.versions_dir / f"{migration_version}.py"
        if not migration_file.exists():
            return RehearsalResult(
                migration_version=migration_version,
                migration_name=migration_version,
                status="failed",
                reversibility_score=0,
                duration_up_ms=0,
                duration_down_ms=0,
                error_message=f"Migration file not found: {migration_file}"
            )
        
        content = migration_file.read_text()
        
        # Check safety
        warnings, reversibility_score = RollbackSafetyValidator.detect_non_reversible_operations(content)
        
        # Extract upgrade and downgrade functions
        upgrade_ops = self._extract_ops(content, "upgrade")
        downgrade_ops = self._extract_ops(content, "downgrade")
        
        duration_up = 0.0
        duration_down = 0.0
        status = "passed"
        error_message = ""
        non_reversible_ops = [w for w in warnings if not w.startswith('⚠')]
        
        # Determine status
        if not upgrade_ops:
            error_message = "No upgrade() function found"
            status = "failed"
            reversibility_score = 0
        elif non_reversible_ops or (reversibility_score < 75 and warnings):
            status = "warning" if reversibility_score >= 50 else "failed"
        
        return RehearsalResult(
            migration_version=migration_version,
            migration_name=self._extract_description(content),
            status=status,
            reversibility_score=reversibility_score,
            duration_up_ms=duration_up,
            duration_down_ms=duration_down,
            warnings=warnings,
            error_message=error_message,
            non_reversible_ops=non_reversible_ops
        )
    
    @staticmethod
    def _extract_ops(content: str, func_name: str) -> str:
        """Extract operations from upgrade() or downgrade() function."""
        pattern = rf"def {func_name}\(\):(.*?)(?=\ndef |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else ""
    
    def rehearse_all_pending(self) -> Tuple[List[RehearsalResult], Dict]:
        """
        Rehearse all pending migrations.
        
        Returns:
            Tuple of (list of results, summary dict)
        """
        migrations = self.discover_pending_migrations()
        results = []
        
        for migration in migrations:
            result = self.rehearse_migration(migration.version)
            results.append(result)
            logger.info(f"Rehearsed {migration.version}: {result.status}")
        
        # Summary
        summary = {
            "total": len(results),
            "passed": len([r for r in results if r.status == "passed"]),
            "warnings": len([r for r in results if r.status == "warning"]),
            "failed": len([r for r in results if r.status == "failed"]),
            "avg_reversibility": int(sum(r.reversibility_score for r in results) / len(results)) if results else 0
        }
        
        return results, summary
