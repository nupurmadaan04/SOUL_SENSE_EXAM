"""
Export Router for user data reports (JSON, CSV, PDF).
Migrated to Async SQLAlchemy 2.0.
"""

from fastapi import APIRouter, Depends, Query, Body, BackgroundTasks, status, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import logging
import os
from pathlib import Path

from ..services.storage_service import StorageService
from ..services.export_service import ExportService, ExportServiceV1
from ..services.db_router import get_db
from ..config import get_settings_instance
from ..models import User, ExportRecord, BackgroundJob
from .auth import get_current_user
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    format: str = Field("json", description="Export format: json, csv, pdf")

class ExportResponse(BaseModel):
    job_id: str
    status: str
    format: str
    filename: str
    download_url: str

class SupportedFormatsResponse(BaseModel):
    formats: List[str]
    default: str

class AsyncExportRequest(BaseModel):
    format: str = "json"

class AsyncPDFExportRequest(BaseModel):
    include_charts: bool = True

class AsyncExportResponse(BaseModel):
    job_id: str
    status: str
    message: str

router = APIRouter()
logger = logging.getLogger("api.export")

# Rate limiting: {user_id: [timestamp]}
_export_rate_limits: Dict[int, List[datetime]] = {}
MAX_REQUESTS_PER_HOUR = 30


def _check_rate_limit(user_id: int) -> None:
    """Check if user has exceeded rate limit."""
    now = datetime.now(timezone.utc)
    if user_id in _export_rate_limits:
        _export_rate_limits[user_id] = [
            ts for ts in _export_rate_limits[user_id]
            if (now - ts).total_seconds() < 3600
        ]
    current_count = len(_export_rate_limits.get(user_id, []))
    if current_count >= MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_HOUR} exports per hour."
        )
    if user_id not in _export_rate_limits:
        _export_rate_limits[user_id] = []
    _export_rate_limits[user_id].append(now)


@router.post("", response_model=ExportResponse)
async def generate_export(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate an export of user assessment data."""
    _check_rate_limit(current_user.id)

    try:
        filepath, job_id = await ExportService.generate_export(db, current_user, request.format)
        filename = os.path.basename(filepath)

        return ExportResponse(
            job_id=job_id,
            status="completed",
            format=request.format,
            filename=filename,
            download_url=f"/api/v1/export/{filename}/download"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Export generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate export")


@router.get("/pdf")
async def export_pdf_direct(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Directly generate and return user assessment report PDF."""
    _check_rate_limit(current_user.id)
    try:
        filepath, _ = await ExportService.generate_export(db, current_user, "pdf")
        filename = os.path.basename(filepath)
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"Direct PDF export failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to export PDF report")


@router.get("/formats", response_model=SupportedFormatsResponse)
@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """Get list of supported export formats."""
    return SupportedFormatsResponse(
        formats=["json", "csv", "pdf"],
        default="json"
    )


@router.get("/{identifier}/download")
async def download_export(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download an export file."""
    # Check if identifier is filename in exports dir
    if not ExportService.validate_export_access(current_user, identifier):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    filepath = str(ExportService.EXPORT_DIR / identifier)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")

    media_type = 'application/octet-stream'
    if identifier.endswith('.json'):
        media_type = 'application/json'
    elif identifier.endswith('.csv'):
        media_type = 'text/csv'
    elif identifier.endswith('.pdf'):
        media_type = 'application/pdf'

    return FileResponse(path=filepath, filename=identifier, media_type=media_type)
