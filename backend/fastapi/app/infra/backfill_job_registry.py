"""
Backfill Job Observability Registry.

Tracks backfill operations during migrations with metrics, checksums, and rollback capability.
Minimal, clean implementation for migration data quality observability.
"""

import json
import logging
import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class BackfillStatus(str, Enum):
    """Backfill job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class BackfillMetrics:
    """Performance and quality metrics for a backfill job."""
    records_processed: int = 0
    records_failed: int = 0
    execution_time_ms: float = 0.0
    success_rate: float = 0.0
    checksum_before: str = ""
    checksum_after: str = ""
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.records_processed == 0:
            return 0.0
        return round(((self.records_processed - self.records_failed) / self.records_processed) * 100, 2)


@dataclass
class BackfillJob:
    """Core backfill job record."""
    backfill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = ""  # e.g., "age_group_backfill", "score_calculation"
    migration_version: str = ""  # e.g., "20260306_001"
    status: str = field(default=BackfillStatus.PENDING.value)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metrics: BackfillMetrics = field(default_factory=BackfillMetrics)
    error_details: Optional[str] = None
    rollback_capable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Flatten metrics for easier access
        metrics_dict = asdict(self.metrics)
        data.update({
            'records_processed': metrics_dict['records_processed'],
            'records_failed': metrics_dict['records_failed'],
            'execution_time_ms': metrics_dict['execution_time_ms'],
            'success_rate': metrics_dict['success_rate'],
            'checksum_before': metrics_dict['checksum_before'],
            'checksum_after': metrics_dict['checksum_after'],
        })
        data['metrics'] = metrics_dict
        return data


class BackfillRegistry:
    """Registry for tracking backfill operations."""
    
    REGISTRY_PATH = Path(__file__).parent.parent.parent / "migrations" / "backfill_registry.json"
    
    def __init__(self):
        """Initialize registry."""
        self.jobs: Dict[str, BackfillJob] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load existing registry from file."""
        if self.REGISTRY_PATH.exists():
            try:
                with open(self.REGISTRY_PATH, 'r') as f:
                    data = json.load(f)
                    for job_id, job_data in data.items():
                        # Extract and remove metrics from job data
                        metrics_data = job_data.pop('metrics', {})
                        
                        # Remove flattened metrics fields if they exist (from old format)
                        for key in ['records_processed', 'records_failed', 'execution_time_ms', 
                                   'success_rate', 'checksum_before', 'checksum_after']:
                            job_data.pop(key, None)
                        
                        job = BackfillJob(**job_data)
                        job.metrics = BackfillMetrics(**metrics_data)
                        self.jobs[job_id] = job
                logger.info(f"Loaded {len(self.jobs)} backfill records")
            except Exception as e:
                logger.warning(f"Failed to load backfill registry: {e}")
                self.jobs = {}
        else:
            self.jobs = {}
    
    def _save_registry(self) -> None:
        """Persist registry to file."""
        try:
            self.REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {job_id: job.to_dict() for job_id, job in self.jobs.items()}
            with open(self.REGISTRY_PATH, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backfill registry: {e}")
    
    def create_job(self, job_type: str, migration_version: str, metadata: Optional[Dict] = None) -> BackfillJob:
        """Create a new backfill job."""
        job = BackfillJob(
            job_type=job_type,
            migration_version=migration_version,
            metadata=metadata or {}
        )
        self.jobs[job.backfill_id] = job
        self._save_registry()
        logger.info(f"Created backfill job {job.backfill_id} ({job_type})")
        return job
    
    def start_job(self, backfill_id: str) -> None:
        """Mark job as in progress."""
        if backfill_id in self.jobs:
            job = self.jobs[backfill_id]
            job.status = BackfillStatus.IN_PROGRESS.value
            job.started_at = datetime.now(UTC).isoformat()
            self._save_registry()
    
    def update_progress(self, backfill_id: str, records_processed: int, records_failed: int = 0) -> None:
        """Update job progress."""
        if backfill_id in self.jobs:
            job = self.jobs[backfill_id]
            job.metrics.records_processed = records_processed
            job.metrics.records_failed = records_failed
            job.metrics.success_rate = job.metrics.calculate_success_rate()
            self._save_registry()
    
    def complete_job(self, backfill_id: str, metrics: Optional[Dict] = None) -> None:
        """Mark job as completed."""
        if backfill_id in self.jobs:
            job = self.jobs[backfill_id]
            job.status = BackfillStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC).isoformat()
            if metrics:
                job.metrics.records_processed = metrics.get('records_processed', job.metrics.records_processed)
                job.metrics.records_failed = metrics.get('records_failed', job.metrics.records_failed)
                job.metrics.checksum_after = metrics.get('checksum_after', '')
                job.metrics.execution_time_ms = metrics.get('execution_time_ms', 0.0)
                job.metrics.success_rate = job.metrics.calculate_success_rate()
            self._save_registry()
            logger.info(f"Completed backfill job {backfill_id} - {job.metrics.success_rate}% success rate")
    
    def fail_job(self, backfill_id: str, error: str) -> None:
        """Mark job as failed."""
        if backfill_id in self.jobs:
            job = self.jobs[backfill_id]
            job.status = BackfillStatus.FAILED.value
            job.completed_at = datetime.now(UTC).isoformat()
            job.error_details = error
            self._save_registry()
            logger.error(f"Failed backfill job {backfill_id}: {error}")
    
    def get_job(self, backfill_id: str) -> Optional[BackfillJob]:
        """Get job by ID."""
        return self.jobs.get(backfill_id)
    
    def get_jobs_by_migration(self, migration_version: str) -> List[BackfillJob]:
        """Get all jobs for a migration."""
        return [job for job in self.jobs.values() if job.migration_version == migration_version]
    
    def get_metrics_summary(self, migration_version: str) -> Dict[str, Any]:
        """Get metrics summary for a migration."""
        jobs = self.get_jobs_by_migration(migration_version)
        if not jobs:
            return {}
        
        total_processed = sum(j.metrics.records_processed for j in jobs)
        total_failed = sum(j.metrics.records_failed for j in jobs)
        avg_success = sum(j.metrics.success_rate for j in jobs) / len(jobs) if jobs else 0
        
        return {
            "job_count": len(jobs),
            "total_records_processed": total_processed,
            "total_records_failed": total_failed,
            "overall_success_rate": round(avg_success, 2),
            "migration_version": migration_version
        }
    
    def validate_data_integrity(self, backfill_id: str, checksum_before: str, checksum_after: str) -> bool:
        """Validate data integrity using checksums."""
        if backfill_id in self.jobs:
            job = self.jobs[backfill_id]
            job.metrics.checksum_before = checksum_before
            job.metrics.checksum_after = checksum_after
            self._save_registry()
            is_valid = checksum_before != checksum_after  # Data should have changed
            logger.info(f"Backfill {backfill_id} integrity: {'✓ PASS' if is_valid else '✗ FAIL'}")
            return is_valid
        return False
    
    def can_rollback(self, backfill_id: str) -> bool:
        """Check if job can be rolled back."""
        job = self.get_job(backfill_id)
        return job.rollback_capable if job else False
    
    def generate_rollback_info(self, backfill_id: str) -> Dict[str, Any]:
        """Generate rollback information."""
        job = self.get_job(backfill_id)
        if not job:
            return {}
        
        return {
            "backfill_id": backfill_id,
            "job_type": job.job_type,
            "migration_version": job.migration_version,
            "records_affected": job.metrics.records_processed,
            "checksum_before": job.metrics.checksum_before,
            "checksum_after": job.metrics.checksum_after,
            "rollback_capable": job.rollback_capable,
            "timestamp": datetime.now(UTC).isoformat()
        }


# Global registry instance
_registry: Optional[BackfillRegistry] = None


def get_backfill_registry() -> BackfillRegistry:
    """Get or create global registry instance."""
    global _registry
    if _registry is None:
        _registry = BackfillRegistry()
    return _registry
