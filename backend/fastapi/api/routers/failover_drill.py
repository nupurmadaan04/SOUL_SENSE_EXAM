"""
Failover Drill API Endpoints (#1424)

Provides REST API endpoints for database failover drill automation,
health monitoring, and disaster recovery testing.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.failover_drill import (
    get_failover_orchestrator,
    FailoverDrillOrchestrator,
    FailoverScenario,
    DrillStatus,
    HealthCheckType,
    DatabaseEndpoint,
    DrillSchedule,
)
from .auth import require_admin


router = APIRouter(tags=["Failover Drill"], prefix="/admin/failover-drill")


# --- Pydantic Schemas ---

class DatabaseEndpointRequest(BaseModel):
    """Schema for adding a database endpoint."""
    name: str = Field(..., description="Endpoint name")
    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(..., description="Database name")
    is_primary: bool = Field(default=False, description="Is primary endpoint")
    is_replica: bool = Field(default=False, description="Is replica endpoint")
    priority: int = Field(default=0, description="Failover priority")


class DatabaseEndpointResponse(BaseModel):
    """Schema for database endpoint response."""
    name: str
    host: str
    port: int
    database: str
    is_primary: bool
    is_replica: bool
    priority: int
    is_available: bool
    last_checked: Optional[str]


class FailoverDrillRequest(BaseModel):
    """Schema for running a failover drill."""
    scenario: FailoverScenario = Field(default=FailoverScenario.CONTROLLED_FAILOVER)
    validate_replication: bool = Field(default=True)
    auto_rollback: bool = Field(default=True)
    timeout_seconds: int = Field(default=300, ge=60, le=1800)


class HealthCheckResultResponse(BaseModel):
    """Schema for health check result."""
    check_type: str
    endpoint: str
    passed: bool
    latency_ms: float
    message: str
    details: Optional[Dict[str, Any]]
    timestamp: str


class FailoverDrillResultResponse(BaseModel):
    """Schema for failover drill result."""
    drill_id: str
    scenario: str
    status: str
    started_at: str
    completed_at: Optional[str]
    pre_checks: List[HealthCheckResultResponse]
    pre_checks_passed: bool
    failover_started_at: Optional[str]
    failover_completed_at: Optional[str]
    failover_duration_ms: float
    post_checks: List[HealthCheckResultResponse]
    post_checks_passed: bool
    replication_lag_ms: Optional[float]
    data_consistent: Optional[bool]
    rollback_duration_ms: float
    errors: List[str]
    success: bool
    total_duration_ms: float


class DrillScheduleRequest(BaseModel):
    """Schema for drill schedule configuration."""
    enabled: bool = Field(default=False)
    frequency_days: int = Field(default=30, ge=1, le=365)
    preferred_hour: int = Field(default=2, ge=0, le=23)
    scenarios: List[FailoverScenario] = Field(default=[FailoverScenario.CONTROLLED_FAILOVER])
    auto_rollback: bool = Field(default=True)
    notify_on_failure: bool = Field(default=True)


class DrillScheduleResponse(BaseModel):
    """Schema for drill schedule response."""
    enabled: bool
    frequency_days: int
    preferred_hour: int
    scenarios: List[str]
    auto_rollback: bool
    notify_on_failure: bool


class FailoverDrillStatisticsResponse(BaseModel):
    """Schema for drill statistics."""
    total_drills: int
    successful_drills: int
    failed_drills: int
    success_rate: float
    average_failover_time_ms: float
    drills_last_7_days: int
    configured_endpoints: int


class FailoverDrillStatusResponse(BaseModel):
    """Schema for drill status."""
    status: str
    endpoints: List[DatabaseEndpointResponse]
    statistics: FailoverDrillStatisticsResponse
    schedule: DrillScheduleResponse


# --- API Endpoints ---

@router.get(
    "/status",
    response_model=FailoverDrillStatusResponse,
    summary="Get failover drill status",
    description="Returns orchestrator status, endpoints, and statistics."
)
async def get_drill_status(
    current_user: Any = Depends(require_admin)
) -> FailoverDrillStatusResponse:
    """Get failover drill orchestrator status."""
    orchestrator = await get_failover_orchestrator()
    
    # Get statistics
    stats = await orchestrator.get_statistics()
    
    # Get endpoints
    endpoints = [
        DatabaseEndpointResponse(**ep.to_dict())
        for ep in orchestrator.get_endpoints()
    ]
    
    # Get schedule
    schedule = orchestrator.get_schedule()
    
    return FailoverDrillStatusResponse(
        status="healthy" if len(endpoints) > 0 else "unconfigured",
        endpoints=endpoints,
        statistics=FailoverDrillStatisticsResponse(**stats),
        schedule=DrillScheduleResponse(**schedule.to_dict()),
    )


@router.get(
    "/statistics",
    response_model=FailoverDrillStatisticsResponse,
    summary="Get drill statistics",
    description="Returns failover drill statistics."
)
async def get_statistics(
    current_user: Any = Depends(require_admin)
) -> FailoverDrillStatisticsResponse:
    """Get failover drill statistics."""
    orchestrator = await get_failover_orchestrator()
    stats = await orchestrator.get_statistics()
    return FailoverDrillStatisticsResponse(**stats)


@router.post(
    "/endpoints",
    response_model=DatabaseEndpointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add database endpoint",
    description="Adds a database endpoint for failover testing."
)
async def add_endpoint(
    request: DatabaseEndpointRequest,
    current_user: Any = Depends(require_admin)
) -> DatabaseEndpointResponse:
    """Add a database endpoint."""
    orchestrator = await get_failover_orchestrator()
    
    endpoint = DatabaseEndpoint(
        name=request.name,
        host=request.host,
        port=request.port,
        database=request.database,
        is_primary=request.is_primary,
        is_replica=request.is_replica,
        priority=request.priority,
    )
    
    orchestrator.add_endpoint(endpoint)
    
    return DatabaseEndpointResponse(**endpoint.to_dict())


@router.get(
    "/endpoints",
    response_model=List[DatabaseEndpointResponse],
    summary="List endpoints",
    description="Returns all configured database endpoints."
)
async def list_endpoints(
    current_user: Any = Depends(require_admin)
) -> List[DatabaseEndpointResponse]:
    """List all configured endpoints."""
    orchestrator = await get_failover_orchestrator()
    
    return [
        DatabaseEndpointResponse(**ep.to_dict())
        for ep in orchestrator.get_endpoints()
    ]


@router.delete(
    "/endpoints/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove endpoint",
    description="Removes a database endpoint."
)
async def remove_endpoint(
    name: str,
    current_user: Any = Depends(require_admin)
) -> None:
    """Remove a database endpoint."""
    orchestrator = await get_failover_orchestrator()
    orchestrator.remove_endpoint(name)


@router.post(
    "/run",
    response_model=FailoverDrillResultResponse,
    summary="Run failover drill",
    description="Executes a failover drill with the specified scenario."
)
async def run_drill(
    request: FailoverDrillRequest,
    current_user: Any = Depends(require_admin)
) -> FailoverDrillResultResponse:
    """Run a failover drill."""
    orchestrator = await get_failover_orchestrator()
    
    result = await orchestrator.run_drill(
        scenario=request.scenario,
        validate_replication=request.validate_replication,
        auto_rollback=request.auto_rollback,
        timeout_seconds=request.timeout_seconds,
    )
    
    return FailoverDrillResultResponse(**result.to_dict())


@router.get(
    "/history",
    response_model=List[Dict[str, Any]],
    summary="Get drill history",
    description="Returns history of failover drills."
)
async def get_drill_history(
    scenario: Optional[FailoverScenario] = Query(None, description="Filter by scenario"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get failover drill history."""
    orchestrator = await get_failover_orchestrator()
    history = await orchestrator.get_drill_history(scenario, limit)
    return history


@router.get(
    "/schedule",
    response_model=DrillScheduleResponse,
    summary="Get drill schedule",
    description="Returns current drill schedule configuration."
)
async def get_schedule(
    current_user: Any = Depends(require_admin)
) -> DrillScheduleResponse:
    """Get drill schedule."""
    orchestrator = await get_failover_orchestrator()
    schedule = orchestrator.get_schedule()
    return DrillScheduleResponse(**schedule.to_dict())


@router.put(
    "/schedule",
    response_model=DrillScheduleResponse,
    summary="Update drill schedule",
    description="Updates drill schedule configuration."
)
async def update_schedule(
    request: DrillScheduleRequest,
    current_user: Any = Depends(require_admin)
) -> DrillScheduleResponse:
    """Update drill schedule."""
    orchestrator = await get_failover_orchestrator()
    
    schedule = DrillSchedule(
        enabled=request.enabled,
        frequency_days=request.frequency_days,
        preferred_hour=request.preferred_hour,
        scenarios=request.scenarios,
        auto_rollback=request.auto_rollback,
        notify_on_failure=request.notify_on_failure,
    )
    
    orchestrator.configure_schedule(schedule)
    
    return DrillScheduleResponse(**schedule.to_dict())


@router.post(
    "/run-scheduled",
    response_model=Optional[FailoverDrillResultResponse],
    summary="Run scheduled drill",
    description="Runs a scheduled drill if conditions are met."
)
async def run_scheduled_drill(
    current_user: Any = Depends(require_admin)
) -> Optional[FailoverDrillResultResponse]:
    """Run scheduled drill if due."""
    orchestrator = await get_failover_orchestrator()
    
    result = await orchestrator.run_scheduled_drill()
    
    if result is None:
        return None
    
    return FailoverDrillResultResponse(**result.to_dict())


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize orchestrator",
    description="Initializes failover drill orchestrator."
)
async def initialize_orchestrator(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize failover orchestrator."""
    orchestrator = await get_failover_orchestrator()
    await orchestrator.initialize()
    return {
        "status": "initialized",
        "endpoints": str(len(orchestrator.get_endpoints())),
    }


@router.get(
    "/scenarios",
    response_model=List[Dict[str, str]],
    summary="List available scenarios",
    description="Returns list of available failover scenarios."
)
async def list_scenarios(
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, str]]:
    """List available failover scenarios."""
    return [
        {"value": s.value, "name": s.name.replace("_", " ").title()}
        for s in FailoverScenario
    ]


@router.post(
    "/health-check",
    response_model=List[HealthCheckResultResponse],
    summary="Run health checks",
    description="Runs health checks on all configured endpoints."
)
async def run_health_checks(
    current_user: Any = Depends(require_admin)
) -> List[HealthCheckResultResponse]:
    """Run health checks on all endpoints."""
    orchestrator = await get_failover_orchestrator()
    
    # Run health checks
    checks = await orchestrator._run_health_checks("manual")
    
    return [HealthCheckResultResponse(**c.to_dict()) for c in checks]
