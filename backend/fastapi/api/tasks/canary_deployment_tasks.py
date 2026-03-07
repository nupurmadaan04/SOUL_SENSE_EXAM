"""
Canary Deployment Celery Tasks

Background tasks for canary deployment automation including:
- Automated health analysis
- Step advancement
- Promotion/rollback automation
- Metric aggregation
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

from backend.fastapi.api.utils.canary_deployment import (
    get_canary_manager,
    CanaryStatus,
    reset_canary_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery('canary_deployment')


# Task 1: Automated Health Analysis
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def automated_health_analysis(self):
    """
    Run automated health analysis on active canary deployments.
    
    Runs: Every 5 minutes
    """
    try:
        logger.info("Starting automated health analysis")
        
        async def _analyze():
            manager = await get_canary_manager()
            
            # Get running deployments
            deployments = await manager.list_deployments(status=CanaryStatus.RUNNING)
            
            analyses = []
            for deployment in deployments:
                # Check if step has been running long enough
                if deployment.steps and deployment.current_step > 0:
                    step = deployment.steps[deployment.current_step - 1]
                    min_duration = timedelta(minutes=step.duration_minutes)
                    
                    # Get last analysis
                    last_analyses = manager.analyses.get(deployment.canary_id, [])
                    if last_analyses:
                        last_analysis = last_analyses[-1]
                        time_since = datetime.utcnow() - last_analysis.timestamp
                        
                        if time_since < min_duration:
                            continue
                
                # Run analysis
                analysis = await manager.analyze_health(deployment.canary_id)
                if analysis:
                    analyses.append({
                        "canary_id": deployment.canary_id,
                        "recommendation": analysis.recommendation,
                        "confidence": analysis.confidence_score
                    })
            
            return {
                "deployments_analyzed": len(deployments),
                "analyses_performed": len(analyses),
                "results": analyses
            }
        
        result = asyncio.run(_analyze())
        logger.info(f"Health analysis completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in health analysis: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for automated_health_analysis")
            return {"error": str(exc)}


# Task 2: Auto-Advance Steps
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def auto_advance_steps(self):
    """
    Automatically advance canary steps when health is good.
    
    Runs: Every 10 minutes
    """
    try:
        logger.info("Starting auto-advance check")
        
        async def _advance():
            manager = await get_canary_manager()
            
            deployments = await manager.list_deployments(status=CanaryStatus.RUNNING)
            
            advanced = 0
            for deployment in deployments:
                if not deployment.auto_promote:
                    continue
                
                # Check last analysis
                analyses = manager.analyses.get(deployment.canary_id, [])
                if not analyses:
                    continue
                
                last_analysis = analyses[-1]
                
                # Only advance if healthy and confident
                if (last_analysis.recommendation == "continue" and 
                    last_analysis.confidence_score >= 0.8 and
                    not last_analysis.issues):
                    
                    # Check minimum duration
                    if deployment.steps and deployment.current_step > 0:
                        step = deployment.steps[deployment.current_step - 1]
                        min_duration = timedelta(minutes=step.duration_minutes)
                        
                        # Get last event
                        events = await manager.get_events(
                            canary_id=deployment.canary_id,
                            event_type="step_advanced",
                            limit=1
                        )
                        
                        if events:
                            time_since = datetime.utcnow() - events[0].timestamp
                            if time_since >= min_duration:
                                await manager.advance_step(deployment.canary_id)
                                advanced += 1
                        else:
                            # First advancement
                            await manager.advance_step(deployment.canary_id)
                            advanced += 1
            
            return {"advanced": advanced}
        
        result = asyncio.run(_advance())
        logger.info(f"Auto-advance completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in auto-advance: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for auto_advance_steps")
            return {"error": str(exc)}


# Task 3: Cleanup Old Deployments
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_deployments(self, days_old: int = 30):
    """
    Archive or remove old canary deployments.
    
    Runs: Daily
    """
    try:
        logger.info(f"Starting cleanup of deployments older than {days_old} days")
        
        async def _cleanup():
            manager = await get_canary_manager()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            archived = 0
            
            for canary_id, deployment in list(manager.deployments.items()):
                if deployment.status in [CanaryStatus.PROMOTED, CanaryStatus.ROLLED_BACK]:
                    if deployment.completed_at and deployment.completed_at < cutoff_date:
                        # Archive by marking
                        deployment.labels["archived"] = "true"
                        deployment.labels["archived_at"] = datetime.utcnow().isoformat()
                        archived += 1
            
            return {"archived": archived}
        
        result = asyncio.run(_cleanup())
        logger.info(f"Old deployment cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up deployments: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_old_deployments")
            return {"error": str(exc)}


# Task 4: Generate Daily Report
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_daily_canary_report(self):
    """
    Generate daily canary deployment report.
    
    Runs: Daily
    """
    try:
        logger.info("Starting daily canary report generation")
        
        async def _generate():
            manager = await get_canary_manager()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            # Get statistics
            stats = await manager.get_statistics()
            
            # Get recent events
            events = await manager.get_events(limit=1000)
            
            # Filter to last 24 hours
            recent_events = [
                e for e in events
                if e.timestamp >= start_time
            ]
            
            report = {
                "date": start_time.strftime("%Y-%m-%d"),
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats,
                "events_summary": {
                    "total": len(recent_events),
                    "by_type": {},
                    "by_severity": {}
                }
            }
            
            # Aggregate events
            for event in recent_events:
                event_type = event.event_type
                severity = event.severity
                
                if event_type not in report["events_summary"]["by_type"]:
                    report["events_summary"]["by_type"][event_type] = 0
                report["events_summary"]["by_type"][event_type] += 1
                
                if severity not in report["events_summary"]["by_severity"]:
                    report["events_summary"]["by_severity"][severity] = 0
                report["events_summary"]["by_severity"][severity] += 1
            
            logger.info("Daily canary report generated successfully")
            return report
        
        result = asyncio.run(_generate())
        return result
        
    except Exception as exc:
        logger.error(f"Error generating report: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_daily_canary_report")
            return {"error": str(exc)}


# Task 5: Alert on Stuck Deployments
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def alert_stuck_deployments(self, max_hours: int = 24):
    """
    Alert on deployments stuck in the same state for too long.
    
    Runs: Every hour
    """
    try:
        logger.info("Checking for stuck deployments")
        
        async def _check():
            manager = await get_canary_manager()
            
            stuck = []
            cutoff = datetime.utcnow() - timedelta(hours=max_hours)
            
            for canary_id, deployment in manager.deployments.items():
                if deployment.status == CanaryStatus.RUNNING:
                    # Check last event
                    events = await manager.get_events(
                        canary_id=canary_id,
                        limit=1
                    )
                    
                    if events and events[0].timestamp < cutoff:
                        stuck.append({
                            "canary_id": canary_id,
                            "name": deployment.name,
                            "current_step": deployment.current_step,
                            "last_activity": events[0].timestamp.isoformat()
                        })
            
            if stuck:
                logger.warning(f"Found {len(stuck)} stuck deployments")
            
            return {
                "stuck_count": len(stuck),
                "deployments": stuck
            }
        
        result = asyncio.run(_check())
        logger.info(f"Stuck deployment check completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error checking stuck deployments: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for alert_stuck_deployments")
            return {"error": str(exc)}


# Celery Beat Schedule Configuration
"""
Add to Celery configuration:

CELERY_BEAT_SCHEDULE = {
    'health-analysis': {
        'task': 'api.tasks.canary_deployment_tasks.automated_health_analysis',
        'schedule': 300.0,  # Every 5 minutes
    },
    'auto-advance': {
        'task': 'api.tasks.canary_deployment_tasks.auto_advance_steps',
        'schedule': 600.0,  # Every 10 minutes
    },
    'cleanup-old': {
        'task': 'api.tasks.canary_deployment_tasks.cleanup_old_deployments',
        'schedule': 86400.0,  # Daily
    },
    'daily-report': {
        'task': 'api.tasks.canary_deployment_tasks.generate_daily_canary_report',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'alert-stuck': {
        'task': 'api.tasks.canary_deployment_tasks.alert_stuck_deployments',
        'schedule': 3600.0,  # Hourly
    },
}
"""
