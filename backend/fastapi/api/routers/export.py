"""
Enhanced Export Router with backward compatibility and new features.

This router maintains backward compatibility with v1 endpoints while adding
advanced export features from ExportServiceV2.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import os

from ..services.db_service import get_db
from ..services.export_service import ExportService as ExportServiceV1
from ..services.export_service_v2 import ExportServiceV2
from ..root_models import User, ExportRecord
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiting: {user_id: [timestamp, request_count]}
_export_rate_limits: Dict[int, List[datetime]] = {}
MAX_REQUESTS_PER_HOUR = 10


def _check_rate_limit(user_id: int) -> None:
    """
    Check if user has exceeded rate limit.
    Allows MAX_REQUESTS_PER_HOUR requests per hour.
    """
    now = datetime.now()

    # Clean old requests
    if user_id in _export_rate_limits:
        # Remove requests older than 1 hour
        _export_rate_limits[user_id] = [
            ts for ts in _export_rate_limits[user_id]
            if (now - ts).seconds < 3600
        ]

    # Check current count
    current_count = len(_export_rate_limits.get(user_id, []))
    if current_count >= MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_HOUR} exports per hour."
        )

    # Add current request
    if user_id not in _export_rate_limits:
        _export_rate_limits[user_id] = []
    _export_rate_limits[user_id].append(now)


# ============================================================================
# V1 ENDPOINTS (Backward Compatible)
# ============================================================================

@router.post("")
async def generate_export(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    V1 Endpoint: Generate an export of user data.

    Backward compatible endpoint that uses v1 service for json/csv formats.
    For enhanced features, use POST /api/v1/export/v2 endpoint.

    Payload: {"format": "json" | "csv"}
    """
    export_format = request.get("format", "json").lower()

    # Rate Limiting
    _check_rate_limit(current_user.id)

    try:
        # Generate Export using V1 service
        filepath, job_id = await ExportServiceV1.generate_export(db, current_user, export_format)

        filename = os.path.basename(filepath)

        return {
            "job_id": job_id,
            "status": "completed",
            "filename": filename,
            "download_url": f"/api/v1/export/{filename}/download"
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Export failed for {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate export.")


# ============================================================================
# V2 ENDPOINTS (Enhanced Features)
# ============================================================================

@router.post("/v2")
async def create_export_v2(
    format: str = Body(..., embed=True),
    options: Optional[Dict[str, Any]] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    V2 Endpoint: Create an export with advanced options.

    Request Body:
    {
        "format": "json" | "csv" | "xml" | "html" | "pdf",
        "options": {
            "date_range": {
                "start": "2023-01-01T00:00:00",
                "end": "2024-12-31T23:59:59"
            },
            "data_types": ["profile", "journal", "assessments"],
            "encrypt": false,
            "password": "optional_password_for_encryption"
        }
    }

    Supported formats:
    - json: Complete data with metadata (GDPR compliant)
    - csv: Tabular data in ZIP archive
    - xml: Structured XML with schema
    - html: Interactive, searchable HTML file
    - pdf: Professional document with charts

    Supported data_types:
    - profile, journal, assessments, scores, satisfaction,
    - settings, medical, strengths, emotional_patterns, responses
    """
    # Rate limiting
    _check_rate_limit(current_user.id)

    # Validate format
    format_lower = format.lower()
    if format_lower not in ExportServiceV2.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported: {', '.join(ExportServiceV2.SUPPORTED_FORMATS)}"
        )

    # Prepare options with defaults
    export_options = options or {}
    if 'data_types' not in export_options:
        export_options['data_types'] = list(ExportServiceV2.DATA_TYPES)

    # Validate data types
    invalid_types = set(export_options['data_types']) - ExportServiceV2.DATA_TYPES
    if invalid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data types: {', '.join(invalid_types)}. Valid types: {', '.join(ExportServiceV2.DATA_TYPES)}"
        )

    # Validate encryption options
    if export_options.get('encrypt', False) and not export_options.get('password'):
        raise HTTPException(
            status_code=400,
            detail="Password is required when encryption is enabled."
        )

    try:
        filepath, export_id = await ExportServiceV2.generate_export(
            db, current_user, format_lower, export_options
        )

        filename = filepath.split('/')[-1]

        return {
            "export_id": export_id,
            "status": "completed",
            "format": format_lower,
            "filename": filename,
            "download_url": f"/api/v1/export/{export_id}/download",
            "expires_at": (datetime.now() + __import__('datetime').timedelta(hours=48)).isoformat(),
            "is_encrypted": export_options.get('encrypt', False),
            "data_types": export_options.get('data_types', []),
            "message": "Export completed successfully"
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Export failed for {current_user.username}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate export. Please try again or contact support."
        )


@router.get("/v2")
async def list_exports_v2(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all exports for the current user.
    """
    try:
        history = await ExportServiceV2.get_export_history(db, current_user, limit)

        return {
            "total": len(history),
            "exports": history
        }

    except Exception as e:
        logger.error(f"Failed to list exports for {current_user.username}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve export history."
        )


@router.get("/v2/{export_id}")
async def get_export_status_v2(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status and details of an export job (V2).
    """
    from sqlalchemy import select
    result = await db.execute(
        select(ExportRecord).filter(
            ExportRecord.export_id == export_id,
            ExportRecord.user_id == current_user.id
        )
    )
    export = result.scalar_one_or_none()

    if not export:
        raise HTTPException(
            status_code=404,
            detail="Export not found or you don't have access to it."
        )

    # Check if expired
    if export.expires_at and export.expires_at < datetime.now():
        return {
            "export_id": export_id,
            "status": "expired",
            "message": "Export has expired. Please create a new export."
        }

    # Check if file still exists
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
    """
    Delete an export file and its record (V2).
    """
    try:
        success = await ExportServiceV2.delete_export(db, current_user, export_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Export not found or you don't have access to it."
            )

        return {
            "message": "Export deleted successfully",
            "export_id": export_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete export {export_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete export. Please try again."
        )


@router.get("/formats")
async def list_supported_formats():
    """
    List all supported export formats and their capabilities.
    """
    return {
        "formats": {
            "json": {
                "description": "Complete data export with GDPR metadata",
                "features": ["Structured data", "Full metadata", "Machine-readable", "Easy to parse"],
                "use_cases": ["Data portability", "Backup", "API integration"]
            },
            "csv": {
                "description": "Tabular data in ZIP archive",
                "features": ["Spreadsheet compatible", "Multiple files", "Easy analysis"],
                "use_cases": ["Excel/Google Sheets", "Data analysis", "Statistical tools"]
            },
            "xml": {
                "description": "Structured XML with schema validation",
                "features": ["Schema validation", "Hierarchical", "Standards compliant"],
                "use_cases": ["Enterprise integration", "System migration"]
            },
            "html": {
                "description": "Interactive, self-contained HTML file",
                "features": ["Searchable", "Interactive", "Printable", "No software needed"],
                "use_cases": ["Viewing in browser", "Printing", "Sharing"]
            },
            "pdf": {
                "description": "Professional document with charts",
                "features": ["Visualizations", "Trend charts", "Professional format"],
                "use_cases": ["Reports", "Archives", "Printing"]
            }
        },
        "data_types": list(ExportServiceV2.DATA_TYPES),
        "encryption": "Supported (requires password)",
        "retention": "48 hours"
    }


# ============================================================================
# SHARED ENDPOINTS
# ============================================================================

@router.get("/{job_id}/status")
async def get_export_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    V1 Endpoint: Get the status of an export job.
    """
    # Check if it's a V2 export (with database record)
    from ..services.db_service import AsyncSessionLocal
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExportRecord).filter(
                ExportRecord.export_id == job_id
            )
        )
        export = result.scalar_one_or_none()

        if export:
            if export.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied.")

            return {
                "job_id": job_id,
                "status": export.status,
                "filename": os.path.basename(export.file_path),
                "download_url": f"/api/v1/export/{job_id}/download"
            }

    # Fallback for V1 exports (no database record)
    raise HTTPException(status_code=404, detail="Job not found.")


@router.get("/{identifier}/download")
async def download_export(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download an export file.
    Supports both V1 (filename) and V2 (export_id) identifiers.
    """
    # First, check if it's a V2 export (by export_id)
    from sqlalchemy import select
    result = await db.execute(
        select(ExportRecord).filter(
            ExportRecord.export_id == identifier
        )
    )
    export = result.scalar_one_or_none()

    filepath = None
    filename = None

    if export:
        # V2 export
        if export.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied.")

        if export.expires_at and export.expires_at < datetime.now():
            raise HTTPException(
                status_code=410,
                detail="Export has expired. Please create a new export."
            )

        filepath = export.file_path
        filename = os.path.basename(filepath)
    else:
        # V1 export - check if it's a valid filename
        if not ExportServiceV1.validate_export_access(current_user, identifier):
            raise HTTPException(status_code=403, detail="Access denied to this export file.")

        filepath = str(ExportServiceV1.EXPORT_DIR / identifier)
        filename = identifier

    # Check if file exists
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail="Export file not found or expired."
        )

    # Determine media type
    if filename.endswith('.json'):
        media_type = 'application/json'
    elif filename.endswith('.csv') or filename.endswith('.zip'):
        media_type = 'application/zip'
    elif filename.endswith('.xml'):
        media_type = 'application/xml'
    elif filename.endswith('.html'):
        media_type = 'text/html'
    elif filename.endswith('.pdf'):
        media_type = 'application/pdf'
    else:
        media_type = 'application/octet-stream'

    # Serve file
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type
    )
