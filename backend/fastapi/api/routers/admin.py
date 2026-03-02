from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..services.db_service import get_db
from ..services.outbox_relay_service import OutboxRelayService
from ..models import User
from .auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/outbox/stats", response_model=Dict[str, int])
async def get_outbox_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Requirement ISSUE-1146: Get health statistics for the Transactional Outbox.
    Returns counts of events by status (pending, processed, failed).
    """
    stats = await OutboxRelayService.get_outbox_stats(db)
    return stats

@router.post("/outbox/retry-failed", response_model=Dict[str, Any])
async def retry_failed_outbox_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Requirement ISSUE-1146: Manually retry all failed (dead-lettered) outbox events.
    Resets status to 'pending' and retry_count to 0.
    """
    count = await OutboxRelayService.retry_all_failed_events(db)
    return {
        "message": f"Successfully reset {count} failed events to pending status.",
        "reset_count": count
    }

@router.get("/health", response_model=Dict[str, Any])
async def admin_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """General admin-only health check that includes system internals."""
    outbox_stats = await OutboxRelayService.get_outbox_stats(db)
    total_purgatory = outbox_stats.get("pending", 0) + outbox_stats.get("failed", 0)
    
    status = "healthy"
    if total_purgatory > 10000:
        status = "degraded (outbox_purgatory)"
    
    return {
        "status": status,
        "outbox": outbox_stats,
        "is_admin": True
    }
