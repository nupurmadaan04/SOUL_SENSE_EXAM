import os
import logging
from celery import Celery
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

# Initialize Celery app
settings = get_settings_instance()

# Note: In production, these should be set via environment variables
# which are loaded into the settings object.
broker_url = settings.celery_broker_url or settings.redis_url or f"redis://{settings.redis_host}:{settings.redis_port}/1"
result_backend = settings.celery_result_backend or broker_url

app = Celery(
    "soulsense",
    broker=broker_url,
    backend=result_backend,
    include=["api.services.journal_service"] # Example: background sentiment analysis
)

# --- Memory Control Optimization ---
# To address the Linux OOM Killer Vulnerability, we configure workers 
# to restart children after a fixed number of tasks. This releases 
# any memory leaked by tasks (especially ML inferences or heavy DB operations).
app.conf.update(
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    worker_prefetch_multiplier=1, # One task at a time for predictability
    task_acks_late=True, # Ensure tasks are retried if worker is killed
    task_reject_on_worker_lost=True,
    
    # Task time limits to prevent hanging processes
    task_time_limit=300, # 5 minutes hard limit
    task_soft_time_limit=240, # 4 minutes soft limit
    
    # Track task progress
    task_track_started=True,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
