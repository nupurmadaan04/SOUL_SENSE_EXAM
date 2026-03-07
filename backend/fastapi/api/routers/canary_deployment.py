"""
Canary Deployment API Router

Provides REST API endpoints for progressive delivery canary deployments including:
- Deployment creation and management
- Traffic splitting
- Health monitoring and analysis
- Promotion and rollback
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.canary_deployment import (
    CanaryDeploymentManager,
    get_canary_manager,
    CanaryStatus,
    RolloutStrategy,
    MetricOperator,
    HealthStatus,
    CanaryDeployment,
    TrafficSplit,
    CanaryAnalysis,
    DeploymentEvent
)

router = APIRouter(prefix="/canary-deployment", tags=["canary-deployment"])


# Pydantic Models

class MetricThresholdCreate(BaseModel):
    metric_name: str
    operator: MetricOperator
    threshold_value: float
    baseline_comparison: bool = False
    tolerance_percentage: Optional[float] = None
    duration_minutes: int = 5


class CanaryCreate(BaseModel):
    name: str
    description: str
    service_name: str
    namespace: str = "default"
    canary_version: str
    baseline_version: str
    strategy: RolloutStrategy = RolloutStrategy.LINEAR
    num_steps: int = 5
    step_duration_minutes: int = 10
    custom_weights: Optional[List[int]] = None
    auto_promote: bool = False
    auto_rollback: bool = True
    metric_thresholds: List[MetricThresholdCreate] = Field(default_factory=list)


class CanaryResponse(BaseModel):
    canary_id: str
    name: str
    description: str
    service_name: str
    namespace: str
    canary_version: str
    baseline_version: str
    status: str
    strategy: str
    current_step: int
    total_steps: int
    canary_weight: int
    baseline_weight: int
    auto_promote: bool
    auto_rollback: bool
    created_at: datetime
    started_at: Optional[datetime]


class TrafficSplitUpdate(BaseModel):
    canary_percentage: float


class HealthMetricSubmit(BaseModel):
    metric_name: str
    canary_value: float
    baseline_value: Optional[float] = None
    unit: Optional[str] = None


class AnalysisResponse(BaseModel):
    analysis_id: str
    canary_id: str
    step_number: int
    timestamp: datetime
    recommendation: str
    confidence_score: float
    issues: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


class EventResponse(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    message: str
    severity: str
    details: Dict[str, Any]


# Deployment Management Endpoints

@router.post("/deployments", response_model=CanaryResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    data: CanaryCreate,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Create a new canary deployment."""
    # Convert metric thresholds
    thresholds = []
    for t in data.metric_thresholds:
        from backend.fastapi.api.utils.canary_deployment import MetricThreshold
        thresholds.append(MetricThreshold(
            metric_name=t.metric_name,
            operator=t.operator,
            threshold_value=t.threshold_value,
            baseline_comparison=t.baseline_comparison,
            tolerance_percentage=t.tolerance_percentage,
            duration_minutes=t.duration_minutes
        ))
    
    canary = await manager.create_deployment(
        name=data.name,
        description=data.description,
        service_name=data.service_name,
        canary_version=data.canary_version,
        baseline_version=data.baseline_version,
        namespace=data.namespace,
        strategy=data.strategy,
        num_steps=data.num_steps,
        step_duration_minutes=data.step_duration_minutes,
        custom_weights=data.custom_weights,
        auto_promote=data.auto_promote,
        auto_rollback=data.auto_rollback
    )
    
    canary.metric_thresholds = thresholds
    
    return _canary_to_response(canary)


@router.get("/deployments", response_model=List[CanaryResponse])
async def list_deployments(
    service_name: Optional[str] = None,
    status: Optional[CanaryStatus] = None,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """List canary deployments."""
    deployments = await manager.list_deployments(
        service_name=service_name,
        status=status
    )
    return [_canary_to_response(d) for d in deployments]


@router.get("/deployments/{canary_id}", response_model=CanaryResponse)
async def get_deployment(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Get a canary deployment by ID."""
    canary = await manager.get_deployment(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/start")
async def start_deployment(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Start a canary deployment."""
    canary = await manager.start_deployment(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found or already started")
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/pause")
async def pause_deployment(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Pause a canary deployment."""
    canary = await manager.get_deployment(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    canary.status = CanaryStatus.PAUSED
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/resume")
async def resume_deployment(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Resume a paused canary deployment."""
    canary = await manager.get_deployment(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    canary.status = CanaryStatus.RUNNING
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/advance")
async def advance_step(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Advance to the next canary step."""
    canary = await manager.advance_step(canary_id)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found or not running")
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/promote")
async def promote_deployment(
    canary_id: str,
    promoted_by: Optional[str] = None,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Promote canary to full deployment."""
    canary = await manager.promote_deployment(canary_id, promoted_by)
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _canary_to_response(canary)


@router.post("/deployments/{canary_id}/rollback")
async def rollback_deployment(
    canary_id: str,
    reason: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Rollback canary deployment."""
    canary = await manager.rollback_deployment(canary_id, reason, trigger="manual")
    if not canary:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _canary_to_response(canary)


# Traffic Management Endpoints

@router.post("/deployments/{canary_id}/traffic")
async def update_traffic_split(
    canary_id: str,
    data: TrafficSplitUpdate,
    applied_by: Optional[str] = None,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Update traffic split for a canary deployment."""
    split = await manager.update_traffic_split(
        canary_id=canary_id,
        canary_percentage=data.canary_percentage,
        applied_by=applied_by
    )
    
    if not split:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {
        "split_id": split.split_id,
        "canary_percentage": split.canary_percentage,
        "baseline_percentage": split.baseline_percentage,
        "applied_at": split.applied_at
    }


# Health Monitoring Endpoints

@router.post("/deployments/{canary_id}/metrics")
async def submit_metric(
    canary_id: str,
    data: HealthMetricSubmit,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Submit a health metric for a canary deployment."""
    try:
        metric = await manager.record_metric(
            canary_id=canary_id,
            metric_name=data.metric_name,
            canary_value=data.canary_value,
            baseline_value=data.baseline_value,
            unit=data.unit
        )
        
        return {
            "metric_name": metric.metric_name,
            "timestamp": metric.timestamp,
            "canary_value": metric.canary_value,
            "baseline_value": metric.baseline_value,
            "status": metric.status.value
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/deployments/{canary_id}/analyze", response_model=AnalysisResponse)
async def analyze_deployment(
    canary_id: str,
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Analyze canary deployment health."""
    analysis = await manager.analyze_health(canary_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return _analysis_to_response(analysis)


@router.get("/deployments/{canary_id}/analysis", response_model=List[AnalysisResponse])
async def get_analysis_history(
    canary_id: str,
    limit: int = Query(10, ge=1, le=100),
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Get analysis history for a canary deployment."""
    analyses = manager.analyses.get(canary_id, [])[:limit]
    return [_analysis_to_response(a) for a in analyses]


# Event Log Endpoints

@router.get("/deployments/{canary_id}/events", response_model=List[EventResponse])
async def get_deployment_events(
    canary_id: str,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Get events for a canary deployment."""
    events = await manager.get_events(
        canary_id=canary_id,
        event_type=event_type,
        severity=severity,
        limit=limit
    )
    return [_event_to_response(e) for e in events]


# Statistics Endpoints

@router.get("/statistics")
async def get_canary_statistics(
    manager: CanaryDeploymentManager = Depends(get_canary_manager)
):
    """Get canary deployment statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/strategies")
async def list_strategies():
    """List supported rollout strategies."""
    return {
        "strategies": [
            {
                "id": s.value,
                "name": s.value.replace("_", " ").title(),
                "description": _get_strategy_description(s)
            }
            for s in RolloutStrategy
        ]
    }


@router.get("/health-statuses")
async def list_health_statuses():
    """List health status values."""
    return {
        "statuses": [
            {"id": s.value, "name": s.value.title()}
            for s in HealthStatus
        ]
    }


# Helper Functions

def _canary_to_response(canary: CanaryDeployment) -> Dict[str, Any]:
    """Convert CanaryDeployment to response dict."""
    return {
        "canary_id": canary.canary_id,
        "name": canary.name,
        "description": canary.description,
        "service_name": canary.service_name,
        "namespace": canary.namespace,
        "canary_version": canary.canary_version,
        "baseline_version": canary.baseline_version,
        "status": canary.status.value,
        "strategy": canary.strategy.value,
        "current_step": canary.current_step,
        "total_steps": len(canary.steps),
        "canary_weight": canary.canary_weight,
        "baseline_weight": canary.baseline_weight,
        "auto_promote": canary.auto_promote,
        "auto_rollback": canary.auto_rollback,
        "created_at": canary.created_at,
        "started_at": canary.started_at
    }


def _analysis_to_response(analysis: CanaryAnalysis) -> Dict[str, Any]:
    """Convert CanaryAnalysis to response dict."""
    return {
        "analysis_id": analysis.analysis_id,
        "canary_id": analysis.canary_id,
        "step_number": analysis.step_number,
        "timestamp": analysis.timestamp,
        "recommendation": analysis.recommendation,
        "confidence_score": analysis.confidence_score,
        "issues": analysis.issues,
        "warnings": analysis.warnings
    }


def _event_to_response(event: DeploymentEvent) -> Dict[str, Any]:
    """Convert DeploymentEvent to response dict."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "message": event.message,
        "severity": event.severity,
        "details": event.details
    }


def _get_strategy_description(strategy: RolloutStrategy) -> str:
    """Get description for rollout strategy."""
    descriptions = {
        RolloutStrategy.LINEAR: "Equal increments between steps (e.g., 20%, 40%, 60%, 80%, 100%)",
        RolloutStrategy.EXPONENTIAL: "Exponential growth between steps (e.g., 2%, 4%, 8%, 16%, 100%)",
        RolloutStrategy.CUSTOM: "User-defined weights for each step",
        RolloutStrategy.ALL_AT_ONCE: "Single step to 100% traffic"
    }
    return descriptions.get(strategy, "Unknown strategy")
