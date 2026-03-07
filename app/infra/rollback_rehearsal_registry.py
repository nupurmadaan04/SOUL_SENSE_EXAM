"""
Rollback Rehearsal Registry

Persists rehearsal results to JSON for audit trail and observability.
Enables tracking of rollback safety metrics over time.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class RollbackRehearsalRegistry:
    """Manages persistence of rehearsal results."""
    
    def __init__(self, registry_path: str = None):
        """
        Initialize registry.
        
        Args:
            registry_path: Path to registry.json. If None, uses default location.
        """
        if registry_path is None:
            registry_path = Path(__file__).parent.parent.parent / "migrations" / "rollback_rehearsal_registry.json"
        
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_registry_exists()
    
    def _ensure_registry_exists(self) -> None:
        """Create empty registry if it doesn't exist."""
        if not self.registry_path.exists():
            initial_data = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "rehearsals": []
            }
            self.registry_path.write_text(json.dumps(initial_data, indent=2))
            logger.info(f"Created rollback rehearsal registry: {self.registry_path}")
    
    def record_rehearsal(self, result) -> None:
        """
        Record a rehearsal result.
        
        Args:
            result: RehearsalResult dataclass instance
        """
        try:
            data = self._load_registry()
            result_dict = asdict(result)
            data["rehearsals"].append(result_dict)
            data["last_updated"] = datetime.utcnow().isoformat()
            self._save_registry(data)
            logger.info(f"Recorded rehearsal for {result.migration_version}")
        except Exception as e:
            logger.error(f"Failed to record rehearsal: {e}")
    
    def record_batch(self, results: List) -> None:
        """
        Record multiple rehearsal results.
        
        Args:
            results: List of RehearsalResult instances
        """
        for result in results:
            self.record_rehearsal(result)
    
    def get_rehearsal_history(self, migration_version: str) -> List[Dict]:
        """
        Get all rehearsals for a specific migration.
        
        Args:
            migration_version: Version identifier
        
        Returns:
            List of rehearsal result dicts
        """
        data = self._load_registry()
        return [r for r in data["rehearsals"] if r["migration_version"] == migration_version]
    
    def get_latest_rehearsal(self, migration_version: str) -> Optional[Dict]:
        """Get the most recent rehearsal for a migration."""
        history = self.get_rehearsal_history(migration_version)
        return history[-1] if history else None
    
    def get_aggregate_metrics(self) -> Dict:
        """
        Calculate aggregate statistics across all rehearsals.
        
        Returns:
            Dict with total runs, pass rate, average reversibility, etc.
        """
        data = self._load_registry()
        rehearsals = data["rehearsals"]
        
        if not rehearsals:
            return {
                "total_rehearsals": 0,
                "pass_rate": 0,
                "warning_rate": 0,
                "failure_rate": 0,
                "avg_reversibility": 0,
                "non_reversible_migrations": []
            }
        
        passed = len([r for r in rehearsals if r["status"] == "passed"])
        warnings = len([r for r in rehearsals if r["status"] == "warning"])
        failed = len([r for r in rehearsals if r["status"] == "failed"])
        total = len(rehearsals)
        
        avg_reversibility = int(sum(r["reversibility_score"] for r in rehearsals) / total) if total else 0
        
        # Find non-reversible migrations
        non_reversible = [
            r["migration_version"] for r in rehearsals 
            if r["reversibility_score"] < 75
        ]
        
        return {
            "total_rehearsals": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "pass_rate": round(100 * passed / total, 1) if total else 0,
            "warning_rate": round(100 * warnings / total, 1) if total else 0,
            "failure_rate": round(100 * failed / total, 1) if total else 0,
            "avg_reversibility": avg_reversibility,
            "non_reversible_migrations": list(set(non_reversible))
        }
    
    def _load_registry(self) -> Dict:
        """Load registry from disk."""
        try:
            return json.loads(self.registry_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {"version": "1.0", "rehearsals": []}
    
    def _save_registry(self, data: Dict) -> None:
        """Save registry to disk."""
        try:
            self.registry_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")


def get_rollback_rehearsal_registry(registry_path: str = None) -> RollbackRehearsalRegistry:
    """Factory function to get registry instance."""
    return RollbackRehearsalRegistry(registry_path)
