"""
Cross-Region Migration Registry.

Persistent audit trail and state management for cross-region migrations.
Stores execution history, enables resume capability, and tracks rollback state.
"""

import json
import logging
import os
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path

from app.infra.cross_region_migration_sequencer import (
    CrossRegionMigrationPlan, 
    RegionalMigrationStep,
    MigrationStatus
)

logger = logging.getLogger(__name__)


class CrossRegionMigrationRegistry:
    """
    Registry for tracking cross-region migrations.
    
    Maintains JSON audit trail at: migrations/cross_region_registry.json
    Enables queries on execution history and state resumption.
    """
    
    def __init__(self, registry_path: str = "migrations/cross_region_registry.json"):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load existing registry or initialize empty."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}, initializing empty")
                self.data = {"migrations": [], "dependencies": {}}
        else:
            self.data = {"migrations": [], "dependencies": {}}
    
    def _save_registry(self) -> None:
        """Persist registry to disk."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_execution(self, plan: CrossRegionMigrationPlan) -> None:
        """Register new migration execution."""
        migration_record = {
            "migration_version": plan.migration_version,
            "status": plan.status.value,
            "created_at": plan.created_at.isoformat(),
            "started_at": plan.started_at.isoformat() if plan.started_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
            "initiated_by": plan.initiated_by,
            "regions": [r.name for r in plan.regions],
            "regions_count": len(plan.regions),
        }
        self.data["migrations"].append(migration_record)
        self._save_registry()
        logger.info(f"✓ Registered migration {plan.migration_version}")
    
    def update_region_status(
        self, 
        migration_version: str, 
        region_name: str, 
        step: RegionalMigrationStep
    ) -> None:
        """Update regional migration step status."""
        for migration in self.data["migrations"]:
            if migration["migration_version"] == migration_version:
                if "steps" not in migration:
                    migration["steps"] = []
                
                # Find or create step record
                step_record = next(
                    (s for s in migration["steps"] if s["region_name"] == region_name),
                    None
                )
                
                if step_record is None:
                    step_record = {"region_name": region_name}
                    migration["steps"].append(step_record)
                
                step_record.update(step.to_dict())
                self._save_registry()
                return
        
        logger.warning(f"Migration {migration_version} not found in registry")
    
    def get_execution_history(self, migration_version: Optional[str] = None) -> List[Dict]:
        """
        Get execution history.
        
        Args:
            migration_version: Filter by specific migration, or None for all
            
        Returns:
            List of migration records
        """
        if migration_version:
            return [
                m for m in self.data["migrations"] 
                if m["migration_version"] == migration_version
            ]
        return self.data["migrations"]
    
    def get_last_migration(self) -> Optional[Dict]:
        """Get most recent migration record."""
        if not self.data["migrations"]:
            return None
        return self.data["migrations"][-1]
    
    def is_migration_safe_to_retry(self, migration_version: str) -> tuple[bool, Optional[str]]:
        """
        Check if migration can safely be retried.
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        records = [m for m in self.data["migrations"] if m["migration_version"] == migration_version]
        
        if not records:
            return True, None  # Never attempted, safe to start
        
        last_record = records[-1]
        status = last_record.get("status")
        
        if status == MigrationStatus.COMPLETED.value:
            return False, "Migration already completed successfully"
        
        if status == MigrationStatus.ROLLED_BACK.value:
            return True, None  # Safe to retry after rollback
        
        if status == MigrationStatus.FAILED.value:
            # Check if enough time has passed since failure
            return True, None  # Can retry failed migrations
        
        if status == MigrationStatus.IN_PROGRESS.value:
            return False, "Migration currently in progress. Complete or rollback first."
        
        return True, None
    
    def get_failed_regions(self, migration_version: str) -> List[str]:
        """Get list of regions that failed in a migration."""
        records = [m for m in self.data["migrations"] if m["migration_version"] == migration_version]
        if not records:
            return []
        
        last_record = records[-1]
        steps = last_record.get("steps", [])
        
        return [s["region_name"] for s in steps if s.get("status") == "failed"]
    
    def store_dependency_graph(self, dependencies: Dict[str, List[str]]) -> None:
        """Store dependency graph for audit trail."""
        self.data["dependencies"] = dependencies
        self._save_registry()
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get stored dependency graph."""
        return self.data.get("dependencies", {})


# Global registry instance
_registry_instance: Optional[CrossRegionMigrationRegistry] = None


def get_cross_region_registry() -> CrossRegionMigrationRegistry:
    """Get or create global registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CrossRegionMigrationRegistry()
    return _registry_instance
