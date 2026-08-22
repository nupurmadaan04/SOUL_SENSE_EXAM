"""
Migration Checksum Registry

Enforces migration file integrity by validating checksums before execution.
Prevents accidental or malicious modification of migration files.

Usage:
    registry = ChecksumRegistry()
    result = registry.verify_all_migrations()
    if not result.passed:
        raise RuntimeError(f"Migration integrity check failed: {result}")
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MigrationChecksum:
    """Checksum record for a single migration."""
    migration_id: str
    filename: str
    content_hash: str
    file_size: int
    created_at: str
    last_verified: str
    status: str = "valid"  # valid, modified, missing

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class RegistryRecord:
    """Complete migration registry snapshot."""
    registry_version: str
    created_at: str
    last_updated: str
    migrations: List[MigrationChecksum] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "registry_version": self.registry_version,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "migrations": [m.to_dict() for m in self.migrations]
        }

    @classmethod
    def from_dict(cls, data: Dict):
        migrations = [
            MigrationChecksum.from_dict(m) for m in data.get("migrations", [])
        ]
        return cls(
            registry_version=data.get("registry_version", "1.0"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            migrations=migrations
        )


@dataclass
class RegistryValidationResult:
    """Result of registry validation."""
    passed: bool
    total_migrations: int
    valid_count: int
    modified_count: int
    missing_count: int
    modified_migrations: List[str] = field(default_factory=list)
    missing_migrations: List[str] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class ChecksumRegistry:
    """Manage migration file checksums."""

    REGISTRY_VERSION = "1.0"
    REGISTRY_FILENAME = "migration_registry.json"

    def __init__(self, migrations_dir: str = None):
        """
        Initialize registry.

        Args:
            migrations_dir: Path to migrations directory. Defaults to project root/migrations
        """
        if migrations_dir is None:
            project_root = Path(__file__).parent.parent.parent
            migrations_dir = str(project_root / "migrations")

        self.migrations_dir = Path(migrations_dir)
        self.registry_path = self.migrations_dir / self.REGISTRY_FILENAME
        self.versions_dir = self.migrations_dir / "versions"
        self.logger = logger

    def generate_checksum(self, file_path: str) -> str:
        """Generate SHA-256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_migration_id(self, filename: str) -> str:
        """Extract migration ID from filename (e.g., 'abc123_desc.py' -> 'abc123')."""
        return filename.replace(".py", "").split("_")[0]

    def compute_all_checksums(self) -> Dict[str, MigrationChecksum]:
        """Compute checksums for all migration files."""
        checksums = {}

        if not self.versions_dir.exists():
            self.logger.warning(f"Versions directory not found: {self.versions_dir}")
            return checksums

        now = datetime.utcnow().isoformat() + "Z"

        for migration_file in sorted(self.versions_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue

            try:
                file_path = str(migration_file)
                content_hash = self.generate_checksum(file_path)
                file_size = migration_file.stat().st_size
                migration_id = self._get_migration_id(migration_file.name)

                checksums[migration_id] = MigrationChecksum(
                    migration_id=migration_id,
                    filename=migration_file.name,
                    content_hash=content_hash,
                    file_size=file_size,
                    created_at=now,
                    last_verified=now,
                    status="valid"
                )
            except Exception as e:
                self.logger.error(f"Error computing checksum for {migration_file.name}: {e}")

        return checksums

    def save_registry(self, checksums: Dict[str, MigrationChecksum]) -> bool:
        """Save checksums to registry file."""
        try:
            now = datetime.utcnow().isoformat() + "Z"
            record = RegistryRecord(
                registry_version=self.REGISTRY_VERSION,
                created_at=now,
                last_updated=now,
                migrations=list(checksums.values())
            )

            with open(self.registry_path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)

            self.logger.info(f"Registry saved: {self.registry_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
            return False

    def load_registry(self) -> Optional[RegistryRecord]:
        """Load registry from file."""
        try:
            if not self.registry_path.exists():
                self.logger.warning(f"Registry file not found: {self.registry_path}")
                return None

            with open(self.registry_path, "r") as f:
                data = json.load(f)
                return RegistryRecord.from_dict(data)
        except json.JSONDecodeError as e:
            self.logger.error(f"Corrupted registry file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
            return None

    def verify_all_migrations(self) -> RegistryValidationResult:
        """Verify all migration files against registry."""
        registry = self.load_registry()
        current_checksums = self.compute_all_checksums()

        if registry is None:
            self.logger.warning("Registry not found. Creating new one.")
            self.save_registry(current_checksums)
            return RegistryValidationResult(
                passed=True,
                total_migrations=len(current_checksums),
                valid_count=len(current_checksums),
                modified_count=0,
                missing_count=0
            )

        # Build lookup maps
        registry_map = {m.migration_id: m for m in registry.migrations}
        current_map = {m.migration_id: m for m in current_checksums.values()}

        modified = []
        missing_in_current = []
        valid_count = 0

        # Check each registered migration
        for migration_id, registered in registry_map.items():
            if migration_id not in current_map:
                missing_in_current.append(registered.filename)
            elif current_map[migration_id].content_hash != registered.content_hash:
                modified.append(registered.filename)
            else:
                valid_count += 1

        # Check for new migrations not in registry
        new_migrations = set(current_map.keys()) - set(registry_map.keys())

        passed = len(modified) == 0 and len(missing_in_current) == 0
        total = len(registry_map) + len(new_migrations)

        result = RegistryValidationResult(
            passed=passed,
            total_migrations=total,
            valid_count=valid_count,
            modified_count=len(modified),
            missing_count=len(missing_in_current),
            modified_migrations=modified,
            missing_migrations=missing_in_current
        )

        if not passed:
            result.error_message = (
                f"Migration integrity check failed: "
                f"{len(modified)} modified, {len(missing_in_current)} missing"
            )
            self.logger.error(result.error_message)
            self.logger.error(f"Modified: {modified}")
            self.logger.error(f"Missing: {missing_in_current}")

        return result

    def register_migration(self, migration_filename: str) -> bool:
        """Register a new migration."""
        try:
            if not self.versions_dir.exists():
                self.logger.error(f"Versions directory not found: {self.versions_dir}")
                return False

            migration_path = self.versions_dir / migration_filename
            if not migration_path.exists():
                self.logger.error(f"Migration file not found: {migration_path}")
                return False

            checksums = self.compute_all_checksums()
            return self.save_registry(checksums)
        except Exception as e:
            self.logger.error(f"Failed to register migration: {e}")
            return False

    def detect_modified_migrations(self) -> List[str]:
        """Detect which migrations have been modified."""
        result = self.verify_all_migrations()
        return result.modified_migrations + result.missing_migrations
