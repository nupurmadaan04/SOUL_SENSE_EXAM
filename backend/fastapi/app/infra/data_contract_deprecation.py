"""Data contract deprecation tracker for safe database schema evolution."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Severity level for breaking changes."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BreakingChangeType(str, Enum):
    """Types of breaking changes detected."""
    REMOVED_COLUMN = "removed_column"
    TYPE_CHANGE = "type_change"
    CONSTRAINT_TIGHTENED = "constraint_tightened"
    INDEX_REMOVED = "index_removed"
    FOREIGN_KEY_CHANGED = "foreign_key_changed"


@dataclass
class DeprecatedField:
    """Represents a field marked for deprecation."""
    field_name: str
    deprecated_at: str  # ISO format datetime
    removal_target: str  # ISO format datetime
    reason: str
    replacement: Optional[str] = None
    
    def days_until_removal(self) -> int:
        """Calculate days remaining until removal."""
        removal = datetime.fromisoformat(self.removal_target)
        return max(0, (removal - datetime.now()).days)
    
    def is_removal_overdue(self) -> bool:
        """Check if removal date has passed."""
        return self.days_until_removal() <= 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BreakingChange:
    """Represents a detected breaking change."""
    change_type: BreakingChangeType
    field_name: str
    severity: SeverityLevel
    description: str
    old_definition: Optional[str] = None
    new_definition: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.change_type.value,
            "field": self.field_name,
            "severity": self.severity.value,
            "description": self.description,
            "old_definition": self.old_definition,
            "new_definition": self.new_definition,
        }


@dataclass
class DataContract:
    """Contract defining backward compatibility guarantees for a table."""
    table_name: str
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    deprecated_fields: List[DeprecatedField] = field(default_factory=list)
    minimum_retention_period_days: int = 90
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "table_name": self.table_name,
            "version": self.version,
            "created_at": self.created_at,
            "deprecated_fields": [f.to_dict() for f in self.deprecated_fields],
            "minimum_retention_period_days": self.minimum_retention_period_days,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContract":
        """Create from dictionary."""
        deprecated_fields = [
            DeprecatedField(**field_data) 
            for field_data in data.get("deprecated_fields", [])
        ]
        return cls(
            table_name=data["table_name"],
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            deprecated_fields=deprecated_fields,
            minimum_retention_period_days=data.get("minimum_retention_period_days", 90),
        )


@dataclass
class CompatibilityCheckResult:
    """Result of compatibility check."""
    passed: bool
    breaking_changes: List[BreakingChange] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "breaking_changes": [c.to_dict() for c in self.breaking_changes],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class DataContractDeprecationTracker:
    """Tracks and enforces data contract deprecation policies."""
    
    def __init__(self, registry_dir: str = "migrations"):
        """Initialize tracker with registry directory."""
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "data_contracts.json"
        self.contracts = self._load_contracts()
    
    def _load_contracts(self) -> Dict[str, DataContract]:
        """Load contracts from registry file."""
        if not self.registry_file.exists():
            return {}
        
        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                return {
                    table_name: DataContract.from_dict(contract_data)
                    for table_name, contract_data in data.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load contracts: {e}")
            return {}
    
    def _save_contracts(self) -> None:
        """Save contracts to registry file."""
        try:
            with open(self.registry_file, "w") as f:
                data = {
                    table_name: contract.to_dict()
                    for table_name, contract in self.contracts.items()
                }
                json.dump(data, f, indent=2)
                logger.info(f"Saved {len(self.contracts)} data contracts")
        except Exception as e:
            logger.error(f"Failed to save contracts: {e}")
    
    def register_contract(self, table_name: str, minimum_retention_days: int = 90) -> DataContract:
        """Register a new data contract for a table."""
        if table_name in self.contracts:
            logger.warning(f"Contract already exists for {table_name}")
            return self.contracts[table_name]
        
        contract = DataContract(
            table_name=table_name,
            minimum_retention_period_days=minimum_retention_days
        )
        self.contracts[table_name] = contract
        self._save_contracts()
        logger.info(f"Registered contract for table: {table_name}")
        return contract
    
    def mark_field_deprecated(
        self,
        table_name: str,
        field_name: str,
        removal_date: str,
        reason: str,
        replacement: Optional[str] = None
    ) -> bool:
        """Mark a field for deprecation."""
        if table_name not in self.contracts:
            logger.error(f"No contract found for table: {table_name}")
            return False
        
        contract = self.contracts[table_name]
        removal_dt = datetime.fromisoformat(removal_date)
        min_retention = timedelta(days=contract.minimum_retention_period_days)
        
        if removal_dt <= datetime.now():
            logger.error(f"Removal date must be in the future: {removal_date}")
            return False
        
        if (removal_dt - datetime.now()) < min_retention:
            logger.error(
                f"Removal date too soon. Required {contract.minimum_retention_period_days} days, "
                f"but only {(removal_dt - datetime.now()).days} days available"
            )
            return False
        
        # Check for duplicate deprecations
        if any(f.field_name == field_name for f in contract.deprecated_fields):
            logger.warning(f"Field {field_name} already marked for deprecation")
            return False
        
        deprecated_field = DeprecatedField(
            field_name=field_name,
            deprecated_at=datetime.now().isoformat(),
            removal_target=removal_date,
            reason=reason,
            replacement=replacement
        )
        contract.deprecated_fields.append(deprecated_field)
        self._save_contracts()
        logger.info(
            f"Marked {table_name}.{field_name} for removal on {removal_date} "
            f"({deprecated_field.days_until_removal()} days remaining)"
        )
        return True
    
    def detect_breaking_changes(
        self,
        table_name: str,
        old_fields: Dict[str, str],
        new_fields: Dict[str, str]
    ) -> List[BreakingChange]:
        """Detect breaking changes between schema versions."""
        changes: List[BreakingChange] = []
        
        # Check for removed fields
        for field_name in old_fields:
            if field_name not in new_fields:
                # Check if field was in deprecation plan
                contract = self.contracts.get(table_name)
                was_deprecated = (
                    contract and any(f.field_name == field_name for f in contract.deprecated_fields)
                )
                
                if not was_deprecated:
                    # Undocumented removal - breaking change
                    changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_COLUMN,
                        field_name=field_name,
                        severity=SeverityLevel.CRITICAL,
                        description=f"Field {field_name} removed without deprecation notice",
                        old_definition=old_fields[field_name]
                    ))
        
        # Check for type changes
        for field_name in old_fields:
            if field_name in new_fields and old_fields[field_name] != new_fields[field_name]:
                changes.append(BreakingChange(
                    change_type=BreakingChangeType.TYPE_CHANGE,
                    field_name=field_name,
                    severity=SeverityLevel.HIGH,
                    description=f"Field type changed from {old_fields[field_name]} to {new_fields[field_name]}",
                    old_definition=old_fields[field_name],
                    new_definition=new_fields[field_name]
                ))
        
        return changes
    
    def validate_migration(self, table_name: str, new_fields: Dict[str, str]) -> CompatibilityCheckResult:
        """Validate that a migration doesn't violate data contracts."""
        result = CompatibilityCheckResult(passed=True)
        
        contract = self.contracts.get(table_name)
        if not contract:
            # No contract defined, can't validate
            return result
        
        # Check deprecated field removals
        for deprecated_field in contract.deprecated_fields:
            if deprecated_field.field_name not in new_fields:
                if not deprecated_field.is_removal_overdue():
                    days_remaining = deprecated_field.days_until_removal()
                    result.passed = False
                    result.breaking_changes.append(BreakingChange(
                        change_type=BreakingChangeType.REMOVED_COLUMN,
                        field_name=deprecated_field.field_name,
                        severity=SeverityLevel.CRITICAL,
                        description=f"Cannot remove {deprecated_field.field_name} yet. "
                                   f"{days_remaining} days remaining until {deprecated_field.removal_target}"
                    ))
                    result.recommendations.append(
                        f"Keep {deprecated_field.field_name} until {deprecated_field.removal_target}"
                    )
            else:
                if not deprecated_field.is_removal_overdue():
                    days_remaining = deprecated_field.days_until_removal()
                    result.warnings.append(
                        f"Field {deprecated_field.field_name} still has {days_remaining} days "
                        f"before scheduled removal on {deprecated_field.removal_target}"
                    )
        
        return result
    
    def get_deprecation_timeline(self, table_name: str) -> Dict[str, Any]:
        """Get deprecation timeline for a table."""
        contract = self.contracts.get(table_name)
        if not contract:
            return {"status": "no_contract", "table": table_name}
        
        in_progress = []
        completed = []
        
        for field in contract.deprecated_fields:
            info = {
                "field": field.field_name,
                "deprecated_at": field.deprecated_at,
                "removal_target": field.removal_target,
                "days_remaining": field.days_until_removal(),
                "reason": field.reason,
                "replacement": field.replacement,
            }
            
            if field.is_removal_overdue():
                completed.append(info)
            else:
                in_progress.append(info)
        
        return {
            "table": table_name,
            "version": contract.version,
            "in_progress": in_progress,
            "completed": completed,
            "minimum_retention_days": contract.minimum_retention_period_days,
        }
    
    def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate full system compatibility report."""
        tables_with_deprecations = []
        reminders = []
        
        for table_name, contract in self.contracts.items():
            if contract.deprecated_fields:
                timeline = self.get_deprecation_timeline(table_name)
                tables_with_deprecations.append(timeline)
                
                # Generate reminders for soon-to-be-removed fields
                for field in contract.deprecated_fields:
                    days = field.days_until_removal()
                    if 0 < days <= 30:
                        reminders.append(
                            f"⚠ {table_name}.{field.field_name} removal in {days} days "
                            f"({field.removal_target})"
                        )
        
        return {
            "total_contracts": len(self.contracts),
            "tables_with_deprecations": len(tables_with_deprecations),
            "deprecation_timelines": tables_with_deprecations,
            "reminders_30_day": reminders,
        }
