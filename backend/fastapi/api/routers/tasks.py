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
from .auth import get_current_user
from ..utils.timestamps import normalize_utc_iso
from app.core import NotFoundError, ValidationError
from pydantic import BaseModel, Field

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


@router.post("/admin/outbox/retry")
async def retry_outbox_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only recovery API to reset failed/dead-letter outbox events to pending.
    Enables manual recovery from Transactional Outbox 'purgatory'.
    """
    from fastapi import HTTPException
    from sqlalchemy import update
    from ..models import OutboxEvent

    if not current_user.is_admin:
        logger.error(f"Unauthorized access to outbox retry by user {current_user.username}")
        raise HTTPException(status_code=403, detail="Admin credentials required for this recovery operation")

    # Reset both 'failed' and 'dead_letter' events
    stmt = (
        update(OutboxEvent)
        .where(OutboxEvent.status.in_(["failed", "dead_letter"]))
        .values(
            status="pending",
            retry_count=0,
            next_retry_at=None,
            processed_at=None
        )
    )

    result = await db.execute(stmt)
    await db.commit()

    affected_rows = result.rowcount
    logger.info(f"Admin {current_user.username} triggered outbox recovery. Reset {affected_rows} events.")

    return {
        "status": "success",
        "recovered_count": affected_rows,
        "message": f"Successfully reset {affected_rows} events to pending status."
    }


@router.get("/admin/outbox/stats")
async def get_outbox_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to surface outbox queue health.

    Returns counts grouped by status, the age of the oldest pending/failed event,
    and dead-letter details so admins can spot purgatory build-up without tailing logs.
    """
    from fastapi import HTTPException
    from sqlalchemy import func, case, select as sa_select
    from ..models import OutboxEvent
    from datetime import datetime, UTC

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin credentials required")

    # Count events grouped by status
    status_stmt = sa_select(
        OutboxEvent.status,
        func.count(OutboxEvent.id).label("count")
    ).group_by(OutboxEvent.status)

    status_result = await db.execute(status_stmt)
    status_counts = {row.status: row.count for row in status_result.all()}

    # Oldest unresolved event (pending or failed) — indicates backlog age
    oldest_stmt = sa_select(
        func.min(OutboxEvent.created_at).label("oldest_created_at")
    ).filter(OutboxEvent.status.in_(["pending", "failed"]))

    oldest_result = await db.execute(oldest_stmt)
    oldest_row = oldest_result.first()
    oldest_created_at = oldest_row.oldest_created_at if oldest_row else None

    oldest_age_seconds = None
    if oldest_created_at:
        now = datetime.now(UTC)
        # Handle both timezone-aware and naive datetimes from DB
        if oldest_created_at.tzinfo is None:
            from datetime import timezone
            oldest_created_at = oldest_created_at.replace(tzinfo=timezone.utc)
        oldest_age_seconds = int((now - oldest_created_at).total_seconds())

    # Calculate purgatory risk level
    total_unresolved = status_counts.get("pending", 0) + status_counts.get("failed", 0) + status_counts.get("dead_letter", 0)
    if total_unresolved >= 10000:
        purgatory_risk = "CRITICAL"
    elif total_unresolved >= 5000:
        purgatory_risk = "WARNING"
    elif total_unresolved >= 1000:
        purgatory_risk = "ELEVATED"
    else:
        purgatory_risk = "NORMAL"

    return {
        "status_counts": {
            "pending": status_counts.get("pending", 0),
            "processed": status_counts.get("processed", 0),
            "failed": status_counts.get("failed", 0),
            "dead_letter": status_counts.get("dead_letter", 0),
        },
        "total_unresolved": total_unresolved,
        "oldest_unresolved_age_seconds": oldest_age_seconds,
        "purgatory_risk": purgatory_risk,
        "purgatory_threshold": 10000,
        "message": (
            "Purgatory threshold exceeded — admin intervention required!"
            if purgatory_risk == "CRITICAL"
            else f"Queue health: {purgatory_risk}"
        )
    }


@router.get("/admin/outbox/dead-letters")
async def list_dead_letter_events(
    limit: int = Query(50, ge=1, le=200, description="Max events to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to enumerate dead-letter outbox events for investigation.

    Returns the most recent events stuck in dead_letter status so admins can
    inspect the payloads and last_error before triggering a retry.
    """
    from fastapi import HTTPException
    from sqlalchemy import select as sa_select, desc
    from ..models import OutboxEvent

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin credentials required")

    stmt = (
        sa_select(OutboxEvent)
        .filter(OutboxEvent.status == "dead_letter")
        .order_by(desc(OutboxEvent.created_at))
        .limit(limit)
    )

    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "topic": e.topic,
                "payload": e.payload,
                "retry_count": e.retry_count,
                "last_error": e.last_error,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "next_retry_at": e.next_retry_at.isoformat() if e.next_retry_at else None,
            }
            for e in events
        ]
    }

