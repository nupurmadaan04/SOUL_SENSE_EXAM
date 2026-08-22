"""
Tasks Router - Background task status polling and management.
Migrated to Async SQLAlchemy 2.0.
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

from ..services.db_service import get_db
from ..services.background_task_service import (
    BackgroundTaskService,
    TaskStatus,
    TaskType
)
from ..models import User, BackgroundJob
from .auth import get_current_user, require_admin
from ..utils.timestamps import normalize_utc_iso
try:
    from ...app.core import NotFoundError, ValidationError
except ImportError:
    from backend.fastapi.app.core import NotFoundError, ValidationError
from pydantic import BaseModel, Field
from ..services.outbox_relay_service import OutboxRelayService

router = APIRouter()
logger = logging.getLogger("api.tasks")


# ============================================================================
# Response Models
# ============================================================================

class TaskStatusResponse(BaseModel):
    """Response schema for task status."""
    job_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task (export_pdf, send_email, etc.)")
    status: str = Field(..., description="Task status: pending, processing, completed, failed")
    progress: int = Field(0, description="Progress percentage (0-100)")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data (if completed)")
    error_message: Optional[str] = Field(None, description="Error message (if failed)")
    created_at: Optional[str] = Field(None, description="When the task was created")
    started_at: Optional[str] = Field(None, description="When the task started processing")
    completed_at: Optional[str] = Field(None, description="When the task finished")
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Response schema for task list."""
    total: int = Field(..., description="Total number of tasks returned")
    tasks: List[TaskStatusResponse] = Field(..., description="List of tasks")


class PendingTasksResponse(BaseModel):
    """Response schema for pending tasks count."""
    pending_count: int = Field(..., description="Number of pending/processing tasks")


# ============================================================================
# Utility Functions
# ============================================================================

def _parse_json_field(field: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse a JSON string field to dict, returning None on failure."""
    if not field:
        return None
    try:
        return json.loads(field)
    except (json.JSONDecodeError, TypeError):
        return None


# ============================================================================
# Task Status Polling Endpoints
# ============================================================================

@router.get("/{job_id}", response_model=TaskStatusResponse)
async def get_task_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a background task."""
    task = await BackgroundTaskService.get_task(db, job_id, user_id=current_user.id)
    
    if not task:
        raise NotFoundError(
            resource="Task",
            resource_id=job_id,
            details=[{"message": "Task not found or you don't have access to it"}]
        )
    
    return TaskStatusResponse(
        job_id=task.job_id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress or 0,
        result=_parse_json_field(task.result),
        error_message=task.error_message,
        created_at=normalize_utc_iso(task.created_at),
        started_at=normalize_utc_iso(task.started_at),
        completed_at=normalize_utc_iso(task.completed_at),
    )


@router.get("", response_model=TaskListResponse)
async def list_user_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all background tasks for the current user."""
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            raise ValidationError(message=f"Invalid status: {status}")
    
    type_filter = None
    if task_type:
        try:
            type_filter = TaskType(task_type)
        except ValueError:
            pass
    
    tasks = await BackgroundTaskService.get_user_tasks(
        db,
        user_id=current_user.id,
        task_type=type_filter,
        status=status_filter,
        limit=limit
    )
    
    task_responses = [
        TaskStatusResponse(
            job_id=task.job_id,
            task_type=task.task_type,
            status=task.status,
            progress=task.progress or 0,
            result=_parse_json_field(task.result),
            error_message=task.error_message,
            created_at=normalize_utc_iso(task.created_at),
            started_at=normalize_utc_iso(task.started_at),
            completed_at=normalize_utc_iso(task.completed_at),
        )
        for task in tasks
    ]
    
    return TaskListResponse(total=len(task_responses), tasks=task_responses)


@router.get("/pending/count", response_model=PendingTasksResponse)
async def get_pending_tasks_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the count of pending/processing tasks for the current user."""
    count = await BackgroundTaskService.get_pending_tasks_count(db, user_id=current_user.id)
    return PendingTasksResponse(pending_count=count)


@router.delete("/{job_id}")
async def cancel_task(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending task."""
    task = await BackgroundTaskService.get_task(db, job_id, user_id=current_user.id)
    
    if not task:
        raise NotFoundError(
            resource="Task",
            resource_id=job_id,
            details=[{"message": "Task not found or you don't have access to it"}]
        )
    
    if task.status != TaskStatus.PENDING.value:
        raise ValidationError(
            message=f"Cannot cancel task with status '{task.status}'",
            details=[{"field": "status", "error": "Only pending tasks can be cancelled"}]
        )
    
    await BackgroundTaskService.update_task_status(
        db,
        job_id,
        TaskStatus.FAILED,
        error_message="Task cancelled by user"
    )
    
    logger.info(f"Task {job_id} cancelled by user {current_user.id}")
    return {"status": "cancelled", "job_id": job_id}


# ============================================================================
# Admin Outbox Management
# ============================================================================

@router.post("/admin/outbox/retry", tags=["Admin", "Outbox"])
async def retry_failed_outbox(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    [Admin Only] Reset all 'failed' or 'dead_letter' outbox events to 'pending'.
    Useful for recovering from broad service outages (e.g. Elasticsearch down).
    """
    count = await OutboxRelayService.retry_all_failed_events(db)
    return {
        "message": f"Successfully reset {count} outbox events to pending for retry.",
        "retried_count": count,
        "triggered_by": admin_user.username,
        "timestamp": datetime.now().isoformat()
    }
