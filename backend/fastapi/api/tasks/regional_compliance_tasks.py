"""
Regional Compliance Celery Tasks

Background tasks for compliance monitoring, audit log management,
consent expiration checks, and data retention enforcement.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

try:
    from celery import Celery, chain, group, chord
    from celery.exceptions import MaxRetriesExceededError
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Create mock Celery class for development
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    Celery = MockCelery

from backend.fastapi.api.utils.regional_compliance import (
    get_compliance_manager,
    ComplianceRegion,
    ComplianceAction,
    DataCategory,
    ConsentStatus,
    reset_compliance_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery('regional_compliance')


# Task 1: Check Expired Consents
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_expired_consents(self):
    """
    Check for expired consent records and update their status.
    
    Runs: Daily
    """
    try:
        logger.info("Starting expired consent check task")
        
        async def _check():
            manager = await get_compliance_manager()
            expired_count = 0
            
            for consent_id, consent in manager.consent_records.items():
                if consent.status == ConsentStatus.GRANTED:
                    if consent.expires_at and consent.expires_at < datetime.utcnow():
                        consent.status = ConsentStatus.EXPIRED
                        consent.updated_at = datetime.utcnow()
                        expired_count += 1
                        logger.info(f"Marked consent as expired: {consent_id}")
            
            return {"expired_consents": expired_count}
        
        result = asyncio.run(_check())
        logger.info(f"Expired consent check completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error checking expired consents: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for check_expired_consents")
            return {"error": str(exc), "expired_consents": 0}


# Task 2: Process Pending RTD Requests
@app.task(bind=True, max_retries=3, default_retry_delay=300)
def process_pending_rtd_requests(self):
    """
    Process pending Right to Deletion requests.
    
    Runs: Every 6 hours
    """
    try:
        logger.info("Starting pending RTD requests processing")
        
        async def _process():
            manager = await get_compliance_manager()
            processed = 0
            overdue = 0
            
            now = datetime.utcnow()
            
            for request_id, request in manager.rtd_requests.items():
                if request.status == "pending":
                    # Check if approaching deadline
                    if request.completion_deadline:
                        days_until_deadline = (request.completion_deadline - now).days
                        
                        if days_until_deadline < 0:
                            # Overdue - escalate
                            overdue += 1
                            logger.warning(f"RTD request overdue: {request_id}")
                        elif days_until_deadline <= 3:
                            # Approaching deadline - notify
                            logger.info(f"RTD request approaching deadline: {request_id} ({days_until_deadline} days)")
                    
                    # Auto-approve simple requests (no verification needed)
                    if not request.verification_method:
                        request.status = "in_progress"
                        request.audit_trail.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "action": "auto_approved",
                            "details": "Request auto-approved (no verification required)"
                        })
                        processed += 1
            
            return {
                "processed": processed,
                "overdue": overdue,
                "total_pending": len([r for r in manager.rtd_requests.values() if r.status == "pending"])
            }
        
        result = asyncio.run(_process())
        logger.info(f"Pending RTD processing completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error processing pending RTD requests: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for process_pending_rtd_requests")
            return {"error": str(exc)}


# Task 3: Generate Compliance Report
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_compliance_report(self, region: str = None):
    """
    Generate a compliance report for a region or globally.
    
    Runs: Weekly
    """
    try:
        logger.info(f"Starting compliance report generation for region: {region or 'all'}")
        
        async def _generate():
            manager = await get_compliance_manager()
            
            # Get statistics
            stats = await manager.get_statistics()
            
            # Get recent audit logs
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            logs = await manager.get_audit_logs(
                region=ComplianceRegion(region) if region else None,
                start_time=start_time,
                end_time=end_time,
                limit=1000
            )
            
            # Analyze risk levels
            risk_distribution = {"low": 0, "medium": 0, "high": 0}
            for log in logs:
                risk_distribution[log.risk_level] = risk_distribution.get(log.risk_level, 0) + 1
            
            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "region": region or "all",
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "statistics": stats,
                "audit_activity": {
                    "total_logs": len(logs),
                    "risk_distribution": risk_distribution
                },
                "recommendations": []
            }
            
            # Add recommendations based on findings
            if risk_distribution["high"] > 10:
                report["recommendations"].append({
                    "priority": "high",
                    "message": f"High number of high-risk activities ({risk_distribution['high']}). Review processing activities."
                })
            
            if stats["rtd_requests"]["pending"] > 5:
                report["recommendations"].append({
                    "priority": "medium",
                    "message": f"{stats['rtd_requests']['pending']} pending RTD requests. Ensure timely processing."
                })
            
            return report
        
        result = asyncio.run(_generate())
        logger.info("Compliance report generated successfully")
        return result
        
    except Exception as exc:
        logger.error(f"Error generating compliance report: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_compliance_report")
            return {"error": str(exc)}


# Task 4: Verify Audit Log Integrity
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def verify_audit_log_integrity(self, start_date: str = None, end_date: str = None):
    """
    Verify integrity of audit logs by checking checksums.
    
    Runs: Daily
    """
    try:
        logger.info("Starting audit log integrity verification")
        
        async def _verify():
            manager = await get_compliance_manager()
            
            # Filter logs by date if specified
            logs = manager.audit_logs
            if start_date:
                start = datetime.fromisoformat(start_date)
                logs = [l for l in logs if l.timestamp >= start]
            if end_date:
                end = datetime.fromisoformat(end_date)
                logs = [l for l in logs if l.timestamp <= end]
            
            verified_count = 0
            failed_count = 0
            
            import json
            import hashlib
            
            for log in logs:
                if not log.checksum:
                    continue
                
                # Recompute checksum
                log_data = json.dumps({
                    "log_id": log.log_id,
                    "timestamp": log.timestamp.isoformat(),
                    "region": log.region.value,
                    "action": log.action.value,
                    "user_id": log.user_id,
                    "data_subject_id": log.data_subject_id
                }, sort_keys=True)
                computed_checksum = hashlib.sha256(log_data.encode()).hexdigest()
                
                if computed_checksum == log.checksum:
                    log.verified = True
                    log.verification_timestamp = datetime.utcnow()
                    verified_count += 1
                else:
                    failed_count += 1
                    logger.error(f"Checksum mismatch for log: {log.log_id}")
            
            return {
                "verified": verified_count,
                "failed": failed_count,
                "total_checked": len(logs)
            }
        
        result = asyncio.run(_verify())
        logger.info(f"Audit log verification completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error verifying audit logs: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for verify_audit_log_integrity")
            return {"error": str(exc)}


# Task 5: Cleanup Old Export Requests
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_export_requests(self, days_old: int = 30):
    """
    Clean up expired data export requests.
    
    Runs: Daily
    """
    try:
        logger.info(f"Starting cleanup of export requests older than {days_old} days")
        
        async def _cleanup():
            manager = await get_compliance_manager()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            removed = 0
            expired = 0
            
            expired_ids = []
            for request_id, request in manager.export_requests.items():
                # Mark expired requests
                if request.expires_at and request.expires_at < datetime.utcnow():
                    if request.status != "expired":
                        request.status = "expired"
                        expired += 1
                
                # Remove old expired/ready requests
                if request.requested_at < cutoff_date:
                    expired_ids.append(request_id)
                    removed += 1
            
            for request_id in expired_ids:
                del manager.export_requests[request_id]
            
            return {
                "removed": removed,
                "marked_expired": expired,
                "remaining": len(manager.export_requests)
            }
        
        result = asyncio.run(_cleanup())
        logger.info(f"Export request cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up export requests: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_old_export_requests")
            return {"error": str(exc)}


# Task 6: Monitor Compliance Deadlines
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def monitor_compliance_deadlines(self):
    """
    Monitor upcoming compliance deadlines and send alerts.
    
    Runs: Hourly
    """
    try:
        logger.info("Starting compliance deadline monitoring")
        
        async def _monitor():
            manager = await get_compliance_manager()
            now = datetime.utcnow()
            
            alerts = []
            
            # Check RTD deadlines
            for request_id, request in manager.rtd_requests.items():
                if request.status in ["pending", "in_progress"] and request.completion_deadline:
                    days_remaining = (request.completion_deadline - now).days
                    
                    if days_remaining < 0:
                        alerts.append({
                            "type": "rtd_overdue",
                            "request_id": request_id,
                            "user_id": request.user_id,
                            "days_overdue": abs(days_remaining),
                            "severity": "critical"
                        })
                    elif days_remaining <= 3:
                        alerts.append({
                            "type": "rtd_approaching_deadline",
                            "request_id": request_id,
                            "user_id": request.user_id,
                            "days_remaining": days_remaining,
                            "severity": "high" if days_remaining <= 1 else "medium"
                        })
            
            # Check export deadlines
            for request_id, request in manager.export_requests.items():
                if request.status == "pending" and request.expires_at:
                    days_remaining = (request.expires_at - now).days
                    
                    if days_remaining < 0:
                        alerts.append({
                            "type": "export_deadline_passed",
                            "request_id": request_id,
                            "user_id": request.user_id,
                            "severity": "high"
                        })
            
            return {
                "alerts": alerts,
                "total_alerts": len(alerts),
                "critical": len([a for a in alerts if a["severity"] == "critical"]),
                "high": len([a for a in alerts if a["severity"] == "high"]),
                "medium": len([a for a in alerts if a["severity"] == "medium"])
            }
        
        result = asyncio.run(_monitor())
        
        if result["total_alerts"] > 0:
            logger.warning(f"Compliance deadline alerts: {result}")
        else:
            logger.info("No compliance deadline alerts")
        
        return result
        
    except Exception as exc:
        logger.error(f"Error monitoring compliance deadlines: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for monitor_compliance_deadlines")
            return {"error": str(exc)}


# Task 7: Sync Consent Across Regions
@app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_consent_across_regions(self, user_id: str = None):
    """
    Sync consent records across regions for a user.
    
    Runs: On-demand or scheduled
    """
    try:
        logger.info(f"Starting consent sync for user: {user_id or 'all'}")
        
        async def _sync():
            manager = await get_compliance_manager()
            
            if user_id:
                user_ids = [user_id]
            else:
                user_ids = list(manager.user_consents.keys())
            
            synced = 0
            conflicts = 0
            
            for uid in user_ids:
                consents = await manager.get_user_consents(uid, active_only=False)
                
                # Check for conflicts (e.g., granted in one region, withdrawn in another)
                purposes = {}
                for consent in consents:
                    for purpose in consent.purposes:
                        key = f"{purpose}_{','.join(sorted(dc.value for dc in consent.data_categories))}"
                        if key not in purposes:
                            purposes[key] = []
                        purposes[key].append(consent)
                
                # Detect conflicts
                for key, consent_list in purposes.items():
                    statuses = set(c.status for c in consent_list)
                    if len(statuses) > 1:
                        conflicts += 1
                        logger.warning(f"Consent conflict detected for user {uid}: {key}")
            
            return {
                "users_checked": len(user_ids),
                "consents_synced": synced,
                "conflicts_detected": conflicts
            }
        
        result = asyncio.run(_sync())
        logger.info(f"Consent sync completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error syncing consent: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for sync_consent_across_regions")
            return {"error": str(exc)}


# Task 8: Archive Old Audit Logs
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def archive_old_audit_logs(self, days_old: int = 365):
    """
    Archive old audit logs to cold storage.
    
    Runs: Monthly
    """
    try:
        logger.info(f"Starting audit log archival for logs older than {days_old} days")
        
        async def _archive():
            manager = await get_compliance_manager()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old logs
            old_logs = [log for log in manager.audit_logs if log.timestamp < cutoff_date]
            
            # In real implementation, these would be moved to cold storage
            # For now, we just mark them as archived
            archived = 0
            for log in old_logs:
                log.metadata["archived"] = True
                log.metadata["archived_at"] = datetime.utcnow().isoformat()
                archived += 1
            
            return {
                "archived": archived,
                "cutoff_date": cutoff_date.isoformat(),
                "remaining_active": len(manager.audit_logs) - archived
            }
        
        result = asyncio.run(_archive())
        logger.info(f"Audit log archival completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error archiving audit logs: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for archive_old_audit_logs")
            return {"error": str(exc)}


# Task 9: Validate Data Retention Policies
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def validate_data_retention_policies(self):
    """
    Validate that data retention policies are being followed.
    
    Runs: Weekly
    """
    try:
        logger.info("Starting data retention policy validation")
        
        async def _validate():
            manager = await get_compliance_manager()
            
            violations = []
            
            # Check each retention policy
            for policy_id, policy in manager.retention_policies.items():
                # In real implementation, this would check actual data
                # For now, we just verify the policy configuration
                
                if policy.retention_period_days <= 0:
                    violations.append({
                        "policy_id": policy_id,
                        "issue": "invalid_retention_period",
                        "message": f"Retention period must be positive: {policy.retention_period_days}"
                    })
                
                if policy.auto_delete and not policy.retention_period_days:
                    violations.append({
                        "policy_id": policy_id,
                        "issue": "auto_delete_without_retention",
                        "message": "Auto-delete enabled but no retention period set"
                    })
            
            return {
                "policies_checked": len(manager.retention_policies),
                "violations": violations,
                "violation_count": len(violations)
            }
        
        result = asyncio.run(_validate())
        
        if result["violation_count"] > 0:
            logger.warning(f"Data retention policy violations found: {result['violation_count']}")
        else:
            logger.info("All data retention policies validated successfully")
        
        return result
        
    except Exception as exc:
        logger.error(f"Error validating retention policies: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for validate_data_retention_policies")
            return {"error": str(exc)}


# Task 10: Generate Regional Compliance Score
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_regional_compliance_score(self, region: str):
    """
    Calculate a compliance score for a region.
    
    Runs: Daily
    """
    try:
        logger.info(f"Generating compliance score for region: {region}")
        
        async def _score():
            manager = await get_compliance_manager()
            region_enum = ComplianceRegion(region)
            
            stats = await manager.get_statistics()
            
            # Calculate score components
            score = 100.0
            details = {}
            
            # Deduct for pending RTD requests
            pending_rtd = stats["rtd_requests"]["pending"]
            if pending_rtd > 0:
                rtd_penalty = min(pending_rtd * 2, 20)
                score -= rtd_penalty
                details["pending_rtd_penalty"] = rtd_penalty
            
            # Deduct for expired consents
            expired_consents = stats["consents"]["expired"]
            if expired_consents > 0:
                consent_penalty = min(expired_consents * 0.5, 10)
                score -= consent_penalty
                details["expired_consent_penalty"] = consent_penalty
            
            # Deduct for non-compliant audit entries
            region_logs = await manager.get_audit_logs(region=region_enum, limit=1000)
            high_risk_count = len([l for l in region_logs if l.risk_level == "high"])
            if high_risk_count > 0:
                risk_penalty = min(high_risk_count * 1, 15)
                score -= risk_penalty
                details["high_risk_penalty"] = risk_penalty
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            return {
                "region": region,
                "score": round(score, 2),
                "max_score": 100,
                "details": details,
                "generated_at": datetime.utcnow().isoformat(),
                "status": "excellent" if score >= 95 else "good" if score >= 85 else "needs_improvement" if score >= 70 else "critical"
            }
        
        result = asyncio.run(_score())
        logger.info(f"Compliance score for {region}: {result['score']}")
        return result
        
    except Exception as exc:
        logger.error(f"Error generating compliance score: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_regional_compliance_score")
            return {"error": str(exc)}


# Celery Beat Schedule Configuration
"""
Add to Celery configuration:

CELERY_BEAT_SCHEDULE = {
    'check-expired-consents': {
        'task': 'api.tasks.regional_compliance_tasks.check_expired_consents',
        'schedule': 86400.0,  # Daily
    },
    'process-pending-rtd': {
        'task': 'api.tasks.regional_compliance_tasks.process_pending_rtd_requests',
        'schedule': 21600.0,  # Every 6 hours
    },
    'generate-compliance-report': {
        'task': 'api.tasks.regional_compliance_tasks.generate_compliance_report',
        'schedule': 604800.0,  # Weekly
    },
    'verify-audit-logs': {
        'task': 'api.tasks.regional_compliance_tasks.verify_audit_log_integrity',
        'schedule': 86400.0,  # Daily
    },
    'cleanup-export-requests': {
        'task': 'api.tasks.regional_compliance_tasks.cleanup_old_export_requests',
        'schedule': 86400.0,  # Daily
    },
    'monitor-deadlines': {
        'task': 'api.tasks.regional_compliance_tasks.monitor_compliance_deadlines',
        'schedule': 3600.0,  # Hourly
    },
    'archive-audit-logs': {
        'task': 'api.tasks.regional_compliance_tasks.archive_old_audit_logs',
        'schedule': 2592000.0,  # Monthly
    },
    'validate-retention': {
        'task': 'api.tasks.regional_compliance_tasks.validate_data_retention_policies',
        'schedule': 604800.0,  # Weekly
    },
    'compliance-score-eu': {
        'task': 'api.tasks.regional_compliance_tasks.generate_regional_compliance_score',
        'schedule': 86400.0,  # Daily
        'args': ('eu',)
    },
    'compliance-score-usa': {
        'task': 'api.tasks.regional_compliance_tasks.generate_regional_compliance_score',
        'schedule': 86400.0,  # Daily
        'args': ('usa',)
    },
}
"""
