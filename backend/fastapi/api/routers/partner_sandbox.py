"""
Partner API Sandbox Router (#1443)

REST API endpoints for partner sandbox environment management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.partner_sandbox import (
    get_sandbox_manager,
    PartnerSandboxManager,
    SandboxConfig,
    SandboxScenario,
    SandboxStatus,
    SandboxEnvironment,
)
from .auth import require_admin, get_current_user


router = APIRouter(tags=["Partner Sandbox"], prefix="/partner-sandbox")


# --- Pydantic Schemas ---

class SandboxConfigRequest(BaseModel):
    """Schema for sandbox configuration."""
    latency_ms: int = Field(default=100, ge=0, le=10000)
    scenario: SandboxScenario = Field(default=SandboxScenario.SUCCESS)
    quota_daily: int = Field(default=1000, ge=1, le=100000)
    quota_hourly: int = Field(default=100, ge=1, le=10000)
    webhook_url: Optional[str] = Field(None)
    allowed_endpoints: List[str] = Field(default=["*"])
    blocked_endpoints: List[str] = Field(default_factory=list)
    enable_logging: bool = Field(default=True)
    log_retention_days: int = Field(default=30, ge=1, le=365)


class SandboxCreateRequest(BaseModel):
    """Schema for creating a sandbox."""
    partner_id: str = Field(..., description="Partner identifier")
    name: str = Field(..., description="Sandbox name")
    description: Optional[str] = Field(None)
    config: Optional[SandboxConfigRequest] = Field(None)
    expires_days: Optional[int] = Field(default=30, ge=1, le=365)


class SandboxResponse(BaseModel):
    """Schema for sandbox response."""
    sandbox_id: str
    partner_id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    status: str
    created_at: str
    expires_at: Optional[str]


class ApiKeyCreateRequest(BaseModel):
    """Schema for creating an API key."""
    expires_days: Optional[int] = Field(default=90, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """Schema for API key response (includes secret once)."""
    key_id: str
    key_secret: str  # Only shown once
    partner_id: str
    sandbox_id: str
    created_at: str
    expires_at: Optional[str]


class ApiKeyInfoResponse(BaseModel):
    """Schema for API key info (no secret)."""
    key_id: str
    partner_id: str
    sandbox_id: str
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int
    is_revoked: bool


class SandboxSimulateRequest(BaseModel):
    """Schema for simulating a request."""
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    path: str = Field(..., description="API path")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    body: Optional[str] = Field(None)


class SandboxSimulateResponse(BaseModel):
    """Schema for simulation response."""
    status: int
    body: Dict[str, Any]
    headers: Dict[str, str]
    latency_ms: float
    scenario: str
    sandbox_id: str


class SandboxUsageStatsResponse(BaseModel):
    """Schema for usage stats."""
    sandbox_id: str
    total_requests: int
    requests_today: int
    requests_this_hour: int
    average_latency_ms: float
    success_rate: float
    quota_remaining_daily: int
    quota_remaining_hourly: int
    last_request_at: Optional[str]


class RequestLogResponse(BaseModel):
    """Schema for request log entry."""
    log_id: str
    timestamp: str
    method: str
    path: str
    response_status: int
    latency_ms: float
    scenario: str


class WebhookEventRequest(BaseModel):
    """Schema for creating a webhook event."""
    event_type: str = Field(..., description="Event type")
    payload: Dict[str, Any] = Field(default_factory=dict)


class WebhookEventResponse(BaseModel):
    """Schema for webhook event response."""
    event_id: str
    event_type: str
    delivery_status: str
    created_at: str


class SandboxStatisticsResponse(BaseModel):
    """Schema for global statistics."""
    total_sandboxes: int
    active_sandboxes: int
    total_requests: int
    active_api_keys: int
    webhooks_24h: int
    timestamp: str


# --- API Endpoints ---

@router.post(
    "/sandboxes",
    response_model=SandboxResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create sandbox environment",
    description="Creates a new sandbox environment for partner testing."
)
async def create_sandbox(
    request: SandboxCreateRequest,
    current_user: Any = Depends(require_admin)
) -> SandboxResponse:
    """Create a new sandbox environment."""
    manager = await get_sandbox_manager()
    
    config = None
    if request.config:
        config = SandboxConfig(
            latency_ms=request.config.latency_ms,
            scenario=request.config.scenario,
            quota_daily=request.config.quota_daily,
            quota_hourly=request.config.quota_hourly,
            webhook_url=request.config.webhook_url,
            allowed_endpoints=request.config.allowed_endpoints,
            blocked_endpoints=request.config.blocked_endpoints,
            enable_logging=request.config.enable_logging,
            log_retention_days=request.config.log_retention_days,
        )
    
    sandbox = await manager.create_sandbox(
        partner_id=request.partner_id,
        name=request.name,
        config=config,
        description=request.description,
        expires_days=request.expires_days,
    )
    
    return SandboxResponse(**sandbox.to_dict())


@router.get(
    "/sandboxes",
    response_model=List[SandboxResponse],
    summary="List sandbox environments",
    description="Returns list of sandbox environments."
)
async def list_sandboxes(
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    status: Optional[SandboxStatus] = Query(None, description="Filter by status"),
    current_user: Any = Depends(require_admin)
) -> List[SandboxResponse]:
    """List sandbox environments."""
    manager = await get_sandbox_manager()
    sandboxes = await manager.list_sandboxes(partner_id, status)
    return [SandboxResponse(**s.to_dict()) for s in sandboxes]


@router.get(
    "/sandboxes/{sandbox_id}",
    response_model=SandboxResponse,
    summary="Get sandbox details",
    description="Returns details for a specific sandbox."
)
async def get_sandbox(
    sandbox_id: str,
    current_user: Any = Depends(require_admin)
) -> SandboxResponse:
    """Get sandbox environment details."""
    manager = await get_sandbox_manager()
    sandbox = await manager.get_sandbox(sandbox_id)
    
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )
    
    return SandboxResponse(**sandbox.to_dict())


@router.post(
    "/sandboxes/{sandbox_id}/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Creates a new API key for sandbox access."
)
async def create_api_key(
    sandbox_id: str,
    request: ApiKeyCreateRequest,
    current_user: Any = Depends(require_admin)
) -> ApiKeyResponse:
    """Create an API key for sandbox access."""
    manager = await get_sandbox_manager()
    
    # Verify sandbox exists
    sandbox = await manager.get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )
    
    api_key, secret = await manager.create_api_key(
        sandbox_id=sandbox_id,
        partner_id=sandbox.partner_id,
        expires_days=request.expires_days,
    )
    
    return ApiKeyResponse(
        key_id=api_key.key_id,
        key_secret=secret,
        partner_id=api_key.partner_id,
        sandbox_id=api_key.sandbox_id,
        created_at=api_key.created_at.isoformat(),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
    )


@router.get(
    "/sandboxes/{sandbox_id}/api-keys",
    response_model=List[ApiKeyInfoResponse],
    summary="List API keys",
    description="Returns API keys for a sandbox (without secrets)."
)
async def list_api_keys(
    sandbox_id: str,
    current_user: Any = Depends(require_admin)
) -> List[ApiKeyInfoResponse]:
    """List API keys for a sandbox."""
    # This would be implemented in the manager
    # For now, return empty list
    return []


@router.post(
    "/simulate",
    response_model=SandboxSimulateResponse,
    summary="Simulate API request",
    description="Simulates an API request in the sandbox environment."
)
async def simulate_request(
    request: SandboxSimulateRequest,
    api_key: str = Query(..., description="Sandbox API key"),
    current_user: Any = Depends(get_current_user)
) -> SandboxSimulateResponse:
    """Simulate an API request."""
    manager = await get_sandbox_manager()
    
    response = await manager.simulate_request(
        api_key=api_key,
        method=request.method,
        path=request.path,
        headers=request.headers,
        body=request.body,
    )
    
    return SandboxSimulateResponse(**response)


@router.get(
    "/sandboxes/{sandbox_id}/stats",
    response_model=SandboxUsageStatsResponse,
    summary="Get usage statistics",
    description="Returns usage statistics for a sandbox."
)
async def get_usage_stats(
    sandbox_id: str,
    current_user: Any = Depends(require_admin)
) -> SandboxUsageStatsResponse:
    """Get usage statistics for a sandbox."""
    manager = await get_sandbox_manager()
    
    stats = await manager.get_usage_stats(sandbox_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No statistics found for sandbox {sandbox_id}"
        )
    
    return SandboxUsageStatsResponse(**stats.to_dict())


@router.get(
    "/sandboxes/{sandbox_id}/logs",
    response_model=List[RequestLogResponse],
    summary="Get request logs",
    description="Returns request logs for a sandbox."
)
async def get_request_logs(
    sandbox_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: Any = Depends(require_admin)
) -> List[RequestLogResponse]:
    """Get request logs for a sandbox."""
    manager = await get_sandbox_manager()
    logs = await manager.get_request_logs(sandbox_id, limit, offset)
    return [RequestLogResponse(**log) for log in logs]


@router.post(
    "/sandboxes/{sandbox_id}/webhooks",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook event",
    description="Creates a webhook event for testing."
)
async def create_webhook_event(
    sandbox_id: str,
    request: WebhookEventRequest,
    current_user: Any = Depends(require_admin)
) -> WebhookEventResponse:
    """Create a webhook event."""
    manager = await get_sandbox_manager()
    
    # Verify sandbox exists
    sandbox = await manager.get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )
    
    event = await manager.create_webhook_event(
        sandbox_id=sandbox_id,
        partner_id=sandbox.partner_id,
        event_type=request.event_type,
        payload=request.payload,
    )
    
    return WebhookEventResponse(
        event_id=event.event_id,
        event_type=event.event_type,
        delivery_status=event.delivery_status.value,
        created_at=event.created_at.isoformat(),
    )


@router.put(
    "/sandboxes/{sandbox_id}/config",
    response_model=SandboxResponse,
    summary="Update sandbox config",
    description="Updates sandbox configuration."
)
async def update_sandbox_config(
    sandbox_id: str,
    request: SandboxConfigRequest,
    current_user: Any = Depends(require_admin)
) -> SandboxResponse:
    """Update sandbox configuration."""
    manager = await get_sandbox_manager()
    
    config = SandboxConfig(
        latency_ms=request.latency_ms,
        scenario=request.scenario,
        quota_daily=request.quota_daily,
        quota_hourly=request.quota_hourly,
        webhook_url=request.webhook_url,
        allowed_endpoints=request.allowed_endpoints,
        blocked_endpoints=request.blocked_endpoints,
        enable_logging=request.enable_logging,
        log_retention_days=request.log_retention_days,
    )
    
    success = await manager.update_sandbox_config(sandbox_id, config)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )
    
    sandbox = await manager.get_sandbox(sandbox_id)
    return SandboxResponse(**sandbox.to_dict())


@router.post(
    "/sandboxes/{sandbox_id}/revoke-key/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke API key",
    description="Revokes an API key."
)
async def revoke_api_key(
    sandbox_id: str,
    key_id: str,
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Revoke an API key."""
    manager = await get_sandbox_manager()
    
    success = await manager.revoke_api_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    return {"status": "revoked", "key_id": key_id}


@router.delete(
    "/sandboxes/{sandbox_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete sandbox",
    description="Deletes a sandbox environment (soft delete)."
)
async def delete_sandbox(
    sandbox_id: str,
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Delete a sandbox environment."""
    manager = await get_sandbox_manager()
    
    success = await manager.delete_sandbox(sandbox_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )
    
    return {"status": "deleted", "sandbox_id": sandbox_id}


@router.get(
    "/statistics",
    response_model=SandboxStatisticsResponse,
    summary="Get global statistics",
    description="Returns global sandbox statistics."
)
async def get_global_statistics(
    current_user: Any = Depends(require_admin)
) -> SandboxStatisticsResponse:
    """Get global sandbox statistics."""
    manager = await get_sandbox_manager()
    stats = await manager.get_global_statistics()
    return SandboxStatisticsResponse(**stats)


@router.get(
    "/scenarios",
    response_model=List[Dict[str, str]],
    summary="List available scenarios",
    description="Returns list of available sandbox scenarios."
)
async def list_scenarios(
    current_user: Any = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """List available sandbox scenarios."""
    return [
        {"value": s.value, "name": s.name.replace("_", " ").title()}
        for s in SandboxScenario
    ]


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize sandbox manager",
    description="Initializes the sandbox manager and database tables."
)
async def initialize_manager(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize sandbox manager."""
    manager = await get_sandbox_manager()
    await manager.initialize()
    return {"status": "initialized"}
