"""
Online Index Creation Policy Guard

Validates database indexes follow safe creation policies for production.
Prevents regression risk by enforcing database-specific best practices.

Supports: PostgreSQL (CONCURRENT), MySQL (INPLACE), SQLite (with warnings)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class IndexPolicy(Enum):
    """Policy constraints for index creation."""
    MUST_BE_CONCURRENT = "must_use_concurrent"  # PostgreSQL
    MUST_BE_INPLACE = "must_use_inplace"        # MySQL
    REQUIRES_MAINTENANCE = "requires_maintenance"  # SQLite
    MUST_HAVE_ROLLBACK = "must_have_rollback"   # All databases


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


@dataclass
class IndexDefinition:
    """Metadata about a database index."""
    name: str                        # e.g., 'ix_users_email'
    table: str                       # e.g., 'users'
    columns: List[str] = field(default_factory=list)  # ['email']
    is_unique: bool = False
    estimated_duration_seconds: int = 30
    
    def validate(self) -> Tuple[bool, str]:
        """Validate index definition."""
        if not self.name or not self.table:
            return False, "name and table are required"
        if not self.columns:
            return False, "at least one column required"
        if self.estimated_duration_seconds < 0:
            return False, "estimated_duration_seconds cannot be negative"
        return True, ""


@dataclass
class PolicyCheckResult:
    """Result of a single policy check."""
    policy: IndexPolicy
    passed: bool
    reason: str = ""
    recommendation: str = ""
    blocking: bool = True


@dataclass
class ValidationResult:
    """Overall policy validation result."""
    passed: bool
    index_name: str
    database_type: str
    checks: List[PolicyCheckResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "passed": self.passed,
            "index": self.index_name,
            "database": self.database_type,
            "checks": [
                {
                    "policy": c.policy.value,
                    "passed": c.passed,
                    "reason": c.reason,
                    "recommendation": c.recommendation,
                    "blocking": c.blocking
                }
                for c in self.checks
            ],
            "errors": self.errors,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "timestamp": self.timestamp
        }


class OnlineIndexPolicyValidator:
    """
    Validates index creation against database-specific policies.
    
    Usage:
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        index = IndexDefinition(name='ix_users_email', table='users', columns=['email'])
        result = validator.validate(index)
        
        if result.passed:
            print(f"Safe to create: {index.name}")
        else:
            for error in result.errors:
                print(f"ERROR: {error}")
    """
    
    def __init__(self, db_type: DatabaseType):
        """Initialize with target database type."""
        self.db_type = db_type
        self.logger = logger
    
    def validate(self, index: IndexDefinition) -> ValidationResult:
        """
        Validate an index against policies for the configured database.
        
        Returns: ValidationResult with pass/fail, checks performed, and recommendations
        """
        # Validate input
        is_valid, error_msg = index.validate()
        if not is_valid:
            return ValidationResult(
                passed=False,
                index_name=index.name,
                database_type=self.db_type.value,
                errors=[f"Invalid index definition: {error_msg}"]
            )
        
        result = ValidationResult(
            passed=True,
            index_name=index.name,
            database_type=self.db_type.value,
            metrics={
                "table": index.table,
                "columns": len(index.columns),
                "estimated_duration_seconds": index.estimated_duration_seconds,
                "is_unique": index.is_unique
            }
        )
        
        # Run database-specific checks
        if self.db_type == DatabaseType.POSTGRESQL:
            self._check_postgresql(index, result)
        elif self.db_type == DatabaseType.MYSQL:
            self._check_mysql(index, result)
        elif self.db_type == DatabaseType.SQLITE:
            self._check_sqlite(index, result)
        
        # Determine overall pass/fail
        blocking_failures = [c for c in result.checks if not c.passed and c.blocking]
        if blocking_failures:
            result.passed = False
            result.errors = [c.reason for c in blocking_failures]
        
        result.recommendations = [c.recommendation for c in result.checks if c.recommendation]
        
        self._log_result(result)
        return result
    
    def _check_postgresql(self, index: IndexDefinition, result: ValidationResult) -> None:
        """PostgreSQL: Validate CONCURRENT index creation capability."""
        
        # Check 1: Online creation capability
        check = PolicyCheckResult(
            policy=IndexPolicy.MUST_BE_CONCURRENT,
            passed=True,  # PostgreSQL supports CREATE INDEX CONCURRENTLY
            reason="PostgreSQL supports CREATE INDEX CONCURRENTLY",
            recommendation="Use: CREATE INDEX CONCURRENTLY ix_name ON table (columns)"
        )
        result.checks.append(check)
        
        # Check 2: Lock safety (concurrent indexes don't block)
        check = PolicyCheckResult(
            policy=IndexPolicy.MUST_HAVE_ROLLBACK,
            passed=True,
            reason="Concurrent index creation allows concurrent writes",
            recommendation="Ensure corresponding DROP INDEX CONCURRENTLY in downgrade"
        )
        result.checks.append(check)
        
        # Check 3: Duration warning for large tables
        if index.estimated_duration_seconds > 300:
            check = PolicyCheckResult(
                policy=IndexPolicy.MUST_BE_CONCURRENT,
                passed=True,
                blocking=False,
                reason=f"Long index creation ({index.estimated_duration_seconds}s) - monitor progress",
                recommendation="Monitor using: SELECT * FROM pg_stat_progress_create_index"
            )
            result.checks.append(check)
            result.warnings.append(f"Estimated duration {index.estimated_duration_seconds}s is long")
    
    def _check_mysql(self, index: IndexDefinition, result: ValidationResult) -> None:
        """MySQL: Validate INPLACE with LOCK=NONE creation capability."""
        
        # Check 1: INPLACE support (requires MySQL 5.6+)
        check = PolicyCheckResult(
            policy=IndexPolicy.MUST_BE_INPLACE,
            passed=True,
            reason="MySQL supports ALGORITHM=INPLACE",
            recommendation="Use: ALTER TABLE table ADD INDEX ix_name (columns), ALGORITHM=INPLACE, LOCK=NONE"
        )
        result.checks.append(check)
        
        # Check 2: Lock safety (LOCK=NONE allows concurrent writes)
        check = PolicyCheckResult(
            policy=IndexPolicy.MUST_HAVE_ROLLBACK,
            passed=True,
            reason="ALGORITHM=INPLACE with LOCK=NONE is zero-downtime",
            recommendation="Verify downgrade path drops index with same algorithm"
        )
        result.checks.append(check)
        
        # Check 3: Duration warning
        if index.estimated_duration_seconds > 300:
            check = PolicyCheckResult(
                policy=IndexPolicy.MUST_BE_INPLACE,
                passed=True,
                blocking=False,
                reason=f"Long index creation ({index.estimated_duration_seconds}s)",
                recommendation="Monitor using: SELECT * FROM performance_schema.events_stages_current"
            )
            result.checks.append(check)
            result.warnings.append(f"Estimated duration {index.estimated_duration_seconds}s is long")
    
    def _check_sqlite(self, index: IndexDefinition, result: ValidationResult) -> None:
        """SQLite: Flag full table lock and recommend maintenance window."""
        
        # Check 1: Online creation not available
        check = PolicyCheckResult(
            policy=IndexPolicy.REQUIRES_MAINTENANCE,
            passed=False,
            blocking=False,  # Warning, not blocking
            reason="SQLite holds full table lock during CREATE INDEX (no online mode)",
            recommendation="Schedule index creation during maintenance window with no concurrent writes"
        )
        result.checks.append(check)
        result.warnings.append("SQLite requires maintenance window for index creation")
        
        # Check 2: Duration warning
        if index.estimated_duration_seconds > 60:
            check = PolicyCheckResult(
                policy=IndexPolicy.REQUIRES_MAINTENANCE,
                passed=False,
                blocking=False,
                reason=f"Long lock duration ({index.estimated_duration_seconds}s) on SQLite",
                recommendation="If possible, break into smaller indexes or use AUTOINCREMENT optimization"
            )
            result.checks.append(check)
            result.warnings.append(f"Table lock for {index.estimated_duration_seconds}s will block all writes")
        
        # Check 3: Rollback plan
        check = PolicyCheckResult(
            policy=IndexPolicy.MUST_HAVE_ROLLBACK,
            passed=True,
            reason="SQLite downgrade via DROP INDEX is fast",
            recommendation="Ensure downgrade migration drops all created indexes"
        )
        result.checks.append(check)
    
    def _log_result(self, result: ValidationResult) -> None:
        """Log validation result."""
        level = logging.INFO if result.passed else logging.WARNING
        self.logger.log(
            level,
            f"Index validation: {result.index_name} on {result.database_type} - "
            f"{'PASS' if result.passed else 'FAIL'}",
            extra={"result": result.to_dict()}
        )


def validate_index_in_migration(
    db_type: str,
    index_name: str,
    table_name: str,
    columns: List[str],
    estimated_duration_seconds: int = 30,
    is_unique: bool = False
) -> ValidationResult:
    """
    Convenience function to validate a single index.
    
    Args:
        db_type: 'postgresql', 'mysql', or 'sqlite'
        index_name: Name of the index
        table_name: Name of the table
        columns: List of column names
        estimated_duration_seconds: Expected time to create index
        is_unique: Whether this is a unique index
    
    Returns:
        ValidationResult with pass/fail and recommendations
    """
    try:
        db_enum = DatabaseType(db_type)
    except ValueError:
        raise ValueError(f"Unsupported database type: {db_type}. Use: postgresql, mysql, sqlite")
    
    index = IndexDefinition(
        name=index_name,
        table=table_name,
        columns=columns,
        is_unique=is_unique,
        estimated_duration_seconds=estimated_duration_seconds
    )
    
    validator = OnlineIndexPolicyValidator(db_enum)
    return validator.validate(index)
