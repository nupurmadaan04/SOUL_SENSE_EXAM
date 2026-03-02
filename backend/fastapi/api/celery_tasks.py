import asyncio
import os
import logging
import gc
from typing import Dict, Any, Optional
from celery.exceptions import MaxRetriesExceededError
from api.celery_app import celery_app
from api.services.export_service_v2 import ExportServiceV2
from api.services.background_task_service import BackgroundTaskService, TaskStatus
from api.services.db_service import AsyncSessionLocal
from sqlalchemy import select
from api.config import get_settings_instance
from api.models import User, NotificationLog, JournalEntry
from api.services.embedding_service import embedding_service
from api.services.data_archival_service import DataArchivalService
import redis
import json
from api.utils.distributed_lock import require_lock
from api.utils.memory_guard import enforce_memory_limit

logger = logging.getLogger(__name__)

def cleanup_memory():
    """Force garbage collection and clear any cached objects."""
    gc.collect()
    # Clear any module-level caches if they exist
    # This helps prevent memory bloat from long-running processes

def notify_user_via_ws(user_id: int, message: dict):
    settings = get_settings_instance()
    try:
        r = redis.from_url(settings.redis_url)
        payload = {
            "user_id": user_id,
            "payload": message
        }
        r.publish("soulsense_ws_events", json.dumps(payload))
    except Exception as e:
        logger.error(f"Failed to notify user via WS: {e}")

def run_async(coro):
    """Run an asynchronous coroutine from a synchronous context."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # If there's an existing loop, use it
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

@celery_app.task(bind=True, max_retries=3, acks_late=True, track_started=True)
def execute_async_export_task(self, job_id: str, user_id: int, username: str, format: str, options: Dict[str, Any]):
    """
    Celery task to generate an export asynchronously.
    Implements idempotent execution and exponential backoff retry.
    """
    try:
        # Memory management: Check memory before starting
        enforce_memory_limit(threshold_mb=512)
        
        run_async(_execute_async_export_db(job_id, user_id, username, format, options))
        
        # Force garbage collection after large operations
        cleanup_memory()
        
    except Exception as exc:
        logger.error(f"Task Failed for job {job_id}: {exc}")
        # Exponential backoff: 5, 25, 125 seconds
        backoff_delay = 5 ** (self.request.retries + 1)
        try:
            # Requeue task with exponential backoff
            self.retry(exc=exc, countdown=backoff_delay)
        except MaxRetriesExceededError:
            # DLQ behavior: mark as failed and log permanently
            logger.error(f"Max retries exceeded for job {job_id}. Sending to DLQ (marked as FAILED in DB).")
            run_async(_mark_task_failed(job_id, str(exc)))


@require_lock(name="job_{job_id}", timeout=60)
async def _execute_async_export_db(job_id: str, user_id: int, username: str, format: str, options: Dict[str, Any]):
    # Proactive memory guard before starting heavy export
    enforce_memory_limit(threshold_mb=1024) 
    async with AsyncSessionLocal() as db:
        try:
            # Check for idempotency: if it's already completed
            task = await BackgroundTaskService.get_task(db, job_id)
            if task and task.status == TaskStatus.COMPLETED.value:
                logger.info(f"Task {job_id} already completed. Idempotent return.")
                return

            await BackgroundTaskService.update_task_status(db, job_id, TaskStatus.PROCESSING)
            
            stmt = select(User).filter(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            filepath, export_id = await ExportServiceV2.generate_export(
                db, user, format, options
            )
            
            result_data = {
                "filepath": filepath,
                "export_id": export_id,
                "format": format,
                "filename": os.path.basename(filepath),
                "download_url": f"/api/v1/reports/export/{export_id}/download"
            }
            
            await BackgroundTaskService.update_task_status(
                db, job_id, TaskStatus.COMPLETED, result=result_data
            )
            
            # Notify user via WebSocket
            notify_user_via_ws(user_id, {
                "type": "task_completed",
                "task_type": "export",
                "job_id": job_id,
                "message": "Your export has finished generating.",
                "download_url": result_data["download_url"],
                "filename": result_data["filename"]
            })
        except Exception as e:
            # Let the outer Celery task capture and retry
            raise e

async def _mark_task_failed(job_id: str, error_msg: str):
    async with AsyncSessionLocal() as db:
        await BackgroundTaskService.update_task_status(
            db, job_id, TaskStatus.FAILED, error_message=error_msg
        )

@celery_app.task(bind=True, max_retries=5, acks_late=True, track_started=True)
def send_notification_task(self, log_id: int, channel: str, user_id: int, content: Dict[str, str]):
    """
    Celery task to send a notification synchronously/asynchronously via worker.
    """
    try:
        # Memory management
        enforce_memory_limit(threshold_mb=256)
        
        run_async(_execute_send_notification(log_id, channel, user_id, content))
        
        # Force garbage collection
        cleanup_memory()
        
    except Exception as exc:
        logger.error(f"Notification Task Failed for log_id {log_id}: {exc}")
        backoff_delay = 5 ** (self.request.retries + 1)
        try:
            self.retry(exc=exc, countdown=backoff_delay)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for notification {log_id}. Sent to DLQ.")
            run_async(_mark_notification_failed(log_id, str(exc)))

async def _execute_send_notification(log_id: int, channel: str, user_id: int, content: Dict[str, str]):
    from datetime import datetime, UTC
    async with AsyncSessionLocal() as db:
        stmt = select(NotificationLog).where(NotificationLog.id == log_id)
        res = await db.execute(stmt)
        log = res.scalar_one_or_none()
        
        if not log:
            return
            
        try:
            import asyncio
            # MOCK Simulate network latency
            await asyncio.sleep(1.0)
            
            # Implementation for actual dispatch goes here
            if channel == 'email':
                pass
            elif channel == 'push':
                pass
            elif channel == 'in_app':
                pass
                
            log.status = "sent"
            log.sent_at = datetime.now(UTC)
            
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            raise e
            
        finally:
            await db.commit()

async def _mark_notification_failed(log_id: int, error_msg: str):
    async with AsyncSessionLocal() as db:
        stmt = select(NotificationLog).where(NotificationLog.id == log_id)
        res = await db.execute(stmt)
        log = res.scalar_one_or_none()
        if log:
            log.status = "failed"
            log.error_message = error_msg
            await db.commit()

@celery_app.task(bind=True, max_retries=3, acks_late=True, track_started=True)
def generate_archive_task(self, job_id: str, user_id: int, password: str, include_pdf: bool, include_csv: bool, include_json: bool):
    """
    Celery task to generate a secure GDPR data archive asynchronously.
    """
    try:
        # Memory management for large archive operations
        enforce_memory_limit(threshold_mb=1024)
        
        run_async(_execute_archive_generation(job_id, user_id, password, include_pdf, include_csv, include_json))
        
        # Force garbage collection after large operations
        cleanup_memory()
        
    except Exception as exc:
        logger.error(f"Archive Task Failed for job {job_id}: {exc}")
        backoff_delay = 5 ** (self.request.retries + 1)
        try:
            self.retry(exc=exc, countdown=backoff_delay)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for archive {job_id}.")
            run_async(_mark_task_failed(job_id, str(exc)))

async def _execute_archive_generation(job_id: str, user_id: int, password: str, include_pdf: bool, include_csv: bool, include_json: bool):
    async with AsyncSessionLocal() as db:
        try:
            await BackgroundTaskService.update_task_status(db, job_id, TaskStatus.PROCESSING)
            
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User {user_id} not found")
                
            filepath, export_id = await DataArchivalService.generate_comprehensive_archive(
                db=db,
                user=user,
                password=password,
                include_pdf=include_pdf,
                include_csv=include_csv,
                include_json=include_json
            )
            
            result_data = {
                "filepath": filepath,
                "export_id": export_id,
                "filename": os.path.basename(filepath),
                "download_url": f"/api/v1/archival/archive/{export_id}/download"
            }
            
            await BackgroundTaskService.update_task_status(
                db, job_id, TaskStatus.COMPLETED, result=result_data
            )
            
            # Notify user via WebSocket
            notify_user_via_ws(user_id, {
                "type": "task_completed",
                "task_type": "archival",
                "job_id": job_id,
                "message": "Your comprehensive GDPR data archive is ready.",
                "download_url": result_data["download_url"],
                "filename": result_data["filename"]
            })
        except Exception as e:
            await BackgroundTaskService.update_task_status(
                db, job_id, TaskStatus.FAILED, error_message=str(e)
            )
            raise e

@celery_app.task(bind=True, max_retries=3, acks_late=True, track_started=True, name="api.celery_tasks.archive_stale_journals")
def archive_stale_journals_task(self):
    """
    Celery task to archive stale journals to cold storage.
    Moves journals older than the threshold to S3 and clears their content.
    """
    try:
        run_async(_execute_archive_stale_journals())
        cleanup_memory()
    except Exception as exc:
        logger.error(f"Archive stale journals task failed: {exc}")
        backoff_delay = 5 ** (self.request.retries + 1)
        try:
            self.retry(exc=exc, countdown=backoff_delay)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for archive stale journals task.")

async def _execute_archive_stale_journals():
    """Execute the archival of stale journals."""
    async with AsyncSessionLocal() as db:
        try:
            archived_count = await DataArchivalService.archive_stale_journals(db)
            logger.info(f"Successfully archived {archived_count} stale journals")
            return archived_count
        except Exception as e:
            logger.error(f"Failed to archive stale journals: {e}")
            raise

@celery_app.task(bind=True, max_retries=1, name="api.celery_tasks.process_outbox_events")
def process_outbox_events(self):
    """
    Poll the outbox_events table for pending events, publish them to Kafka, 
    and mark them as processed in a single transaction-like boundary.
    This guarantees at-least-once delivery for audit events.
    """
    from api.models import OutboxEvent
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    
    settings = get_settings_instance()
    
    # We use a synchronous DB connection to avoid making the celery worker fully async
    # Adjust as needed if your codebase strictly requires AsyncSession in Celery tasks.
    # Below uses a quick async block wrapper if required, but run_async is cleaner.
    async def _async_process():
        from api.services.kafka_producer import get_kafka_producer
        producer = get_kafka_producer()
        
        async with AsyncSessionLocal() as db:
            # Query pending events (limit to 50 to avoid big locks)
            stmt = select(OutboxEvent).filter(OutboxEvent.status == 'pending').limit(50)
            result = await db.execute(stmt)
            events = result.scalars().all()
            
            if not events:
                return 0
                
            processed_count = 0
            for event in events:
                try:
                    # Push to Kafka first
                    producer.queue_event(event.payload)
                    # Once queued (or sent if queue_event is synchronous/awaitable), mark processed
                    event.status = 'processed'
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process outbox event {event.id}: {e}")
                    # Stop processing this batch on Kafka failure to maintain order and wait for retry
                    break
                    
            if processed_count > 0:
                await db.commit()
                
            return processed_count
            
    return run_async(_async_process())

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def generate_journal_embedding_task(self, journal_entry_id: int):
    """
    Celery task to generate a vector embedding for a journal entry.
    """
    try:
        run_async(_execute_journal_embedding(journal_entry_id))
    except Exception as exc:
        logger.error(f"Journal Embedding Task Failed for entry {journal_entry_id}: {exc}")
        backoff_delay = 5 ** (self.request.retries + 1)
        self.retry(exc=exc, countdown=backoff_delay)

async def _execute_journal_embedding(journal_entry_id: int):
    # Proactive memory guard for ML task
    enforce_memory_limit(threshold_mb=768)
    from datetime import datetime
    async with AsyncSessionLocal() as db:
        stmt = select(JournalEntry).where(JournalEntry.id == journal_entry_id)
        res = await db.execute(stmt)
        entry = res.scalar_one_or_none()
        
        if not entry:
            return
            
        try:
            # Generate the embedding
            # Combine title and content if title exists
            text_to_embed = f"{entry.title}: {entry.content}" if entry.title else entry.content
            embedding = await embedding_service.generate_embedding(text_to_embed)
            
            if embedding:
                entry.embedding = embedding
                entry.embedding_model = embedding_service.model_name
                entry.last_indexed_at = datetime.utcnow()
                await db.commit()
                logger.info(f"Successfully generated embedding for journal entry {journal_entry_id}")
                
                # Proactive Predictive Analytics for Burnout (#1133)
                try:
                    from .ml.burnout_detection_service import BurnoutDetectionService
                    bs = BurnoutDetectionService(db)
                    await bs.run_anomaly_detection(entry.user_id)
                except Exception as e:
                    logger.error(f"Burnout detection failed for user {entry.user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for entry {journal_entry_id}: {e}")
            raise e

@celery_app.task(name="api.celery_tasks.reindex_all_entries_task")
def reindex_all_entries_task(user_id: Optional[int] = None):
    """
    Background job to re-index all journals for a user or all users.
    Useful for system-wide migration or model updates.
    """
    async def _do_reindex():
        async with AsyncSessionLocal() as db:
            from api.services.semantic_search_service import SemanticSearchService
            count = await SemanticSearchService.reindex_journal_entries(db, user_id)
            return count

    return run_async(_do_reindex())

@celery_app.task(name="api.celery_tasks.gdpr_scrub_worker_task")
def gdpr_scrub_worker_task():
    """
    Periodic job to scrub all trace data for users marked as deleted > 30 days.
    Fulfills the "Right to be Forgotten" (GDPR #1134).
    """
    async def _execute_purge():
        from api.services.data_archival_service import DataArchivalService
        async with AsyncSessionLocal() as db:
            count = await DataArchivalService.execute_hard_purges(db)
            return count

    return run_async(_execute_purge())

@celery_app.task(name="api.celery_tasks.morning_prewarming_orchestrator")
def morning_prewarming_orchestrator():
    """
    Identifies active users based on their local time zone and schedules 
    pre-calc for their smart prompts 30 mins before 8 AM local (#1177).
    """
    return run_async(_orchestrate_prewarming())

async def _orchestrate_prewarming():
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        # Fallback for Python < 3.9 if needed
        import pytz
        def ZoneInfo(tz): return pytz.timezone(tz)
    
    async with AsyncSessionLocal() as db:
        from api.models import User, UserSettings
        # 1. Fetch all active users with their settings
        from sqlalchemy import select
        stmt = select(User.id, UserSettings.timezone).join(UserSettings).filter(User.is_active == True)
        result = await db.execute(stmt)
        user_data = result.all()
        
        count = 0
        for user_id, tz_name in user_data:
            try:
                # 2. Get local time for user
                tz = ZoneInfo(tz_name or "UTC")
                local_now = datetime.now(tz)
                
                # 3. Check if it's 7:30 AM local time (the "Predictive" window)
                # We check a 15-min window since this orchestrator runs every 15 mins
                if local_now.hour == 7 and 30 <= local_now.minute < 45:
                    prewarm_user_prompts_task.delay(user_id)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to check prewarm window for user {user_id}: {e}")
        
        logger.info(f"[Pre-warm] Orchestration complete. Scheduled {count} users.")
        return count

@celery_app.task(name="api.celery_tasks.prewarm_user_prompts_task")
def prewarm_user_prompts_task(user_id: int):
    """Calculates and caches the personalized smart prompts asynchronously."""
    return run_async(_execute_prewarm(user_id))

async def _execute_prewarm(user_id: int):
    from api.services.smart_prompt_service import SmartPromptService
    async with AsyncSessionLocal() as db:
        service = SmartPromptService(db)
        await service.prewarm_for_user(user_id)


@celery_app.task(bind=True, max_retries=3, acks_late=True, track_started=True)
def check_secrets_age_compliance(self):
    """
    Scheduled job to check secrets age and rotation compliance (#1246).

    Checks RefreshToken ages against rotation policies and alerts on violations.
    Also updates compliance metrics for dashboard monitoring.

    Runs daily via Celery Beat scheduler.
    """
    try:
        # Memory management: Check memory before starting
        enforce_memory_limit(threshold_mb=256)

        run_async(_execute_secrets_compliance_check())

        # Force garbage collection after operations
        cleanup_memory()

    except Exception as exc:
        logger.error(f"Secrets compliance check failed: {exc}")
        # Exponential backoff: 5, 25, 125 seconds
        backoff_delay = 5 ** (self.request.retries + 1)
        try:
            self.retry(exc=exc, countdown=backoff_delay)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for secrets compliance check. Task failed permanently.")


async def _execute_secrets_compliance_check():
    """
    Execute the secrets age and rotation compliance check.

    Checks all active refresh tokens and identifies those exceeding age thresholds.
    Sends alerts for violations and updates compliance metrics.
    """
    from api.services.secrets_compliance_service import secrets_compliance_service

    async with AsyncSessionLocal() as db:
        try:
            # Run compliance check using the service
            compliance_report = await secrets_compliance_service.check_compliance(db)

            # Update metrics in Redis
            await secrets_compliance_service.update_metrics(compliance_report)

            # Send alerts for violations
            violations = compliance_report.get('violations', [])
            if violations:
                await _send_compliance_alerts(db, violations, compliance_report)

            logger.info(f"Secrets compliance check completed: {compliance_report}")

            # Force rotate critically old tokens as safety measure
            if compliance_report.get('expired_tokens', 0) > 0:
                revoked_count = await secrets_compliance_service.force_rotate_expired_tokens(db)
                if revoked_count > 0:
                    logger.warning(f"Auto-revoked {revoked_count} tokens exceeding maximum age")

        except Exception as e:
            logger.error(f"Error during secrets compliance check: {e}")
            raise


async def _update_compliance_metrics(stats: dict):
    """
    Update compliance metrics in Redis for dashboard monitoring.

    Args:
        stats: Dictionary containing compliance statistics
    """
    try:
        settings = get_settings_instance()
        r = redis.from_url(settings.redis_url)

        # Store metrics with 24-hour expiration
        metrics_key = "secrets_compliance:metrics"
        r.setex(metrics_key, 86400, json.dumps(stats))

        # Also store individual metric keys for easier querying
        r.setex("secrets_compliance:total_active", 86400, stats['total_active_tokens'])
        r.setex("secrets_compliance:warnings", 86400, stats['warning_violations'])
        r.setex("secrets_compliance:critical", 86400, stats['critical_violations'])
        r.setex("secrets_compliance:expired", 86400, stats['expired_tokens'])
        r.setex("secrets_compliance:compliant", 86400, stats['compliant_tokens'])

        logger.debug(f"Updated compliance metrics: {stats}")

    except Exception as e:
        logger.error(f"Failed to update compliance metrics: {e}")


async def _send_compliance_alerts(db, violations: list, stats: dict):
    """
    Send alerts for secrets compliance violations.

    Args:
        db: Database session
        violations: List of violation dictionaries
        stats: Compliance statistics
    """
    from api.services.notification_service import NotificationService

    try:
        # Group violations by severity
        critical_violations = [v for v in violations if v['severity'] == 'critical']
        warning_violations = [v for v in violations if v['severity'] == 'warning']

        # Send critical alerts (immediate attention required)
        if critical_violations:
            await _send_critical_alert(db, critical_violations, stats)

        # Send warning alerts (scheduled maintenance)
        if warning_violations:
            await _send_warning_alert(db, warning_violations, stats)

        logger.info(f"Sent compliance alerts: {len(critical_violations)} critical, {len(warning_violations)} warnings")

    except Exception as e:
        logger.error(f"Failed to send compliance alerts: {e}")


async def _send_critical_alert(db, violations: list, stats: dict):
    """
    Send critical alerts for tokens exceeding maximum age or in critical zone.

    These require immediate action - tokens should be rotated or revoked.
    """
    try:
        # Create notification log entry
        notification = NotificationLog(
            user_id=None,  # System-wide alert
            template_name="secrets_critical_violation",
            channel="email",  # Could also send to Slack, PagerDuty, etc.
            status="pending"
        )
        db.add(notification)

        # Prepare alert message
        alert_data = {
            "alert_type": "critical",
            "total_violations": len(violations),
            "total_active_tokens": stats['total_active_tokens'],
            "violations": violations[:10],  # Limit to first 10 for email
            "compliance_rate": (stats['compliant_tokens'] / stats['total_active_tokens'] * 100) if stats['total_active_tokens'] > 0 else 0,
            "checked_at": stats['checked_at']
        }

        # In a real system, this would integrate with email service, Slack, PagerDuty, etc.
        # For now, log the alert
        logger.warning(f"CRITICAL: Secrets compliance violations detected: {alert_data}")

        # TODO: Integrate with actual alerting system (email, Slack, PagerDuty)
        # await NotificationService.send_system_alert(alert_data)

        await db.commit()

    except Exception as e:
        logger.error(f"Failed to send critical alert: {e}")
        await db.rollback()


async def _send_warning_alert(db, violations: list, stats: dict):
    """
    Send warning alerts for tokens approaching maximum age.

    These are advance notices for scheduled rotation.
    """
    try:
        # Create notification log entry
        notification = NotificationLog(
            user_id=None,  # System-wide alert
            template_name="secrets_warning_violation",
            channel="email",
            status="pending"
        )
        db.add(notification)

        # Prepare alert message
        alert_data = {
            "alert_type": "warning",
            "total_violations": len(violations),
            "total_active_tokens": stats['total_active_tokens'],
            "violations": violations[:20],  # More violations for warnings
            "compliance_rate": (stats['compliant_tokens'] / stats['total_active_tokens'] * 100) if stats['total_active_tokens'] > 0 else 0,
            "checked_at": stats['checked_at']
        }

        logger.info(f"WARNING: Secrets compliance warnings: {len(violations)} tokens need attention")

        # TODO: Integrate with actual alerting system
        # await NotificationService.send_system_alert(alert_data)

        await db.commit()

    except Exception as e:
        logger.error(f"Failed to send warning alert: {e}")
        await db.rollback()

