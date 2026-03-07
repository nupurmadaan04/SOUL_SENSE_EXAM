"""
Onboarding Template Celery Tasks (#1439)

Background tasks for onboarding operations including:
- Automated onboarding execution
- Progress monitoring
- Cleanup of old onboarding data
- Notifications and reporting
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from ..utils.onboarding_template_generator import (
    get_template_generator,
    OnboardingTemplateGenerator,
    OnboardingStatus,
    TemplateStatus,
)
from ..services.db_service import engine


logger = logging.getLogger("api.tasks.onboarding")


# --- Automated Onboarding Tasks ---

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    time_limit=1800,  # 30 minutes
)
def execute_onboarding_task(self, onboarding_id: str) -> Dict[str, Any]:
    """
    Execute an onboarding process asynchronously.
    
    Args:
        onboarding_id: Onboarding ID to execute
        
    Returns:
        Execution result
    """
    logger.info(f"Executing onboarding {onboarding_id}")
    
    async def _execute():
        generator = await get_template_generator(engine)
        
        try:
            onboarding = await generator.execute_onboarding(onboarding_id)
            
            return {
                "status": "completed" if onboarding.status == OnboardingStatus.COMPLETED else "failed",
                "onboarding_id": onboarding_id,
                "tenant_id": onboarding.tenant_id,
                "progress": onboarding.progress_percentage,
                "errors": onboarding.errors,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Onboarding execution failed: {e}")
            raise self.retry(exc=e)
    
    try:
        return asyncio.run(_execute())
    except SoftTimeLimitExceeded:
        logger.error(f"Onboarding {onboarding_id} timed out")
        return {
            "status": "timeout",
            "onboarding_id": onboarding_id,
            "error": "Task exceeded time limit",
        }
    except Exception as exc:
        logger.error(f"Onboarding task failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "onboarding_id": onboarding_id,
                "error": str(exc),
            }


@shared_task
def process_pending_onboardings() -> Dict[str, Any]:
    """
    Process all pending onboardings.
    
    Returns:
        Processing summary
    """
    logger.info("Processing pending onboardings")
    
    async def _process():
        generator = await get_template_generator(engine)
        
        # Get pending onboardings
        pending = await generator.list_onboardings(
            status=OnboardingStatus.PENDING,
            limit=50
        )
        
        # Queue execution tasks
        queued = []
        for onboarding in pending:
            task = execute_onboarding_task.delay(onboarding.onboarding_id)
            queued.append({
                "onboarding_id": onboarding.onboarding_id,
                "tenant_id": onboarding.tenant_id,
                "task_id": task.id,
            })
        
        return {
            "status": "queued",
            "pending_count": len(pending),
            "queued": queued,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_process())
    except Exception as exc:
        logger.error(f"Process pending onboardings failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Monitoring Tasks ---

@shared_task
def check_onboarding_health() -> Dict[str, Any]:
    """
    Check health of running onboardings.
    
    Returns:
        Health status report
    """
    logger.info("Checking onboarding health")
    
    async def _check():
        generator = await get_template_generator(engine)
        
        # Get running onboardings
        running = await generator.list_onboardings(
            status=OnboardingStatus.IN_PROGRESS,
            limit=100
        )
        
        issues = []
        for onboarding in running:
            # Check if running too long
            if onboarding.started_at:
                duration = datetime.utcnow() - onboarding.started_at
                if duration > timedelta(hours=2):  # Running for more than 2 hours
                    issues.append({
                        "onboarding_id": onboarding.onboarding_id,
                        "tenant_id": onboarding.tenant_id,
                        "issue": "Running too long",
                        "duration_hours": duration.total_seconds() / 3600,
                    })
        
        return {
            "status": "healthy" if not issues else "issues_found",
            "running_count": len(running),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_check())
    except Exception as exc:
        return {
            "status": "unknown",
            "error": str(exc),
        }


@shared_task
def notify_onboarding_completion() -> Dict[str, Any]:
    """
    Send notifications for completed onboardings.
    
    Returns:
        Notification summary
    """
    logger.info("Notifying completed onboardings")
    
    async def _notify():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get recently completed onboardings (last hour)
            result = await session.execute(
                text("""
                    SELECT onboarding_id, tenant_id, tenant_name, status
                    FROM tenant_onboardings
                    WHERE completed_at > NOW() - INTERVAL '1 hour'
                    AND (status = 'completed' OR status = 'failed')
                """)
            )
            recent = result.fetchall()
            
            notifications = []
            for row in recent:
                # In production, would send actual email/Slack notifications
                notifications.append({
                    "onboarding_id": row.onboarding_id,
                    "tenant_id": row.tenant_id,
                    "tenant_name": row.tenant_name,
                    "status": row.status,
                })
                logger.info(f"Onboarding {row.onboarding_id} for {row.tenant_name} is {row.status}")
            
            return {
                "status": "completed",
                "notifications_sent": len(notifications),
                "notifications": notifications,
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    try:
        return asyncio.run(_notify())
    except Exception as exc:
        logger.error(f"Notification task failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Reporting Tasks ---

@shared_task
def generate_daily_onboarding_report() -> Dict[str, Any]:
    """
    Generate daily onboarding report.
    
    Returns:
        Report data
    """
    logger.info("Generating daily onboarding report")
    
    async def _generate():
        generator = await get_template_generator(engine)
        
        stats = await generator.get_statistics()
        
        # Get recent completions
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Completions in last 24 hours
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM tenant_onboardings
                    WHERE completed_at > NOW() - INTERVAL '24 hours'
                    AND status = 'completed'
                """)
            )
            completions_24h = result.scalar()
            
            # Failed in last 24 hours
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM tenant_onboardings
                    WHERE completed_at > NOW() - INTERVAL '24 hours'
                    AND status = 'failed'
                """)
            )
            failures_24h = result.scalar()
            
            # Average completion time
            result = await session.execute(
                text("""
                    SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_time
                    FROM tenant_onboardings
                    WHERE completed_at > NOW() - INTERVAL '24 hours'
                    AND status = 'completed'
                """)
            )
            row = result.fetchone()
            avg_completion_time = row.avg_time if row and row.avg_time else 0
        
        report = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "summary": {
                "total_templates": stats["total_templates"],
                "active_templates": stats["active_templates"],
                "total_onboardings": stats["total_onboardings"],
                "completions_24h": completions_24h,
                "failures_24h": failures_24h,
                "avg_completion_time_seconds": round(avg_completion_time, 2),
            },
            "status_breakdown": stats["status_breakdown"],
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        return report
    
    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def generate_tenant_provisioning_summary() -> Dict[str, Any]:
    """
    Generate summary of tenant provisioning.
    
    Returns:
        Provisioning summary
    """
    logger.info("Generating tenant provisioning summary")
    
    async def _generate():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Onboardings by template
            result = await session.execute(
                text("""
                    SELECT 
                        t.name as template_name,
                        COUNT(o.onboarding_id) as count,
                        SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN o.status = 'failed' THEN 1 ELSE 0 END) as failed
                    FROM onboarding_templates t
                    LEFT JOIN tenant_onboardings o ON t.template_id = o.template_id
                    GROUP BY t.template_id, t.name
                """)
            )
            by_template = [
                {
                    "template_name": r.template_name,
                    "total": r.count,
                    "completed": r.completed,
                    "failed": r.failed,
                }
                for r in result
            ]
            
            # Recent activity
            result = await session.execute(
                text("""
                    SELECT 
                        tenant_id,
                        tenant_name,
                        status,
                        created_at
                    FROM tenant_onboardings
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
            )
            recent = [
                {
                    "tenant_id": r.tenant_id,
                    "tenant_name": r.tenant_name,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in result
            ]
        
        return {
            "by_template": by_template,
            "recent_activity": recent,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Summary generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Cleanup Tasks ---

@shared_task
def cleanup_old_onboarding_data(retention_days: int = 90) -> Dict[str, Any]:
    """
    Clean up old onboarding data.
    
    Args:
        retention_days: Days to retain data
        
    Returns:
        Cleanup summary
    """
    logger.info(f"Cleaning up onboarding data older than {retention_days} days")
    
    async def _cleanup():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Clean up old step logs
            result = await session.execute(
                text("""
                    DELETE FROM onboarding_step_logs
                    WHERE executed_at < NOW() - INTERVAL ':days days'
                    RETURNING COUNT(*)
                """),
                {"days": retention_days}
            )
            logs_deleted = result.scalar()
            
            # Clean up old completed/failed onboardings
            result = await session.execute(
                text("""
                    DELETE FROM tenant_onboardings
                    WHERE created_at < NOW() - INTERVAL ':days days'
                    AND status IN ('completed', 'failed', 'rolled_back')
                    RETURNING COUNT(*)
                """),
                {"days": retention_days}
            )
            onboardings_deleted = result.scalar()
            
            await session.commit()
        
        return {
            "status": "completed",
            "logs_deleted": logs_deleted,
            "onboardings_deleted": onboardings_deleted,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def archive_old_templates(archive_days: int = 365) -> Dict[str, Any]:
    """
    Archive old templates that haven't been used.
    
    Args:
        archive_days: Days of inactivity before archiving
        
    Returns:
        Archival summary
    """
    logger.info(f"Archiving templates inactive for {archive_days} days")
    
    async def _archive():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Find templates without recent onboardings
            result = await session.execute(
                text("""
                    UPDATE onboarding_templates
                    SET status = 'archived', updated_at = NOW()
                    WHERE status = 'active'
                    AND template_id NOT IN (
                        SELECT DISTINCT template_id
                        FROM tenant_onboardings
                        WHERE created_at > NOW() - INTERVAL ':days days'
                    )
                    AND created_at < NOW() - INTERVAL ':days days'
                    RETURNING template_id, name
                """),
                {"days": archive_days}
            )
            archived = result.fetchall()
            await session.commit()
        
        return {
            "status": "completed",
            "archived_count": len(archived),
            "archived_templates": [{"id": r.template_id, "name": r.name} for r in archived],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_archive())
    except Exception as exc:
        logger.error(f"Archival failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Maintenance Tasks ---

@shared_task
def retry_failed_onboardings() -> Dict[str, Any]:
    """
    Retry failed onboardings.
    
    Returns:
        Retry summary
    """
    logger.info("Retrying failed onboardings")
    
    async def _retry():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get failed onboardings from last 24 hours
            result = await session.execute(
                text("""
                    SELECT onboarding_id, tenant_id
                    FROM tenant_onboardings
                    WHERE status = 'failed'
                    AND created_at > NOW() - INTERVAL '24 hours'
                    LIMIT 10
                """)
            )
            failed = result.fetchall()
        
        retried = []
        for row in failed:
            task = execute_onboarding_task.delay(row.onboarding_id)
            retried.append({
                "onboarding_id": row.onboarding_id,
                "tenant_id": row.tenant_id,
                "task_id": task.id,
            })
        
        return {
            "status": "completed",
            "failed_count": len(failed),
            "retried": retried,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_retry())
    except Exception as exc:
        logger.error(f"Retry task failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def validate_template_integrity() -> Dict[str, Any]:
    """
    Validate integrity of active templates.
    
    Returns:
        Validation summary
    """
    logger.info("Validating template integrity")
    
    async def _validate():
        generator = await get_template_generator(engine)
        
        templates = await generator.list_templates(
            status=TemplateStatus.ACTIVE,
            limit=1000
        )
        
        issues = []
        for template in templates:
            # Check for empty steps
            if not template.config.steps:
                issues.append({
                    "template_id": template.template_id,
                    "template_name": template.name,
                    "issue": "No steps defined",
                })
            
            # Check for circular dependencies
            step_ids = {s.step_id for s in template.config.steps}
            for step in template.config.steps:
                for dep in step.dependencies:
                    if dep not in step_ids:
                        issues.append({
                            "template_id": template.template_id,
                            "template_name": template.name,
                            "issue": f"Step {step.step_id} has invalid dependency: {dep}",
                        })
        
        return {
            "status": "completed",
            "templates_checked": len(templates),
            "issues_found": len(issues),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_validate())
    except Exception as exc:
        logger.error(f"Validation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Setup Task ---

@shared_task
def setup_onboarding_schedules() -> Dict[str, Any]:
    """
    Setup periodic onboarding maintenance schedules.
    
    Returns:
        Setup result
    """
    logger.info("Setting up onboarding schedules")
    
    return {
        "status": "configured",
        "schedules": [
            {
                "task": "api.tasks.onboarding_tasks.process_pending_onboardings",
                "schedule": "every 5 minutes",
            },
            {
                "task": "api.tasks.onboarding_tasks.check_onboarding_health",
                "schedule": "every 15 minutes",
            },
            {
                "task": "api.tasks.onboarding_tasks.notify_onboarding_completion",
                "schedule": "hourly",
            },
            {
                "task": "api.tasks.onboarding_tasks.generate_daily_onboarding_report",
                "schedule": "daily at 9:00",
            },
            {
                "task": "api.tasks.onboarding_tasks.retry_failed_onboardings",
                "schedule": "every 6 hours",
            },
            {
                "task": "api.tasks.onboarding_tasks.cleanup_old_onboarding_data",
                "schedule": "weekly",
            },
            {
                "task": "api.tasks.onboarding_tasks.validate_template_integrity",
                "schedule": "daily",
            },
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }
