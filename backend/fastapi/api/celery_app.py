import os
from celery import Celery
from api.config import get_settings_instance

settings = get_settings_instance()

# Configure Celery with Redis/RabbitMQ based on config.
# Note: For Dead Letter Queue or Retry logic, Celery retries via `max_retries`
# failed tasks can also be routed to a separate queue using task routes if needed.
celery_app = Celery(
    "soulsense_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["api.celery_tasks"]
)

# Optional configuration for Idempotency and DLQ-like behavior
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True, # Important for idempotent tasks; won't ack until successful
    task_reject_on_worker_lost=True,
    task_default_retry_delay=5, # Overriden by task exponential backoff
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'process-outbox-events-frequent': {
        'task': 'api.celery_tasks.process_outbox_events',
        'schedule': 5.0, # Execute every 5 seconds
    },
    'archive-stale-journals-weekly': {
        'task': 'api.celery_tasks.archive_stale_journals',
        'schedule': crontab(hour=3, minute=0, day_of_week='sun'), # Sunday at 3 AM (#1125)
    },
}
