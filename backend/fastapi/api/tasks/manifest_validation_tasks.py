"""
Manifest Validation Celery Tasks

Background tasks for manifest validation automation including:
- Batch validation
- Policy compliance checks
- Image scanning
- Report generation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

try:
    from celery import Celery
    from celery.exceptions import MaxRetriesExceededError
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    Celery = MockCelery

from backend.fastapi.api.utils.manifest_validation import (
    get_validation_manager,
    ValidationStatus,
    reset_validation_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery('manifest_validation')


# Task 1: Batch Validate Manifests
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def batch_validate_manifests(self, manifests: List[Dict[str, Any]], policy_id: str = None):
    """
    Validate multiple manifests in batch.
    
    Runs: On-demand
    """
    try:
        logger.info(f"Starting batch validation of {len(manifests)} manifests")
        
        async def _validate():
            manager = await get_validation_manager()
            
            results = []
            for manifest_data in manifests:
                result = await manager.validate_manifest(
                    manifest_content=manifest_data["content"],
                    manifest_format=manifest_data.get("format", "yaml"),
                    policy_id=policy_id,
                    manifest_name=manifest_data.get("name", "unnamed")
                )
                results.append({
                    "validation_id": result.validation_id,
                    "manifest_name": result.manifest_name,
                    "status": result.status.value,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count
                })
            
            return {
                "total": len(results),
                "valid": len([r for r in results if r["status"] == "valid"]),
                "invalid": len([r for r in results if r["status"] == "invalid"]),
                "partial": len([r for r in results if r["status"] == "partial"]),
                "results": results
            }
        
        result = asyncio.run(_validate())
        logger.info(f"Batch validation completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in batch validation: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for batch_validate_manifests")
            return {"error": str(exc)}


# Task 2: Generate Compliance Report
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_compliance_report(self, policy_id: str = None):
    """
    Generate compliance report for all validations.
    
    Runs: Daily
    """
    try:
        logger.info("Starting compliance report generation")
        
        async def _generate():
            manager = await get_validation_manager()
            
            # Get statistics
            stats = await manager.get_statistics()
            
            # Get recent validations
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            results = list(manager.validation_results.values())
            recent_results = [
                r for r in results
                if r.started_at >= start_time
            ]
            
            # Calculate compliance rate
            total = len(recent_results)
            compliant = len([r for r in recent_results if r.status == ValidationStatus.VALID])
            compliance_rate = (compliant / total * 100) if total > 0 else 0
            
            report = {
                "date": start_time.strftime("%Y-%m-%d"),
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats,
                "compliance_rate": round(compliance_rate, 2),
                "total_validations": total,
                "compliant": compliant,
                "non_compliant": total - compliant
            }
            
            logger.info("Compliance report generated successfully")
            return report
        
        result = asyncio.run(_generate())
        return result
        
    except Exception as exc:
        logger.error(f"Error generating compliance report: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_compliance_report")
            return {"error": str(exc)}


# Task 3: Cleanup Old Validation Results
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_validations(self, days_old: int = 30):
    """
    Archive or remove old validation results.
    
    Runs: Weekly
    """
    try:
        logger.info(f"Starting cleanup of validations older than {days_old} days")
        
        async def _cleanup():
            manager = await get_validation_manager()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            archived = 0
            
            for validation_id, result in list(manager.validation_results.items()):
                if result.started_at < cutoff_date:
                    # Mark as archived
                    result.policy_version = f"{result.policy_version}-archived"
                    archived += 1
            
            return {
                "archived": archived,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        result = asyncio.run(_cleanup())
        logger.info(f"Old validation cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up validations: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_old_validations")
            return {"error": str(exc)}


# Task 4: Check Policy Compliance
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def check_policy_compliance(self, policy_id: str):
    """
    Check compliance status for a specific policy.
    
    Runs: Every 6 hours
    """
    try:
        logger.info(f"Starting policy compliance check for {policy_id}")
        
        async def _check():
            manager = await get_validation_manager()
            
            policy = await manager.get_policy(policy_id)
            if not policy:
                return {"error": "Policy not found"}
            
            # Get validations using this policy
            results = [
                r for r in manager.validation_results.values()
                if r.policy_version.startswith(policy.version)
            ]
            
            total = len(results)
            valid = len([r for r in results if r.status == ValidationStatus.VALID])
            invalid = len([r for r in results if r.status == ValidationStatus.INVALID])
            partial = len([r for r in results if r.status == ValidationStatus.PARTIAL])
            
            return {
                "policy_id": policy_id,
                "policy_name": policy.name,
                "total_validations": total,
                "valid": valid,
                "invalid": invalid,
                "partial": partial,
                "compliance_rate": round((valid / total * 100), 2) if total > 0 else 0
            }
        
        result = asyncio.run(_check())
        logger.info(f"Policy compliance check completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error checking policy compliance: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for check_policy_compliance")
            return {"error": str(exc)}


# Celery Beat Schedule Configuration
"""
Add to Celery configuration:

CELERY_BEAT_SCHEDULE = {
    'compliance-report': {
        'task': 'api.tasks.manifest_validation_tasks.generate_compliance_report',
        'schedule': 86400.0,  # Daily
    },
    'cleanup-validations': {
        'task': 'api.tasks.manifest_validation_tasks.cleanup_old_validations',
        'schedule': 604800.0,  # Weekly
    },
    'policy-compliance-check': {
        'task': 'api.tasks.manifest_validation_tasks.check_policy_compliance',
        'schedule': 21600.0,  # Every 6 hours
        'args': ('golden-policy-default',)
    },
}
"""
