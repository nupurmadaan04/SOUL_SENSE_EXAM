"""
Enhanced Export Router with backward compatibility and new features.
Migrated to Async SQLAlchemy 2.0.
"""

from fastapi import APIRouter, Depends, Query, Body, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional
import logging
import os

from ..services.db_service import get_db, AsyncSessionLocal
from ..services.export_service import ExportService as ExportServiceV1
from ..services.export_service_v2 import ExportServiceV2
from ..services.background_task_service import BackgroundTaskService, TaskStatus, TaskType
from ..models import User, ExportRecord, BackgroundJob
from .auth import get_current_user
from app.core import (
    NotFoundError,
    ValidationError,
    AuthorizationError,
    InternalServerError,
    RateLimitError
)
from api.celery_tasks import execute_async_export_task

router = APIRouter()
logger = logging.getLogger("api.export")

# Import schemas for validation
from ..schemas import (
    ExportRequest,
    ExportV2Request,
    ExportResponse,
    SupportedFormatsResponse,
    AsyncExportRequest,
    AsyncPDFExportRequest,
    AsyncExportResponse
)

# Rate limiting: {user_id: [timestamp, request_count]}
_export_rate_limits: Dict[int, List[datetime]] = {}
MAX_REQUESTS_PER_HOUR = 10


def _check_rate_limit(user_id: int) -> None:
    """Check if user has exceeded rate limit."""
    now = datetime.now(UTC)

    if user_id in _export_rate_limits:
        _export_rate_limits[user_id] = [
            ts for ts in _export_rate_limits[user_id]
            if (now - ts).total_seconds() < 3600
        ]

    current_count = len(_export_rate_limits.get(user_id, []))
    if current_count >= MAX_REQUESTS_PER_HOUR:
        raise RateLimitError(
            message=f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_HOUR} exports per hour.",
            wait_seconds=3600
        )

    if user_id not in _export_rate_limits:
        _export_rate_limits[user_id] = []
    _export_rate_limits[user_id].append(now)


# ============================================================================
# V1 ENDPOINTS (Backward Compatible)
# ============================================================================

@router.post("", response_model=ExportResponse)
async def generate_export(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """V1 Endpoint: Generate an export of user data."""
    _check_rate_limit(current_user.id)

    try:
        filepath, job_id = await ExportServiceV1.generate_export(db, current_user, request.format)
        filename = os.path.basename(filepath)

        return ExportResponse(
            job_id=job_id,
            status="completed",
            format=request.format,
            filename=filename,
            download_url=f"/api/v1/export/{filename}/download"
        )

    except ValueError as ve:
        raise ValidationError(message=str(ve))
    except Exception as e:
        logger.error(f"Export failed for {current_user.username}: {e}")
        raise InternalServerError(message="Failed to generate export")


# ============================================================================
# V2 ENDPOINTS (Enhanced Features)
# ============================================================================

@router.get("/pdf")
async def export_pdf_direct(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate and return a comprehensive PDF report immediately."""
    _check_rate_limit(current_user.id)
    
    try:
        options = {
            "data_types": list(ExportServiceV2.DATA_TYPES),
            "include_metadata": True
        }
        
        filepath, export_id = await ExportServiceV2.generate_export(
            db, current_user, "pdf", options
        )
        
        filename = f"SoulSense_Report_{datetime.now(UTC).strftime('%Y-%m-%d')}.pdf"
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/pdf"
        )
        
    except Exception as e:
        logger.error(f"Instant PDF export failed for {current_user.username}: {e}")
        raise InternalServerError(
            message="Failed to generate your PDF report. Please try again."
        )


# ============================================================================
# ASYNC EXPORT ENDPOINTS (Background Task Queue)
# ============================================================================

async def _execute_async_export(
    user_id: int,
    username: str,
    format: str,
    options: Dict[str, Any]
) -> Dict[str, Any]:
    """Background task function for generating exports asynchronously."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(User).filter(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        filepath, export_id = await ExportServiceV2.generate_export(
            db, user, format, options
        )
        
        return {
            "filepath": filepath,
            "export_id": export_id,
            "format": format,
            "filename": os.path.basename(filepath),
            "download_url": f"/api/v1/reports/export/{export_id}/download"
        }


@router.post("/async", status_code=status.HTTP_202_ACCEPTED, response_model=AsyncExportResponse)
async def create_async_export(
    request: AsyncExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an export asynchronously."""
    _check_rate_limit(current_user.id)
    
    pending_count = await BackgroundTaskService.get_pending_tasks_count(db, current_user.id)
    if pending_count >= 5:
        raise RateLimitError(
            message="Too many pending exports. Please wait for existing exports to complete.",
            wait_seconds=60
        )
    
    task_type_map = {
        "pdf": TaskType.EXPORT_PDF,
        "csv": TaskType.EXPORT_CSV,
        "json": TaskType.EXPORT_JSON,
        "xml": TaskType.EXPORT_XML,
        "html": TaskType.EXPORT_HTML,
    }
    task_type = task_type_map.get(request.format, TaskType.EXPORT_JSON)
    
    export_options = request.options.model_dump() if request.options else {}
    if 'data_types' not in export_options:
        export_options['data_types'] = list(ExportServiceV2.DATA_TYPES)
    
    task = await BackgroundTaskService.create_task(
        db=db,
        user_id=current_user.id,
        task_type=task_type,
        params={"format": request.format, "options": export_options}
    )
    
    # Enqueue task to Celery
    execute_async_export_task.delay(
        task.job_id,
        current_user.id,
        current_user.username,
        request.format,
        export_options
    )
    
    return AsyncExportResponse(
        job_id=task.job_id,
        status="processing",
        poll_url=f"/api/v1/tasks/{task.job_id}",
        format=request.format
    )


@router.post("/async/pdf", status_code=status.HTTP_202_ACCEPTED, response_model=AsyncExportResponse)
async def create_async_pdf_export(
    request: AsyncPDFExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a PDF report asynchronously."""
    options = {
        "data_types": request.data_types or list(ExportServiceV2.DATA_TYPES),
        "include_metadata": True,
        "include_charts": request.include_charts
    }
    
    # Create a temporary AsyncExportRequest for the helper function
    export_request = AsyncExportRequest(format="pdf", options=ExportOptions(**options))
    
    return await create_async_export(
        request=export_request,
        current_user=current_user,
        db=db
    )


@router.post("/v2", response_model=ExportResponse)
async def create_export_v2(
    request: ExportV2Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """V2 Endpoint: Create an export with advanced options."""
    _check_rate_limit(current_user.id)

    export_options = request.options.model_dump() if request.options else {}
    if 'data_types' not in export_options:
        export_options['data_types'] = list(ExportServiceV2.DATA_TYPES)

    try:
        filepath, export_id = await ExportServiceV2.generate_export(
            db, current_user, request.format, export_options
        )

        filename = os.path.basename(filepath)

        return ExportResponse(
            export_id=export_id,
            status="completed",
            format=request.format,
            filename=filename,
            download_url=f"/api/v1/export/{export_id}/download",
            expires_at=(datetime.now(UTC) + timedelta(hours=48)).isoformat(),
            message="Export completed successfully"
        )

    except ValueError as ve:
        raise ValidationError(message=str(ve))
    except Exception as e:
        logger.error(f"Export failed for {current_user.username}: {e}")
        raise InternalServerError(message="Failed to generate export")


@router.get("/v2")
async def list_exports_v2(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all exports for the current user."""
    try:
        history = await ExportServiceV2.get_export_history(db, current_user, limit)
        return {
            "total": len(history),
            "exports": history
        }
    except Exception as e:
        logger.error(f"Failed to list exports for {current_user.username}: {e}")
        raise InternalServerError(message="Failed to retrieve export history")


@router.get("/v2/{export_id}")
async def get_export_status_v2(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status and details of an export job."""
    from sqlalchemy import select
    stmt = select(ExportRecord).filter(
        ExportRecord.export_id == export_id,
        ExportRecord.user_id == current_user.id
    )
    res = await db.execute(stmt)
    export = res.scalar_one_or_none()

    if not export:
        raise NotFoundError(resource="Export", resource_id=export_id)

    if export.expires_at and export.expires_at < datetime.now(UTC):
        return {
            "export_id": export_id,
            "status": "expired",
            "message": "Export has expired."
        }

    file_exists = os.path.exists(export.file_path)

    return {
        "export_id": export_id,
        "status": export.status if file_exists else "deleted",
        "format": export.format,
        "created_at": export.created_at.isoformat() if export.created_at else None,
        "expires_at": export.expires_at.isoformat() if export.expires_at else None,
        "is_encrypted": export.is_encrypted,
        "file_exists": file_exists,
        "download_url": f"/api/v1/export/{export_id}/download" if file_exists else None
    }


@router.delete("/v2/{export_id}")
async def delete_export_v2(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an export file and its record."""
    try:
        success = await ExportServiceV2.delete_export(db, current_user, export_id)

        if not success:
            raise NotFoundError(resource="Export", resource_id=export_id)

        return {
            "message": "Export deleted successfully",
            "export_id": export_id
        }
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete export {export_id}: {e}")
        raise InternalServerError(message="Failed to delete export")


@router.get("/formats", response_model=SupportedFormatsResponse)
async def list_supported_formats():
    """List all supported export formats."""
    return SupportedFormatsResponse(
        formats={
            "json": {"description": "Complete data export"},
            "csv": {"description": "Tabular data in ZIP archive"},
            "xml": {"description": "Structured XML"},
            "html": {"description": "Interactive HTML"},
            "pdf": {"description": "Professional document"}
        },
        data_types=list(ExportServiceV2.DATA_TYPES),
        retention="48 hours"
    )


@router.get("/{job_id}/status")
async def get_export_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """V1 Endpoint: Get the status of an export job."""
    from sqlalchemy import select
    stmt = select(ExportRecord).filter(ExportRecord.export_id == job_id)
    res = await db.execute(stmt)
    export = res.scalar_one_or_none()

    if export:
        if export.user_id != current_user.id:
            raise AuthorizationError(message="Access denied")

        return {
            "job_id": job_id,
            "status": export.status,
            "filename": os.path.basename(export.file_path),
            "download_url": f"/api/v1/export/{job_id}/download"
        }

    raise NotFoundError(resource="Export job", resource_id=job_id)


@router.get("/{identifier}/download")
async def download_export(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download an export file."""
    from sqlalchemy import select
    stmt = select(ExportRecord).filter(ExportRecord.export_id == identifier)
    res = await db.execute(stmt)
    export = res.scalar_one_or_none()

    filepath = None
    filename = None

    if export:
        if export.user_id != current_user.id:
            raise AuthorizationError(message="Access denied")

        if export.expires_at and export.expires_at < datetime.now(UTC):
            raise ValidationError(message="Export has expired.")

        filepath = export.file_path
        filename = os.path.basename(filepath)
    else:
        if not ExportServiceV1.validate_export_access(current_user, identifier):
            raise AuthorizationError(message="Access denied")

        filepath = str(ExportServiceV1.EXPORT_DIR / identifier)
        filename = identifier

    if not os.path.exists(filepath):
        raise NotFoundError(resource="Export file")

    media_type = 'application/octet-stream'
    if filename.endswith('.json'): media_type = 'application/json'
    elif filename.endswith('.csv') or filename.endswith('.zip'): media_type = 'application/zip'
    elif filename.endswith('.xml'): media_type = 'application/xml'
    elif filename.endswith('.html'): media_type = 'text/html'
    elif filename.endswith('.pdf'): media_type = 'application/pdf'

    return FileResponse(path=filepath, filename=filename, media_type=media_type)
