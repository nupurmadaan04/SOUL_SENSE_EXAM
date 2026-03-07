"""
API Deprecation API Routes

Provides REST API endpoints for managing API deprecation notices,
version lifecycle, and deprecation header configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.api_deprecation import (
    DeprecationStatus, DeprecationSeverity, ApiVersionStatus,
    ApiVersion, DeprecationNotice, DeprecatedField,
    DeprecationHeaders, ApiDeprecationManager, get_deprecation_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api-deprecation", tags=["api-deprecation"])


# Pydantic Models

class ApiVersionCreateRequest(BaseModel):
    """Request to create API version."""
    version: str
    base_path: str
    status: ApiVersionStatus
    released_at: Optional[datetime] = None
    documentation_url: str = ""


class ApiVersionResponse(BaseModel):
    """Response model for API version."""
    version: str
    base_path: str
    status: ApiVersionStatus
    released_at: datetime
    deprecated_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None
    documentation_url: str
    request_count: int
    unique_client_count: int


class DeprecationNoticeCreateRequest(BaseModel):
    """Request to create deprecation notice."""
    notice_id: str
    endpoint_path: str
    http_method: str
    status: DeprecationStatus
    severity: DeprecationSeverity
    deprecated_since: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    alternative_endpoint: str = ""
    alternative_version: str = ""
    migration_guide_url: str = ""
    notice_message: str = ""
    breaking_changes: List[str] = Field(default_factory=list)


class DeprecationNoticeResponse(BaseModel):
    """Response model for deprecation notice."""
    notice_id: str
    endpoint_path: str
    http_method: str
    status: DeprecationStatus
    severity: DeprecationSeverity
    deprecated_since: datetime
    sunset_date: Optional[datetime] = None
    removal_date: Optional[datetime] = None
    alternative_endpoint: str
    alternative_version: str
    migration_guide_url: str
    notice_message: str
    breaking_changes: List[str]
    affected_client_count: int
    notification_sent: bool


class DeprecatedFieldRequest(BaseModel):
    """Request to register deprecated field."""
    endpoint_path: str
    field_name: str
    field_location: str
    deprecated_since: datetime
    removal_version: str = ""
    replacement_field: str = ""


class DeprecatedFieldResponse(BaseModel):
    """Response model for deprecated field."""
    field_name: str
    field_location: str
    deprecated_since: datetime
    removal_version: str
    replacement_field: str


class DeprecationHeadersResponse(BaseModel):
    """Response model for deprecation headers."""
    headers: Dict[str, str]
    endpoint_path: str
    http_method: str


class ClientNotificationRequest(BaseModel):
    """Request to notify client."""
    client_id: str
    notice_id: str


class ClientAcknowledgementRequest(BaseModel):
    """Request to acknowledge deprecation."""
    client_id: str
    notice_id: str


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    api_versions: Dict[str, Any]
    deprecation_notices: Dict[str, Any]
    affected_clients: int
    notification_coverage: float


# Helper Functions

def _version_to_response(version: ApiVersion) -> ApiVersionResponse:
    """Convert ApiVersion to response model."""
    return ApiVersionResponse(
        version=version.version,
        base_path=version.base_path,
        status=version.status,
        released_at=version.released_at,
        deprecated_at=version.deprecated_at,
        sunset_at=version.sunset_at,
        documentation_url=version.documentation_url,
        request_count=version.request_count,
        unique_client_count=len(version.unique_clients)
    )


def _notice_to_response(notice: DeprecationNotice) -> DeprecationNoticeResponse:
    """Convert DeprecationNotice to response model."""
    return DeprecationNoticeResponse(
        notice_id=notice.notice_id,
        endpoint_path=notice.endpoint_path,
        http_method=notice.http_method,
        status=notice.status,
        severity=notice.severity,
        deprecated_since=notice.deprecated_since,
        sunset_date=notice.sunset_date,
        removal_date=notice.removal_date,
        alternative_endpoint=notice.alternative_endpoint,
        alternative_version=notice.alternative_version,
        migration_guide_url=notice.migration_guide_url,
        notice_message=notice.notice_message,
        breaking_changes=notice.breaking_changes,
        affected_client_count=len(notice.affected_clients),
        notification_sent=notice.notification_sent
    )


# API Routes

@router.post("/versions", response_model=ApiVersionResponse, status_code=status.HTTP_201_CREATED)
async def register_api_version(
    request: ApiVersionCreateRequest,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(require_admin)
):
    """
    Register a new API version.
    
    Requires admin privileges.
    """
    version = await manager.register_api_version(
        version=request.version,
        base_path=request.base_path,
        status=request.status,
        released_at=request.released_at,
        documentation_url=request.documentation_url
    )
    
    return _version_to_response(version)


@router.get("/versions", response_model=List[ApiVersionResponse])
async def list_api_versions(
    status: Optional[ApiVersionStatus] = None,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """List API versions."""
    versions = await manager.list_api_versions(status=status)
    return [_version_to_response(v) for v in versions]


@router.get("/versions/{version}", response_model=ApiVersionResponse)
async def get_api_version(
    version: str,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Get API version by version string."""
    api_version = await manager.get_api_version(version)
    
    if not api_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API version {version} not found"
        )
    
    return _version_to_response(api_version)


@router.post("/versions/{version}/deprecate", response_model=ApiVersionResponse)
async def deprecate_version(
    version: str,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(require_admin)
):
    """
    Mark an API version as deprecated.
    
    Requires admin privileges.
    """
    deprecated = await manager.deprecate_version(version)
    
    if not deprecated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API version {version} not found"
        )
    
    return _version_to_response(deprecated)


@router.post("/notices", response_model=DeprecationNoticeResponse, status_code=status.HTTP_201_CREATED)
async def create_deprecation_notice(
    request: DeprecationNoticeCreateRequest,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a deprecation notice for an endpoint.
    
    Requires admin privileges.
    """
    notice = await manager.create_deprecation_notice(
        notice_id=request.notice_id,
        endpoint_path=request.endpoint_path,
        http_method=request.http_method,
        status=request.status,
        severity=request.severity,
        deprecated_since=request.deprecated_since,
        sunset_date=request.sunset_date,
        alternative_endpoint=request.alternative_endpoint,
        alternative_version=request.alternative_version,
        migration_guide_url=request.migration_guide_url,
        notice_message=request.notice_message,
        breaking_changes=request.breaking_changes
    )
    
    return _notice_to_response(notice)


@router.get("/notices", response_model=List[DeprecationNoticeResponse])
async def list_deprecation_notices(
    status: Optional[DeprecationStatus] = None,
    severity: Optional[DeprecationSeverity] = None,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """List deprecation notices."""
    notices = await manager.list_deprecation_notices(
        status=status,
        severity=severity
    )
    return [_notice_to_response(n) for n in notices]


@router.get("/notices/{notice_id}", response_model=DeprecationNoticeResponse)
async def get_deprecation_notice(
    notice_id: str,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Get deprecation notice by ID."""
    notice = await manager.get_deprecation_notice(notice_id)
    
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deprecation notice {notice_id} not found"
        )
    
    return _notice_to_response(notice)


@router.get("/headers", response_model=DeprecationHeadersResponse)
async def get_deprecation_headers(
    endpoint_path: str,
    http_method: str = "GET",
    client_id: Optional[str] = None,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Get RFC-compliant deprecation headers for an endpoint."""
    headers = await manager.get_deprecation_headers(
        endpoint_path=endpoint_path,
        http_method=http_method,
        client_id=client_id
    )
    
    return DeprecationHeadersResponse(
        headers=headers,
        endpoint_path=endpoint_path,
        http_method=http_method
    )


@router.post("/fields", response_model=DeprecatedFieldResponse, status_code=status.HTTP_201_CREATED)
async def register_deprecated_field(
    request: DeprecatedFieldRequest,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(require_admin)
):
    """
    Register a deprecated field for an endpoint.
    
    Requires admin privileges.
    """
    field = await manager.register_deprecated_field(
        endpoint_path=request.endpoint_path,
        field_name=request.field_name,
        field_location=request.field_location,
        deprecated_since=request.deprecated_since,
        removal_version=request.removal_version,
        replacement_field=request.replacement_field
    )
    
    return DeprecatedFieldResponse(
        field_name=field.field_name,
        field_location=field.field_location,
        deprecated_since=field.deprecated_since,
        removal_version=field.removal_version,
        replacement_field=field.replacement_field
    )


@router.get("/fields/{endpoint_path:path}", response_model=List[DeprecatedFieldResponse])
async def get_deprecated_fields(
    endpoint_path: str,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Get deprecated fields for an endpoint."""
    fields = await manager.get_deprecated_fields(endpoint_path)
    
    return [
        DeprecatedFieldResponse(
            field_name=f.field_name,
            field_location=f.field_location,
            deprecated_since=f.deprecated_since,
            removal_version=f.removal_version,
            replacement_field=f.replacement_field
        ) for f in fields
    ]


@router.post("/notifications", status_code=status.HTTP_201_CREATED)
async def notify_client(
    request: ClientNotificationRequest,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(require_admin)
):
    """
    Record that a client has been notified of deprecation.
    
    Requires admin privileges.
    """
    client_notice = await manager.notify_client(
        client_id=request.client_id,
        notice_id=request.notice_id
    )
    
    if not client_notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client or notice not found"
        )
    
    return {
        "client_id": request.client_id,
        "notice_id": request.notice_id,
        "sent_at": client_notice.sent_at.isoformat(),
        "message": "Notification recorded successfully"
    }


@router.post("/acknowledgements", status_code=status.HTTP_200_OK)
async def acknowledge_notice(
    request: ClientAcknowledgementRequest,
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Mark a deprecation notice as acknowledged by a client."""
    result = await manager.acknowledge_notice(
        client_id=request.client_id,
        notice_id=request.notice_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client notice not found"
        )
    
    return {
        "client_id": request.client_id,
        "notice_id": request.notice_id,
        "acknowledged": True,
        "acknowledged_at": datetime.utcnow().isoformat()
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: ApiDeprecationManager = Depends(get_deprecation_manager),
    user: Dict = Depends(get_current_user)
):
    """Get API deprecation statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        api_versions=stats["api_versions"],
        deprecation_notices=stats["deprecation_notices"],
        affected_clients=stats["affected_clients"],
        notification_coverage=stats["notification_coverage"]
    )


@router.get("/health")
async def health_check(
    manager: ApiDeprecationManager = Depends(get_deprecation_manager)
):
    """Health check endpoint for API deprecation service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "api_versions": len(manager.api_versions),
        "deprecation_notices": len(manager.deprecation_notices),
        "deprecated_fields": sum(len(f) for f in manager.deprecated_fields.values())
    }
