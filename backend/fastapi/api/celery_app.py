import os
import signal
import multiprocessing
import logging
from celery import Celery
from api.config import get_settings_instance

logger = logging.getLogger(__name__)

# Set multiprocessing start method to 'spawn' to prevent zombie processes
multiprocessing.set_start_method('spawn', force=True)

# Handle SIGCHLD to reap zombie processes
def sigchld_handler(signum, frame):
    """Reap zombie processes to prevent accumulation."""
    try:
        while True:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            logger.info(f"Reaped zombie process {pid} with status {status}")
    except OSError:
        # No child processes
        pass

# Register the signal handler
signal.signal(signal.SIGCHLD, sigchld_handler)

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
    # Memory management to prevent fragmentation
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory bloat
    worker_prefetch_multiplier=1,   # Prefetch only 1 task per worker
    task_time_limit=3600,           # Kill tasks that run longer than 1 hour
    task_soft_time_limit=3300,      # Soft time limit 55 minutes
    worker_disable_rate_limits=False,  # Enable rate limiting
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'process-outbox-events-frequent': {
        'task': 'api.celery_tasks.process_outbox_events',
        'schedule': 5.0, # Execute every 5 seconds
    },
    'morning-prewarming-task': {
        'task': 'api.celery_tasks.morning_prewarming_orchestrator',
        'schedule': 900.0, # Execute every 15 minutes to catch time zone windows
    },
}
