"""
Usage Telemetry Celery Tasks

Background tasks for usage aggregation, billing, and telemetry maintenance.
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

from backend.fastapi.api.utils.usage_telemetry import (
    get_telemetry_manager,
    BillingPeriodStatus,
    reset_telemetry_manager
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery('usage_telemetry')


# Task 1: Aggregate Hourly Usage
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def aggregate_hourly_usage(self):
    """
    Aggregate usage data for the past hour.
    
    Runs: Hourly
    """
    try:
        logger.info("Starting hourly usage aggregation")
        
        async def _aggregate():
            manager = await get_telemetry_manager()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Get all customers with events in period
            customers = set()
            for event in manager.events:
                if start_time <= event.timestamp <= end_time:
                    customers.add(event.customer_id)
            
            aggregated = 0
            for customer_id in customers:
                summary = await manager.get_usage_summary(
                    customer_id=customer_id,
                    start_time=start_time,
                    end_time=end_time
                )
                aggregated += summary.get("total_events", 0)
            
            return {
                "period": "hourly",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "customers_processed": len(customers),
                "events_aggregated": aggregated
            }
        
        result = asyncio.run(_aggregate())
        logger.info(f"Hourly aggregation completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in hourly aggregation: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for aggregate_hourly_usage")
            return {"error": str(exc)}


# Task 2: Close Expired Billing Periods
@app.task(bind=True, max_retries=2, default_retry_delay=300)
def close_expired_billing_periods(self):
    """
    Close billing periods that have reached their end date.
    
    Runs: Daily
    """
    try:
        logger.info("Starting close of expired billing periods")
        
        async def _close():
            manager = await get_telemetry_manager()
            
            now = datetime.utcnow()
            closed = 0
            
            for period_id, period in manager.billing_periods.items():
                if period.status == BillingPeriodStatus.OPEN:
                    if period.end_date <= now:
                        await manager.close_billing_period(period_id)
                        closed += 1
                        logger.info(f"Closed billing period: {period_id}")
            
            return {"closed_periods": closed}
        
        result = asyncio.run(_close())
        logger.info(f"Expired period closure completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error closing periods: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for close_expired_billing_periods")
            return {"error": str(exc)}


# Task 3: Check Quota Alerts
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def check_quota_alerts(self):
    """
    Check for quotas approaching or exceeding limits.
    
    Runs: Every 15 minutes
    """
    try:
        logger.info("Starting quota alert check")
        
        async def _check():
            manager = await get_telemetry_manager()
            
            alerts = []
            
            for quota_id, quota in manager.quotas.items():
                if quota.alert_threshold and not quota.alert_triggered:
                    usage_pct = (quota.current_usage / quota.limit_quantity) * 100
                    
                    if usage_pct >= quota.alert_threshold:
                        quota.alert_triggered = True
                        alerts.append({
                            "quota_id": quota_id,
                            "customer_id": quota.customer_id,
                            "meter_id": quota.meter_id,
                            "usage_percentage": round(float(usage_pct), 2),
                            "threshold": float(quota.alert_threshold)
                        })
                        logger.warning(
                            f"Quota alert: {quota.customer_id} at {usage_pct:.1f}%"
                        )
            
            return {
                "alerts_triggered": len(alerts),
                "alerts": alerts
            }
        
        result = asyncio.run(_check())
        logger.info(f"Quota alert check completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error checking quota alerts: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for check_quota_alerts")
            return {"error": str(exc)}


# Task 4: Reset Daily Quotas
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def reset_daily_quotas(self):
    """
    Reset daily quotas at midnight.
    
    Runs: Daily at midnight
    """
    try:
        logger.info("Starting daily quota reset")
        
        async def _reset():
            manager = await get_telemetry_manager()
            
            reset_count = 0
            now = datetime.utcnow()
            
            for quota_id, quota in manager.quotas.items():
                if quota.period_type == "daily":
                    if quota.period_end and now >= quota.period_end:
                        # Reset quota
                        quota.current_usage = 0
                        quota.period_start = now
                        quota.period_end = now + timedelta(days=1)
                        quota.alert_triggered = False
                        reset_count += 1
            
            return {"quotas_reset": reset_count}
        
        result = asyncio.run(_reset())
        logger.info(f"Daily quota reset completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error resetting quotas: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for reset_daily_quotas")
            return {"error": str(exc)}


# Task 5: Generate Daily Usage Report
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_daily_usage_report(self):
    """
    Generate daily usage report for all customers.
    
    Runs: Daily
    """
    try:
        logger.info("Starting daily usage report generation")
        
        async def _generate():
            manager = await get_telemetry_manager()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
            
            # Get unique customers
            customers = set(e.customer_id for e in manager.events)
            
            reports = []
            for customer_id in customers:
                summary = await manager.get_usage_summary(
                    customer_id=customer_id,
                    start_time=start_time,
                    end_time=end_time
                )
                reports.append({
                    "customer_id": customer_id,
                    "summary": summary
                })
            
            return {
                "date": start_time.strftime("%Y-%m-%d"),
                "customers_reported": len(reports),
                "reports": reports[:10]  # Limit for response size
            }
        
        result = asyncio.run(_generate())
        logger.info(f"Daily report generation completed")
        return result
        
    except Exception as exc:
        logger.error(f"Error generating report: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for generate_daily_usage_report")
            return {"error": str(exc)}


# Task 6: Cleanup Old Events
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_events(self, days_old: int = 90):
    """
    Archive or remove old usage events.
    
    Runs: Weekly
    """
    try:
        logger.info(f"Starting cleanup of events older than {days_old} days")
        
        async def _cleanup():
            manager = await get_telemetry_manager()
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            archived = 0
            
            # Mark old events as archived
            for event in manager.events:
                if event.timestamp < cutoff_date:
                    if not event.properties.get("archived"):
                        event.properties["archived"] = True
                        event.properties["archived_at"] = datetime.utcnow().isoformat()
                        archived += 1
            
            return {
                "archived": archived,
                "cutoff_date": cutoff_date.isoformat()
            }
        
        result = asyncio.run(_cleanup())
        logger.info(f"Old events cleanup completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error cleaning up events: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for cleanup_old_events")
            return {"error": str(exc)}


# Task 7: Validate Event Integrity
@app.task(bind=True, max_retries=2, default_retry_delay=60)
def validate_event_integrity(self, start_date: str = None, end_date: str = None):
    """
    Validate integrity of usage events by checking checksums.
    
    Runs: Daily
    """
    try:
        logger.info("Starting event integrity validation")
        
        async def _validate():
            manager = await get_telemetry_manager()
            
            from backend.fastapi.api.utils.usage_telemetry import UsageEventValidator
            
            # Filter events by date if specified
            events = manager.events
            if start_date:
                start = datetime.fromisoformat(start_date)
                events = [e for e in events if e.timestamp >= start]
            if end_date:
                end = datetime.fromisoformat(end_date)
                events = [e for e in events if e.timestamp <= end]
            
            valid = 0
            invalid = 0
            
            for event in events:
                expected_checksum = UsageEventValidator.calculate_checksum(event)
                if event.checksum == expected_checksum:
                    valid += 1
                else:
                    invalid += 1
                    logger.error(f"Checksum mismatch for event: {event.event_id}")
            
            return {
                "validated": len(events),
                "valid": valid,
                "invalid": invalid
            }
        
        result = asyncio.run(_validate())
        logger.info(f"Event integrity validation completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error validating events: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for validate_event_integrity")
            return {"error": str(exc)}


# Task 8: Export Billing Data
@app.task(bind=True, max_retries=3, default_retry_delay=300)
def export_billing_data(self, period_id: str = None):
    """
    Export billing data to external system.
    
    Runs: On-demand or scheduled
    """
    try:
        logger.info(f"Starting billing data export for period: {period_id}")
        
        async def _export():
            manager = await get_telemetry_manager()
            
            if period_id:
                period = manager.billing_periods.get(period_id)
                periods = [period] if period else []
            else:
                # Export all closed periods not yet exported
                periods = [
                    p for p in manager.billing_periods.values()
                    if p.status == BillingPeriodStatus.CLOSED
                    and not p.metadata.get("exported")
                ]
            
            exported = 0
            for period in periods:
                # Mark as exported
                period.metadata["exported"] = True
                period.metadata["exported_at"] = datetime.utcnow().isoformat()
                exported += 1
            
            return {
                "periods_exported": exported
            }
        
        result = asyncio.run(_export())
        logger.info(f"Billing data export completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Error exporting billing data: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for export_billing_data")
            return {"error": str(exc)}


# Celery Beat Schedule Configuration
"""
Add to Celery configuration:

CELERY_BEAT_SCHEDULE = {
    'aggregate-hourly-usage': {
        'task': 'api.tasks.usage_telemetry_tasks.aggregate_hourly_usage',
        'schedule': 3600.0,  # Hourly
    },
    'close-expired-periods': {
        'task': 'api.tasks.usage_telemetry_tasks.close_expired_billing_periods',
        'schedule': 86400.0,  # Daily
    },
    'check-quota-alerts': {
        'task': 'api.tasks.usage_telemetry_tasks.check_quota_alerts',
        'schedule': 900.0,  # Every 15 minutes
    },
    'reset-daily-quotas': {
        'task': 'api.tasks.usage_telemetry_tasks.reset_daily_quotas',
        'schedule': crontab(hour=0, minute=0),  # Midnight
    },
    'daily-usage-report': {
        'task': 'api.tasks.usage_telemetry_tasks.generate_daily_usage_report',
        'schedule': crontab(hour=1, minute=0),  # 1 AM
    },
    'cleanup-old-events': {
        'task': 'api.tasks.usage_telemetry_tasks.cleanup_old_events',
        'schedule': 604800.0,  # Weekly
    },
    'validate-event-integrity': {
        'task': 'api.tasks.usage_telemetry_tasks.validate_event_integrity',
        'schedule': 86400.0,  # Daily
    },
}
"""
