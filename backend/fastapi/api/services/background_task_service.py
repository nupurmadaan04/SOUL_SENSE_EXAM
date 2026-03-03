"""
Background Task Service - Manages asynchronous job execution and tracking.
Migrated to Async SQLAlchemy 2.0.
"""

import uuid
import logging
import traceback
import json
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, List
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.exc import SQLAlchemyError

from ..models import BackgroundJob, User
from ..services.db_service import AsyncSessionLocal

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
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
    """

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: int,
        task_type: TaskType,
        params: Optional[Dict[str, Any]] = None
    ) -> BackgroundJob:
        """Create a new background task."""
        job_id = str(uuid.uuid4())
        
        job = BackgroundJob(
            job_id=job_id,
            user_id=user_id,
            task_type=task_type.value,
            status=TaskStatus.PENDING.value,
            params=json.dumps(params) if params else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"Created background task {job_id} of type {task_type.value} for user {user_id}")
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
        
        logger.info(f"Updated task {job_id} to status {status.value}")
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
        **kwargs
    ) -> None:
        """Execute task function asynchronously."""
        async with AsyncSessionLocal() as db:
            try:
                await BackgroundTaskService.update_task_status(
                    db, job_id, TaskStatus.PROCESSING
                )
                
                logger.info(f"Starting execution of task {job_id}")
                
                # If task_fn is async, await it, else run it sync
                if hasattr(task_fn, '__call__') and (
                    getattr(task_fn, '__code__', None) and 
                    task_fn.__code__.co_flags & 0x80 # CO_COROUTINE
                ) or hasattr(task_fn, '__name__') and task_fn.__name__ == 'wrapped': # simplistic check for decorators
                     result = await task_fn(*args, **kwargs)
                else:
                     # For legacy sync functions or those not easily detectable as async
                     import asyncio
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
                
                logger.info(f"Task {job_id} completed successfully")
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                error_trace = traceback.format_exc()
                
                logger.error(f"Task {job_id} failed: {error_msg}\n{error_trace}")
                
                await BackgroundTaskService.update_task_status(
                    db, job_id, TaskStatus.FAILED, error_message=error_msg
                )

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
            BackgroundJob.status.in_([TaskStatus.PENDING.value, TaskStatus.PROCESSING.value])
        )
        
        if user_id:
            stmt = stmt.filter(BackgroundJob.user_id == user_id)
        
        res = await db.execute(stmt)
        return res.scalar() or 0
