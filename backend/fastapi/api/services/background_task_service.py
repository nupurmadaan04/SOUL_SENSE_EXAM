"""
Background Task Service - Manages asynchronous job execution and tracking.
Migrated to Async SQLAlchemy 2.0.

Issue #1363: Request Context Propagation into Async Tasks
- Captures request context when tasks are created
- Propagates context to async task execution
- Maintains traceability across async boundaries
- Supports correlation IDs and distributed tracing
"""

import asyncio
import uuid
import logging
import traceback
import json
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, List
from functools import wraps
from fastapi import BackgroundTasks

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError

from ..models import BackgroundJob, User
from ..services.db_service import AsyncSessionLocal
from ..utils.context_propagation import (
    RequestContext,
    capture_request_context,
    propagate_context,
    get_request_id,
    get_user_id,
    get_correlation_id,
)

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """Types of background tasks."""
    EXPORT_PDF = "export_pdf"
    EXPORT_CSV = "export_csv"
    EXPORT_JSON = "export_json"
    EXPORT_XML = "export_xml"
    EXPORT_HTML = "export_html"
    SEND_EMAIL = "send_email"
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"


class BackgroundTaskService:
    """
    Service for managing background task execution and tracking.
    
    Issue #1363: Supports request context propagation to maintain traceability
    across async boundaries. Context is captured when tasks are created and
    propagated when tasks are executed.
    """
    # Concurrency limiting configuration
    MAX_GLOBAL_HEAVY_TASKS = 5
    MAX_USER_TASKS = 2

    # Internal semaphore management
    _global_heavy_semaphore: Optional[asyncio.Semaphore] = None
    _user_semaphores: Dict[int, asyncio.Semaphore] = {}
    _semaphore_lock = asyncio.Lock()

    @classmethod
    def _get_global_semaphore(cls) -> asyncio.Semaphore:
        """Lazy initialization of the global heavy task semaphore."""
        if cls._global_heavy_semaphore is None:
            cls._global_heavy_semaphore = asyncio.Semaphore(cls.MAX_GLOBAL_HEAVY_TASKS)
        return cls._global_heavy_semaphore

    @classmethod
    async def _get_user_semaphore(cls, user_id: int) -> asyncio.Semaphore:
        """Lazy initialization of per-user semaphores with thread-safe locking."""
        async with cls._semaphore_lock:
            if user_id not in cls._user_semaphores:
                cls._user_semaphores[user_id] = asyncio.Semaphore(cls.MAX_USER_TASKS)
            return cls._user_semaphores[user_id]

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: int,
        task_type: TaskType,
        params: Optional[Dict[str, Any]] = None,
        request_context: Optional[RequestContext] = None
    ) -> BackgroundJob:
        """
        Create a new background task.
        
        Issue #1363: Optionally captures request context for propagation to async task.
        
        Args:
            db: Database session
            user_id: User ID for the task
            task_type: Type of task
            params: Task parameters
            request_context: Optional request context for trace propagation
        """
        job_id = str(uuid.uuid4())
        
        # Capture request context if not provided
        if request_context is None:
            request_context = capture_request_context()
        
        # Store context in params for later propagation
        context_data = request_context.to_dict()
        
        # Merge with existing params
        merged_params = params.copy() if params else {}
        merged_params["__request_context"] = context_data
        
        job = BackgroundJob(
            job_id=job_id,
            user_id=user_id,
            task_type=task_type.value,
            status=TaskStatus.PENDING.value,
            params=json.dumps(merged_params) if merged_params else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Log with context info
        log_extra = {
            "job_id": job_id,
            "task_type": task_type.value,
            "user_id": user_id,
            "request_id": request_context.request_id,
        }
        if request_context.correlation_id:
            log_extra["correlation_id"] = request_context.correlation_id
        
        logger.info(
            f"Created background task {job_id} of type {task_type.value} for user {user_id}",
            extra=log_extra
        )
        return job

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        job_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        progress: Optional[int] = None
    ) -> Optional[BackgroundJob]:
        """Update task status."""
        stmt = select(BackgroundJob).filter(BackgroundJob.job_id == job_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        
        if not job:
            logger.warning(f"Job {job_id} not found for status update")
            return None
        
        job.status = status.value
        job.updated_at = datetime.now(UTC)
        
        if result is not None:
            job.result = json.dumps(result)
        
        if error_message is not None:
            job.error_message = error_message
            
        if progress is not None:
            job.progress = min(100, max(0, progress))
        
        if status == TaskStatus.COMPLETED:
            job.completed_at = datetime.now(UTC)
            job.progress = 100
        elif status == TaskStatus.FAILED:
            job.completed_at = datetime.now(UTC)
        elif status == TaskStatus.PROCESSING:
            job.started_at = datetime.now(UTC)
        
        await db.commit()
        await db.refresh(job)
        
        # Log with request_id from context if available
        log_extra = {"job_id": job_id, "status": status.value}
        request_id = get_request_id()
        if request_id:
            log_extra["request_id"] = request_id
        
        logger.info(f"Updated task {job_id} to status {status.value}", extra=log_extra)
        return job

    @staticmethod
    async def get_task(db: AsyncSession, job_id: str, user_id: Optional[int] = None) -> Optional[BackgroundJob]:
        """Get task by ID."""
        stmt = select(BackgroundJob).filter(BackgroundJob.job_id == job_id)
        if user_id is not None:
            stmt = stmt.filter(BackgroundJob.user_id == user_id)
        
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_user_tasks(
        db: AsyncSession,
        user_id: int,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 50
    ) -> List[BackgroundJob]:
        """Get user tasks."""
        stmt = select(BackgroundJob).filter(BackgroundJob.user_id == user_id)
        
        if task_type:
            stmt = stmt.filter(BackgroundJob.task_type == task_type.value)
        
        if status:
            stmt = stmt.filter(BackgroundJob.status == status.value)
        
        stmt = stmt.order_by(desc(BackgroundJob.created_at)).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def execute_task(
        job_id: str,
        task_fn: Callable,
        *args,
        request_context: Optional[RequestContext] = None,
        **kwargs
    ) -> None:
        """
        Execute task function asynchronously with concurrency limiting and fairness.
        Implements a Semaphore-based limiter to prevent event loop starvation and memory exhaustion.
        
        Issue #1363: Supports request context propagation to maintain traceability.
        
        Args:
            job_id: Job ID to execute
            task_fn: Function to execute
            *args: Positional arguments for task_fn
            request_context: Optional request context for propagation
            **kwargs: Keyword arguments for task_fn
        """
        # Step 1: Identification (Fetch job metadata without holding the session open)
        async with AsyncSessionLocal() as db:
            job = await BackgroundTaskService.get_task(db, job_id)
            if not job:
                logger.error(f"Background task execution failed: Job {job_id} not found")
                return
            
            user_id = job.user_id
            task_type = job.task_type
            
            # Extract request context from params if available
            if job.params:
                try:
                    params = json.loads(job.params)
                    context_data = params.get("__request_context")
                    if context_data and not request_context:
                        request_context = RequestContext.from_dict(context_data)
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Determine if this is a "heavy" task that requires global limiting
            heavy_types = [
                TaskType.EXPORT_PDF.value, 
                TaskType.EXPORT_CSV.value, 
                TaskType.DATA_ANALYSIS.value,
                TaskType.REPORT_GENERATION.value
            ]
            is_heavy = task_type in heavy_types

        # Step 2: Queueing & Concurrency Control
        if is_heavy:
            # Set status to QUEUED if it's going to wait for a slot
            async with AsyncSessionLocal() as db:
                await BackgroundTaskService.update_task_status(db, job_id, TaskStatus.QUEUED)
            
            logger.info(f"Task {job_id} ({task_type}) for user {user_id} moved to QUEUE")
            
            global_sem = BackgroundTaskService._get_global_semaphore()
            user_sem = await BackgroundTaskService._get_user_semaphore(user_id)
            
            # Use nested context managers for both levels of fairness
            async with global_sem:
                async with user_sem:
                    await BackgroundTaskService._run_task_internal(
                        job_id, task_fn, *args, request_context=request_context, **kwargs
                    )
        else:
            # For non-heavy tasks, we still apply user-level fairness but skip global heavy limit
            user_sem = await BackgroundTaskService._get_user_semaphore(user_id)
            async with user_sem:
                await BackgroundTaskService._run_task_internal(
                    job_id, task_fn, *args, request_context=request_context, **kwargs
                )

    @staticmethod
    async def _run_task_internal(
        job_id: str,
        task_fn: Callable,
        *args,
        request_context: Optional[RequestContext] = None,
        **kwargs
    ) -> None:
        """
        Internal execution logic with status updates and error handling.
        
        Issue #1363: Propagates request context to task execution.
        """
        async def execute_with_context():
            """Execute task function within propagated context."""
            async with AsyncSessionLocal() as db:
                try:
                    await BackgroundTaskService.update_task_status(
                        db, job_id, TaskStatus.PROCESSING
                    )
                    
                    # Log with propagated context
                    request_id = get_request_id()
                    correlation_id = get_correlation_id()
                    log_msg = f"Starting execution of task {job_id}"
                    log_extra = {"job_id": job_id}
                    if request_id:
                        log_extra["request_id"] = request_id
                    if correlation_id:
                        log_extra["correlation_id"] = correlation_id
                    
                    logger.info(log_msg, extra=log_extra)
                    
                    # If task_fn is async, await it, else run it sync
                    if hasattr(task_fn, '__call__') and (
                        getattr(task_fn, '__code__', None) and 
                        task_fn.__code__.co_flags & 0x80 # CO_COROUTINE
                    ) or hasattr(task_fn, '__name__') and task_fn.__name__ == 'wrapped': # simplistic check for decorators
                         result = await task_fn(*args, **kwargs)
                    else:
                         if asyncio.iscoroutinefunction(task_fn):
                             result = await task_fn(*args, **kwargs)
                         else:
                             result = task_fn(*args, **kwargs)
                    
                    result_data = None
                    if isinstance(result, dict):
                        result_data = result
                    elif isinstance(result, tuple) and len(result) == 2:
                        result_data = {"filepath": result[0], "export_id": result[1]}
                    elif result is not None:
                        result_data = {"result": str(result)}
                    
                    await BackgroundTaskService.update_task_status(
                        db, job_id, TaskStatus.COMPLETED, result=result_data
                    )
                    
                    # Log completion with context
                    log_msg = f"Task {job_id} completed successfully"
                    log_extra = {"job_id": job_id}
                    request_id = get_request_id()
                    if request_id:
                        log_extra["request_id"] = request_id
                    
                    logger.info(log_msg, extra=log_extra)
                    
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    error_trace = traceback.format_exc()
                    
                    # Log error with context
                    log_extra = {"job_id": job_id}
                    request_id = get_request_id()
                    if request_id:
                        log_extra["request_id"] = request_id
                    
                    logger.error(
                        f"Task {job_id} failed: {error_msg}\n{error_trace}",
                        extra=log_extra
                    )
                    
                    await BackgroundTaskService.update_task_status(
                        db, job_id, TaskStatus.FAILED, error_message=error_msg
                    )
        
        # Execute with context propagation if context is available
        if request_context:
            await propagate_context(request_context, execute_with_context)
        else:
            await execute_with_context()

    @staticmethod
    async def cleanup_old_tasks(db: AsyncSession, days: int = 30) -> int:
        """Cleanup old tasks."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        
        stmt = delete(BackgroundJob).filter(
            BackgroundJob.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]),
            BackgroundJob.created_at < cutoff
        )
        
        res = await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Cleaned up {res.rowcount} old background tasks")
        return res.rowcount

    @staticmethod
    async def get_pending_tasks_count(db: AsyncSession, user_id: Optional[int] = None) -> int:
        """Get active tasks count."""
        stmt = select(func.count(BackgroundJob.id)).filter(
            BackgroundJob.status.in_([TaskStatus.PENDING.value, TaskStatus.QUEUED.value, TaskStatus.PROCESSING.value])
        )
        
        if user_id:
            stmt = stmt.filter(BackgroundJob.user_id == user_id)
        
        res = await db.execute(stmt)
        return res.scalar() or 0


def background_task(task_type: TaskType):
    """
    Decorator to wrap a function as a background task.
    Automatically handles task creation and scheduling with concurrency limits.
    
    Issue #1363: Supports request context propagation.
    
    Args:
        task_type: Type of background task
        
    Returns:
        Decorated function that creates and schedules a background task
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapped(
            background_tasks: BackgroundTasks,
            db: AsyncSession,
            user_id: int,
            *args,
            request_context: Optional[RequestContext] = None,
            **kwargs
        ) -> str:
            # Capture context if not provided
            if request_context is None:
                request_context = capture_request_context()
            
            # Create the task record with context
            params = kwargs.get('params')
            job = await BackgroundTaskService.create_task(
                db=db,
                user_id=user_id,
                task_type=task_type,
                params=params,
                request_context=request_context
            )
            
            # Log with context info
            log_extra = {
                "job_id": job.job_id,
                "user_id": user_id,
                "task_type": task_type.value,
                "request_id": request_context.request_id,
            }
            if request_context.correlation_id:
                log_extra["correlation_id"] = request_context.correlation_id
            
            logger.info(
                f"Scheduling background task {job.job_id} via asyncio.create_task",
                extra=log_extra
            )
            
            # Execute via asyncio.create_task with context propagation
            asyncio.create_task(BackgroundTaskService.execute_task(
                job.job_id,
                func,
                *args,
                request_context=request_context,
                **kwargs
            ))
            
            # Call add_task on background_tasks for logging/monitoring if provided
            if background_tasks:
                # We don't actually want FastAPI to run it again, but we might want it 
                # to track that something happened. However, per the problem description 
                # and tests, we should at least simulate the call if expected.
                # In a real app, you'd choose one or the other.
                # background_tasks.add_task(lambda: logger.debug(f"Task {job.job_id} scheduled"))
                pass
                
            return job.job_id
        return wrapped
    return decorator


class TracedBackgroundTask:
    """
    Wrapper for background tasks with automatic context propagation.
    
    Issue #1363: Provides a simple interface for scheduling background tasks
    with automatic request context capture and propagation.
    
    Usage:
        # In route handler
        traced_task = TracedBackgroundTask(process_data, TaskType.DATA_ANALYSIS)
        job_id = await traced_task.schedule(background_tasks, db, user_id, data)
        
        # The task will execute with the same request_id and correlation_id
        # as the original request.
    """
    
    def __init__(
        self,
        task_fn: Callable,
        task_type: TaskType,
        request_context: Optional[RequestContext] = None
    ):
        """
        Initialize traced background task.
        
        Args:
            task_fn: Function to execute
            task_type: Type of task
            request_context: Optional request context (auto-captured if not provided)
        """
        self.task_fn = task_fn
        self.task_type = task_type
        self.request_context = request_context or capture_request_context()
    
    async def schedule(
        self,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
        user_id: int,
        *args,
        **kwargs
    ) -> str:
        """
        Schedule the background task with context propagation.
        
        Args:
            background_tasks: FastAPI BackgroundTasks
            db: Database session
            user_id: User ID
            *args: Positional arguments for task_fn
            **kwargs: Keyword arguments for task_fn
            
        Returns:
            Job ID of the scheduled task
        """
        job = await BackgroundTaskService.create_task(
            db=db,
            user_id=user_id,
            task_type=self.task_type,
            params=kwargs.get('params'),
            request_context=self.request_context
        )
        
        log_extra = {
            "job_id": job.job_id,
            "user_id": user_id,
            "task_type": self.task_type.value,
            "request_id": self.request_context.request_id,
        }
        if self.request_context.correlation_id:
            log_extra["correlation_id"] = self.request_context.correlation_id
        
        logger.info(
            f"Scheduling traced background task {job.job_id}",
            extra=log_extra
        )
        
        # Schedule with context propagation
        asyncio.create_task(BackgroundTaskService.execute_task(
            job.job_id,
            self.task_fn,
            *args,
            request_context=self.request_context,
            **kwargs
        ))
        
        return job.job_id
