"""
Infrastructure Drift Detection API Routes

Provides REST API endpoints for infrastructure drift detection,
IaC state management, and drift alerting.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.infra_drift_detection import (
    DriftStatus, DriftSeverity, IaCProvider, ResourceType,
    DriftedResource, DriftDetectionResult, IaCState, RuntimeState,
    DriftDetectionManager, get_drift_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/drift-detection", tags=["drift-detection"])


# Pydantic Models

class IaCStateCaptureRequest(BaseModel):
    """Request to capture IaC state."""
    provider: IaCProvider
    environment: str
    state_data: Dict[str, Any]
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    pipeline_run_id: Optional[str] = None


class RuntimeStateCaptureRequest(BaseModel):
    """Request to capture runtime state."""
    provider: str
    environment: str
    resources: Dict[str, Any]


class DriftDetectionRequest(BaseModel):
    """Request to run drift detection."""
    iac_state_id: str
    runtime_state_id: str
    scan_name: str
    auto_remediate: bool = False


class ResourceAttributeResponse(BaseModel):
    """Response model for resource attribute."""
    name: str
    iac_value: Optional[Any]
    runtime_value: Optional[Any]
    is_sensitive: bool = False


class DriftedResourceResponse(BaseModel):
    """Response model for drifted resource."""
    resource_id: str
    resource_type: ResourceType
    resource_name: str
    provider: IaCProvider
    drift_status: DriftStatus
    severity: DriftSeverity
    added_attributes: List[ResourceAttributeResponse]
    modified_attributes: List[ResourceAttributeResponse]
    removed_attributes: List[ResourceAttributeResponse]
    region: Optional[str] = None
    remediation_available: bool = False


class DriftDetectionResultResponse(BaseModel):
    """Response model for drift detection result."""
    scan_id: str
    scan_name: str
    status: DriftStatus
    started_at: datetime
    completed_at: Optional[datetime]
    provider: IaCProvider
    environment: str
    region: Optional[str] = None
    total_resources: int
    scanned_resources: int
    drifted_resources: List[DriftedResourceResponse]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    added_resources: int
    modified_resources: int
    removed_resources: int


class IaCStateResponse(BaseModel):
    """Response model for IaC state."""
    state_id: str
    provider: IaCProvider
    environment: str
    captured_at: datetime
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None


class AlertResponse(BaseModel):
    """Response model for drift alert."""
    alert_id: str
    scan_id: str
    severity: DriftSeverity
    resource_id: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    scans: Dict[str, int]
    drift_summary: Dict[str, Any]
    alerts: Dict[str, int]


# Helper Functions

def _drifted_resource_to_response(resource: DriftedResource) -> DriftedResourceResponse:
    """Convert DriftedResource to response model."""
    return DriftedResourceResponse(
        resource_id=resource.resource_id,
        resource_type=resource.resource_type,
        resource_name=resource.resource_name,
        provider=resource.provider,
        drift_status=resource.drift_status,
        severity=resource.severity,
        added_attributes=[
            ResourceAttributeResponse(
                name=a.name,
                iac_value=a.iac_value,
                runtime_value=a.runtime_value,
                is_sensitive=a.is_sensitive
            ) for a in resource.added_attributes
        ],
        modified_attributes=[
            ResourceAttributeResponse(
                name=a.name,
                iac_value=a.iac_value,
                runtime_value=a.runtime_value,
                is_sensitive=a.is_sensitive
            ) for a in resource.modified_attributes
        ],
        removed_attributes=[
            ResourceAttributeResponse(
                name=a.name,
                iac_value=a.iac_value,
                runtime_value=a.runtime_value,
                is_sensitive=a.is_sensitive
            ) for a in resource.removed_attributes
        ],
        region=resource.region,
        remediation_available=resource.remediation_available
    )


def _scan_result_to_response(result: DriftDetectionResult) -> DriftDetectionResultResponse:
    """Convert DriftDetectionResult to response model."""
    return DriftDetectionResultResponse(
        scan_id=result.scan_id,
        scan_name=result.scan_name,
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        provider=result.provider,
        environment=result.environment,
        region=result.region,
        total_resources=result.total_resources,
        scanned_resources=result.scanned_resources,
        drifted_resources=[
            _drifted_resource_to_response(r) for r in result.drifted_resources
        ],
        critical_count=result.critical_count,
        high_count=result.high_count,
        medium_count=result.medium_count,
        low_count=result.low_count,
        added_resources=result.added_resources,
        modified_resources=result.modified_resources,
        removed_resources=result.removed_resources
    )


# API Routes

@router.post("/iac-state", response_model=IaCStateResponse, status_code=status.HTTP_201_CREATED)
async def capture_iac_state(
    request: IaCStateCaptureRequest,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(require_admin)
):
    """
    Capture IaC state snapshot.
    
    Requires admin privileges.
    """
    state = await manager.capture_iac_state(
        provider=request.provider,
        environment=request.environment,
        state_data=request.state_data,
        git_commit=request.git_commit,
        git_branch=request.git_branch,
        pipeline_run_id=request.pipeline_run_id
    )
    
    return IaCStateResponse(
        state_id=state.state_id,
        provider=state.provider,
        environment=state.environment,
        captured_at=state.captured_at,
        git_commit=state.git_commit,
        git_branch=state.git_branch
    )


@router.get("/iac-state", response_model=List[IaCStateResponse])
async def list_iac_states(
    provider: Optional[IaCProvider] = None,
    environment: Optional[str] = None,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """List IaC states with optional filtering."""
    states = await manager.list_iac_states(
        provider=provider,
        environment=environment
    )
    
    return [
        IaCStateResponse(
            state_id=s.state_id,
            provider=s.provider,
            environment=s.environment,
            captured_at=s.captured_at,
            git_commit=s.git_commit,
            git_branch=s.git_branch
        ) for s in states
    ]


@router.get("/iac-state/{state_id}", response_model=IaCStateResponse)
async def get_iac_state(
    state_id: str,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """Get IaC state by ID."""
    state = await manager.get_iac_state(state_id)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IaC state {state_id} not found"
        )
    
    return IaCStateResponse(
        state_id=state.state_id,
        provider=state.provider,
        environment=state.environment,
        captured_at=state.captured_at,
        git_commit=state.git_commit,
        git_branch=state.git_branch
    )


@router.post("/runtime-state", status_code=status.HTTP_201_CREATED)
async def capture_runtime_state(
    request: RuntimeStateCaptureRequest,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(require_admin)
):
    """
    Capture runtime state snapshot.
    
    Requires admin privileges.
    """
    state = await manager.capture_runtime_state(
        provider=request.provider,
        environment=request.environment,
        resources=request.resources
    )
    
    return {
        "state_id": state.state_id,
        "provider": state.provider,
        "environment": state.environment,
        "captured_at": state.captured_at.isoformat()
    }


@router.post("/detect", response_model=DriftDetectionResultResponse)
async def detect_drift(
    request: DriftDetectionRequest,
    background_tasks: BackgroundTasks,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(require_admin)
):
    """
    Run drift detection between IaC and runtime states.
    
    Requires admin privileges.
    """
    result = await manager.detect_drift(
        iac_state_id=request.iac_state_id,
        runtime_state_id=request.runtime_state_id,
        scan_name=request.scan_name,
        auto_remediate=request.auto_remediate
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IaC or runtime state not found"
        )
    
    return _scan_result_to_response(result)


@router.get("/scans", response_model=List[DriftDetectionResultResponse])
async def list_scan_results(
    environment: Optional[str] = None,
    status: Optional[DriftStatus] = None,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """List drift detection scan results."""
    results = await manager.list_scan_results(
        environment=environment,
        status=status
    )
    
    return [_scan_result_to_response(r) for r in results]


@router.get("/scans/{scan_id}", response_model=DriftDetectionResultResponse)
async def get_scan_result(
    scan_id: str,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """Get drift detection scan result by ID."""
    result = await manager.get_scan_result(scan_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan result {scan_id} not found"
        )
    
    return _scan_result_to_response(result)


@router.get("/scans/{scan_id}/drifted-resources", response_model=List[DriftedResourceResponse])
async def get_drifted_resources(
    scan_id: str,
    severity: Optional[DriftSeverity] = None,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """Get drifted resources for a scan."""
    result = await manager.get_scan_result(scan_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan result {scan_id} not found"
        )
    
    resources = result.drifted_resources
    
    if severity:
        resources = [r for r in resources if r.severity == severity]
    
    return [_drifted_resource_to_response(r) for r in resources]


@router.post("/scans/{scan_id}/resources/{resource_id}/remediate")
async def generate_remediation(
    scan_id: str,
    resource_id: str,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(require_admin)
):
    """
    Generate remediation script for drifted resource.
    
    Requires admin privileges.
    """
    script = await manager.generate_remediation(scan_id, resource_id)
    
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan or resource not found"
        )
    
    return {
        "scan_id": scan_id,
        "resource_id": resource_id,
        "remediation_script": script,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    scan_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """Get drift alerts with optional filtering."""
    alerts = await manager.get_alerts(
        scan_id=scan_id,
        acknowledged=acknowledged
    )
    
    return [
        AlertResponse(
            alert_id=a.alert_id,
            scan_id=a.scan_id,
            severity=a.severity,
            resource_id=a.resource_id,
            message=a.message,
            created_at=a.created_at,
            acknowledged=a.acknowledged,
            acknowledged_by=a.acknowledged_by
        ) for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(require_admin)
):
    """
    Acknowledge a drift alert.
    
    Requires admin privileges.
    """
    alert = await manager.acknowledge_alert(alert_id, user.get("email", "unknown"))
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )
    
    return {
        "alert_id": alert.alert_id,
        "acknowledged": alert.acknowledged,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: DriftDetectionManager = Depends(get_drift_manager),
    user: Dict = Depends(get_current_user)
):
    """Get drift detection statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        scans=stats["scans"],
        drift_summary=stats["drift_summary"],
        alerts=stats["alerts"]
    )


@router.get("/health")
async def health_check(
    manager: DriftDetectionManager = Depends(get_drift_manager)
):
    """Health check endpoint for drift detection service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "total_scans": len(manager.scan_results),
        "total_alerts": len(manager.alerts)
    }
