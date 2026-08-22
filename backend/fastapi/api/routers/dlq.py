"""
Dead-Letter Queue (DLQ) Management API - Issue #1355

Admin endpoints for managing dead-lettered tasks:
- List DLQ tasks with filtering
- View DLQ statistics
- Manually replay tasks
- Discard unrecoverable tasks
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from ..models import User
from .auth import get_current_user, require_admin
from ..services.db_service import get_db
from ..services.dlq_service import DLQService

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Dead-Letter Queue (Admin)"],
)


@router.get("/tasks", status_code=status.HTTP_200_OK)
async def list_dlq_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    dlq_status: Optional[str] = Query(None, description="Filter by status (pending_replay, archived, discarded)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to retrieve"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    List dead-lettered tasks with optional filtering.
    
    **Requires:** Admin role
    
    Query Parameters:
    - task_type: Filter by task type (e.g., "export_pdf", "send_notification")
    - dlq_status: Filter by status ("pending_replay", "archived", "discarded")
    - user_id: Filter by user ID
    - limit: Results per page (default: 50, max: 500)
    - offset: Pagination offset (default: 0)
    
    Returns:
    - tasks: List of DLQ task records
    - total_count: Total number of matching records
    """
    try:
        tasks, total_count = await DLQService.get_dlq_tasks(
            db=db,
            task_type=task_type,
            status=dlq_status,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        
        return {
            "tasks": [task.to_dict() for task in tasks],
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to list DLQ tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DLQ tasks"
        )


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_dlq_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get DLQ health metrics and statistics.
    
    **Requires:** Admin role
    
    Returns:
    - total_count: Total tasks in DLQ
    - pending_replay_count: Tasks awaiting replay
    - archived_count: Archived/cleaned up tasks
    - discarded_count: Discarded tasks
    - by_task_type: Breakdown by task type
    - oldest_task_age_hours: Age of oldest pending task
    - growth_rate_per_hour: Tasks added in last hour
    - timestamp: When stats were computed
    """
    try:
        stats = await DLQService.get_dlq_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Failed to get DLQ stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DLQ statistics"
        )


@router.post("/tasks/{task_id}/replay", status_code=status.HTTP_200_OK)
async def replay_dlq_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Manually replay (requeue) a task from the DLQ.
    
    **Requires:** Admin role
    
    Path Parameters:
    - task_id: Celery task ID to replay
    
    Response:
    - success: Boolean indicating if replay was initiated
    - message: Status message
    - replay_count: Number of replay attempts for this task
    
    Error Conditions:
    - Task not found (404)
    - Max replay attempts exceeded (400)
    - Internal error during replay (500)
    
    **Important:** A task can be replayed maximum 3 times.
    Use discard for unrecoverable failures.
    """
    try:
        success = await DLQService.replay_task(db, task_id)
        
        if not success:
            # Fetch task to see why replay failed
            dlq_tasks, _ = await DLQService.get_dlq_tasks(db, limit=1)
            dlq_task = next((t for t in dlq_tasks if t.task_id == task_id), None)
            
            if not dlq_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"DLQ task {task_id} not found"
                )
            
            if dlq_task.replay_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task has exceeded max replay attempts ({dlq_task.replay_count}/3)"
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to replay task"
            )
        
        return {
            "success": True,
            "message": f"Task {task_id} has been requeued for processing",
            "task_id": task_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replay DLQ task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to replay task"
        )


@router.post("/tasks/{task_id}/discard", status_code=status.HTTP_200_OK)
async def discard_dlq_task(
    task_id: str,
    reason: str = Query(
        "Manual discard",
        description="Reason for discarding the task"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Discard (archive) a task from the DLQ.
    
    Use this for unrecoverable failures:
    - Business logic errors (invalid parameters)
    - User deleted or account closed
    - Task is deprecated or obsolete
    - Persistent recovery failures after retries
    
    **Requires:** Admin role
    
    Path Parameters:
    - task_id: Celery task ID to discard
    
    Query Parameters:
    - reason: Reason for discarding (for audit trail)
    
    Response:
    - success: Boolean indicating if discard succeeded
    - message: Status message
    
    Error Conditions:
    - Task not found (404)
    - Internal error (500)
    """
    try:
        success = await DLQService.discard_task(db, task_id, reason)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DLQ task {task_id} not found"
            )
        
        logger.info(f"Discarded DLQ task {task_id}: {reason}")
        
        return {
            "success": True,
            "message": f"Task {task_id} has been discarded",
            "task_id": task_id,
            "reason": reason,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discard DLQ task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discard task"
        )


@router.get("/task/{task_id}", status_code=status.HTTP_200_OK)
async def get_dlq_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get detailed information about a specific DLQ task.
    
    **Requires:** Admin role
    
    Path Parameters:
    - task_id: Celery task ID
    
    Response:
    - Full task record with parameters, error details, and history
    
    Error Conditions:
    - Task not found (404)
    """
    try:
        tasks, _ = await DLQService.get_dlq_tasks(db, limit=1, offset=0)
        dlq_task = next((t for t in tasks if t.task_id == task_id), None)
        
        if not dlq_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DLQ task {task_id} not found"
            )
        
        return dlq_task.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get DLQ task detail {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task details"
        )
