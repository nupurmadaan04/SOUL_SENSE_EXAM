from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from ..services.db_service import get_db
from ..services.audit_service import AuditService
from ..models import User
from ..routers.auth import get_current_user, require_admin
from ..schemas import AuditLogResponse, AuditLogListResponse, AuditExportResponse
from ..services.kafka_producer import get_kafka_producer
from ..models import AuditSnapshot
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    username: Optional[str] = Query(None, description="Filter by username"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve audit logs with filtering and pagination.

    This endpoint allows administrators to query the system's audit trail with various filters.

    Args:
        event_type (Optional[str]): Filter by the type of event (e.g., 'auth', 'data_access').
        username (Optional[str]): Filter by the username of the actor.
        resource_type (Optional[str]): Filter by the type of resource affected.
        action (Optional[str]): Filter by the action performed (e.g., 'login', 'delete').
        outcome (Optional[str]): Filter by the outcome of the event (success/failure).
        severity (Optional[str]): Filter by event severity (info, warning, error, critical).
        start_date (Optional[datetime]): Filter logs after this timestamp.
        end_date (Optional[datetime]): Filter logs before this timestamp.
        page (int): The page number for pagination (defaults to 1).
        per_page (int): The number of results per page (defaults to 50, max 100).
        current_user (User): The authenticated admin user.
        db (AsyncSession): Database session.

    Returns:
        AuditLogListResponse: A paginated list of audit logs and total count.

    Raises:
        HTTPException: 403 Forbidden if the user is not an administrator.
    """

    filters = {}
    if event_type:
        filters['event_type'] = event_type
    if username:
        filters['username'] = username
    if resource_type:
        filters['resource_type'] = resource_type
    if action:
        filters['action'] = action
    if outcome:
        filters['outcome'] = outcome
    if severity:
        filters['severity'] = severity
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    logs, total_count = await AuditService.query_logs(filters, page, per_page, db)

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total_count=total_count,
        page=page,
        per_page=per_page
    )

@router.get("/my-activity", response_model=AuditLogListResponse)
async def get_my_activity(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the current user's own audit activity logs.

    Allows users to see a history of their own actions within the system for security and transparency.

    Args:
        page (int): The page number for pagination (defaults to 1).
        per_page (int): The number of results per page (defaults to 20, max 50).
        current_user (User): The authenticated user.
        db (AsyncSession): Database session.

    Returns:
        AuditLogListResponse: A paginated list of the user's audit logs.
    """
    logs, total_count = await AuditService.get_user_activity(current_user.id, page, per_page, db)

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total_count=total_count,
        page=page,
        per_page=per_page
    )

@router.get("/export", response_model=AuditExportResponse)
async def export_audit_logs(
    format: str = Query("json", description="Export format"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    username: Optional[str] = Query(None, description="Filter by username"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Export audit logs in JSON or CSV format for external analysis or compliance.

    Args:
        format (str): The desired export format ('json' or 'csv'). Defaults to 'json'.
        event_type (Optional[str]): Filter by event type.
        username (Optional[str]): Filter by username.
        start_date (Optional[datetime]): Start of the date range to export.
        end_date (Optional[datetime]): End of the date range to export.
        current_user (User): The authenticated admin user.
        db (AsyncSession): Database session.

    Returns:
        AuditExportResponse: The exported log data with timestamp and format.

    Raises:
        HTTPException: 403 Forbidden if the user is not an administrator.
    """

    filters = {}
    if event_type:
        filters['event_type'] = event_type
    if username:
        filters['username'] = username
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    exported_data = await AuditService.export_logs(filters, format, db)

    return AuditExportResponse(
        data=exported_data,
        format=format,
        timestamp=datetime.now(UTC)
    )

@router.post("/archive")
async def archive_old_logs(
    retention_days: Optional[int] = Query(90, ge=1, description="Retention period in days"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Archive audit logs older than the specified retention period.

    Moves old logs to a secondary storage or marks them as archived to optimize active table performance.

    Args:
        retention_days (Optional[int]): Number of days to keep logs online. Defaults to 90.
        current_user (User): The authenticated admin user.
        db (AsyncSession): Database session.

    Returns:
        Dict[str, Any]: A message confirming the outcome and the count of archived logs.

    Raises:
        HTTPException: 403 Forbidden if the user is not an administrator.
    """

    archived_count = await AuditService.archive_old_logs(retention_days, db)

    return {
        "message": f"Archived {archived_count} audit logs",
        "archived_count": archived_count
    }

@router.post("/cleanup")
async def cleanup_expired_logs(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete expired audit logs from the system.

    This action is irrevokable and should be used to maintain database size and comply with data retention policies.

    Args:
        current_user (User): The authenticated admin user.
        db (AsyncSession): Database session.

    Returns:
        Dict[str, Any]: A message confirming the outcome and the count of deleted logs.

    Raises:
        HTTPException: 403 Forbidden if the user is not an administrator.
    """

    deleted_count = await AuditService.cleanup_expired_logs(db)

    return {
        "message": f"Cleaned up {deleted_count} expired audit logs",
        "deleted_count": deleted_count
    }

async def event_generator(request: Request):
    """Generator for live audit events using the internal Event Queue (#1085)."""
    producer = get_kafka_producer()
    while True:
        if await request.is_disconnected():
            break
        # Wait for a new event from the producer's live queue
        event_data = await producer.live_events.get()
        yield f"data: {json.dumps(event_data)}\n\n"

@router.get("/stream")
async def audit_stream(request: Request, current_user: User = Depends(require_admin)):
    """Admin-only SSE stream for live audit events."""
    return StreamingResponse(event_generator(request), media_type="text/event-stream")

@router.get("/snapshots", response_model=List[Dict[str, Any]])
async def get_audit_snapshots(
    entity: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Retrieve audit history from the compacted snapshot table."""
    from sqlalchemy import select
    query = select(AuditSnapshot).order_by(AuditSnapshot.timestamp.desc()).limit(100)
    if entity:
        query = query.filter(AuditSnapshot.entity == entity)
    
    result = await db.execute(query)
    snapshots = result.scalars().all()
    return [{
        "id": s.id,
        "type": s.event_type,
        "entity": s.entity,
        "entity_id": s.entity_id,
        "payload": s.payload,
        "timestamp": s.timestamp.isoformat() if s.timestamp else None
    } for s in snapshots]