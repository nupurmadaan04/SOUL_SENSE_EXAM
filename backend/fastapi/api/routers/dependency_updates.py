"""
Dependency Update Batching API Routes

Provides REST API endpoints for dependency update management,
risk assessment, and batching operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.dependency_update_batching import (
    UpdateType, RiskTier, UpdateStatus, BatchingStrategy, CompatibilityStatus,
    Dependency, AvailableUpdate, UpdateBatch, DeploymentResult,
    DependencyUpdateManager, get_update_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/dependency-updates", tags=["dependency-updates"])


# Pydantic Models

class DependencyRegisterRequest(BaseModel):
    """Request to register dependency."""
    name: str
    current_version: str
    ecosystem: str
    direct_dependency: bool = True
    usage_scope: str = "production"


class DependencyResponse(BaseModel):
    """Response model for dependency."""
    name: str
    current_version: str
    ecosystem: str
    direct_dependency: bool
    usage_scope: str
    known_vulnerabilities: List[Dict[str, Any]]
    license_type: str
    license_compliant: bool


class AvailableUpdateRequest(BaseModel):
    """Request to register available update."""
    dependency_name: str
    new_version: str
    update_type: UpdateType
    changelog: str = ""
    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list)
    published_at: Optional[datetime] = None


class AvailableUpdateResponse(BaseModel):
    """Response model for available update."""
    update_id: str
    dependency_name: str
    current_version: str
    new_version: str
    update_type: UpdateType
    risk_tier: RiskTier
    risk_score: float
    changelog_summary: str
    security_fixes: List[str]
    compatibility_status: CompatibilityStatus
    discovered_at: datetime


class BatchCreateRequest(BaseModel):
    """Request to create batch."""
    name: str
    description: str = ""
    strategy: BatchingStrategy
    update_ids: List[str]
    policy_id: str = "default"


class BatchResponse(BaseModel):
    """Response model for batch."""
    batch_id: str
    name: str
    description: str
    strategy: BatchingStrategy
    status: UpdateStatus
    highest_risk_tier: RiskTier
    total_risk_score: float
    update_count: int
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    requires_approval: bool
    approved_by: str = ""


class BatchApproveRequest(BaseModel):
    """Request to approve batch."""
    pass  # Just needs authentication


class BatchScheduleRequest(BaseModel):
    """Request to schedule batch."""
    scheduled_at: datetime


class DeploymentResponse(BaseModel):
    """Response model for deployment."""
    deployment_id: str
    batch_id: str
    status: UpdateStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    successful_updates: int
    failed_updates: int
    skipped_updates: int
    error_message: str


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    dependencies: Dict[str, Any]
    updates: Dict[str, Any]
    batches: Dict[str, Any]
    deployments: Dict[str, Any]


# Helper Functions

def _dependency_to_response(dep: Dependency) -> DependencyResponse:
    """Convert Dependency to response model."""
    return DependencyResponse(
        name=dep.name,
        current_version=dep.current_version,
        ecosystem=dep.ecosystem,
        direct_dependency=dep.direct_dependency,
        usage_scope=dep.usage_scope,
        known_vulnerabilities=dep.known_vulnerabilities,
        license_type=dep.license_type,
        license_compliant=dep.license_compliant
    )


def _update_to_response(update: AvailableUpdate) -> AvailableUpdateResponse:
    """Convert AvailableUpdate to response model."""
    return AvailableUpdateResponse(
        update_id=update.update_id,
        dependency_name=update.dependency.name,
        current_version=update.dependency.current_version,
        new_version=update.new_version,
        update_type=update.update_type,
        risk_tier=update.risk_tier,
        risk_score=update.risk_score,
        changelog_summary=update.changelog_summary,
        security_fixes=update.security_fixes,
        compatibility_status=update.compatibility_status,
        discovered_at=update.discovered_at
    )


def _batch_to_response(batch: UpdateBatch) -> BatchResponse:
    """Convert UpdateBatch to response model."""
    return BatchResponse(
        batch_id=batch.batch_id,
        name=batch.name,
        description=batch.description,
        strategy=batch.strategy,
        status=batch.status,
        highest_risk_tier=batch.highest_risk_tier,
        total_risk_score=batch.total_risk_score,
        update_count=len(batch.updates),
        created_at=batch.created_at,
        scheduled_at=batch.scheduled_at,
        deployed_at=batch.deployed_at,
        requires_approval=batch.requires_approval,
        approved_by=batch.approved_by
    )


def _deployment_to_response(deploy: DeploymentResult) -> DeploymentResponse:
    """Convert DeploymentResult to response model."""
    return DeploymentResponse(
        deployment_id=deploy.deployment_id,
        batch_id=deploy.batch_id,
        status=deploy.status,
        started_at=deploy.started_at,
        completed_at=deploy.completed_at,
        successful_updates=len(deploy.successful_updates),
        failed_updates=len(deploy.failed_updates),
        skipped_updates=len(deploy.skipped_updates),
        error_message=deploy.error_message
    )


# API Routes

@router.post("/dependencies", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED)
async def register_dependency(
    request: DependencyRegisterRequest,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Register a dependency for tracking.
    
    Requires admin privileges.
    """
    dep = await manager.register_dependency(
        name=request.name,
        current_version=request.current_version,
        ecosystem=request.ecosystem,
        direct_dependency=request.direct_dependency,
        usage_scope=request.usage_scope
    )
    
    return _dependency_to_response(dep)


@router.get("/dependencies", response_model=List[DependencyResponse])
async def list_dependencies(
    ecosystem: Optional[str] = None,
    direct_only: bool = False,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """List tracked dependencies."""
    deps = await manager.list_dependencies(
        ecosystem=ecosystem,
        direct_only=direct_only
    )
    
    return [_dependency_to_response(d) for d in deps]


@router.get("/dependencies/{name}", response_model=DependencyResponse)
async def get_dependency(
    name: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """Get dependency by name."""
    dep = await manager.get_dependency(name)
    
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency {name} not found"
        )
    
    return _dependency_to_response(dep)


@router.post("/updates", response_model=AvailableUpdateResponse, status_code=status.HTTP_201_CREATED)
async def register_available_update(
    request: AvailableUpdateRequest,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Register an available update for a dependency.
    
    Requires admin privileges.
    """
    update = await manager.register_available_update(
        dependency_name=request.dependency_name,
        new_version=request.new_version,
        update_type=request.update_type,
        changelog=request.changelog,
        vulnerabilities=request.vulnerabilities,
        published_at=request.published_at
    )
    
    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency {request.dependency_name} not found"
        )
    
    return _update_to_response(update)


@router.get("/updates", response_model=List[AvailableUpdateResponse])
async def list_available_updates(
    risk_tier: Optional[RiskTier] = None,
    update_type: Optional[UpdateType] = None,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """List available updates."""
    updates = await manager.list_available_updates(
        risk_tier=risk_tier,
        update_type=update_type
    )
    
    return [_update_to_response(u) for u in updates]


@router.get("/updates/{update_id}", response_model=AvailableUpdateResponse)
async def get_available_update(
    update_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """Get available update by ID."""
    update = await manager.get_available_update(update_id)
    
    if not update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Update {update_id} not found"
        )
    
    return _update_to_response(update)


@router.post("/batches", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    request: BatchCreateRequest,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a batch of dependency updates.
    
    Requires admin privileges.
    """
    batch = await manager.create_batch(
        name=request.name,
        description=request.description,
        strategy=request.strategy,
        update_ids=request.update_ids,
        policy_id=request.policy_id
    )
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create batch. Check update IDs."
        )
    
    return _batch_to_response(batch)


@router.get("/batches", response_model=List[BatchResponse])
async def list_batches(
    status: Optional[UpdateStatus] = None,
    strategy: Optional[BatchingStrategy] = None,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """List update batches."""
    batches = await manager.list_batches(
        status=status,
        strategy=strategy
    )
    
    return [_batch_to_response(b) for b in batches]


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """Get batch by ID."""
    batch = await manager.get_batch(batch_id)
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    return _batch_to_response(batch)


@router.post("/batches/{batch_id}/approve", response_model=BatchResponse)
async def approve_batch(
    batch_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Approve a batch for deployment.
    
    Requires admin privileges.
    """
    batch = await manager.approve_batch(
        batch_id=batch_id,
        approved_by=user.get("email", "unknown")
    )
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    return _batch_to_response(batch)


@router.post("/batches/{batch_id}/schedule", response_model=BatchResponse)
async def schedule_batch(
    batch_id: str,
    request: BatchScheduleRequest,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Schedule a batch for deployment.
    
    Requires admin privileges.
    """
    batch = await manager.schedule_batch(batch_id, request.scheduled_at)
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found"
        )
    
    return _batch_to_response(batch)


@router.post("/batches/{batch_id}/deploy", response_model=DeploymentResponse)
async def deploy_batch(
    batch_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Deploy a batch of updates.
    
    Requires admin privileges.
    """
    result = await manager.deploy_batch(
        batch_id=batch_id,
        triggered_by=user.get("email", "unknown")
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch not found or not in deployable state"
        )
    
    return _deployment_to_response(result)


@router.post("/batches/{batch_id}/rollback", response_model=DeploymentResponse)
async def rollback_batch(
    batch_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(require_admin)
):
    """
    Rollback a deployed batch.
    
    Requires admin privileges.
    """
    result = await manager.rollback_batch(
        batch_id=batch_id,
        triggered_by=user.get("email", "unknown")
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch not found, not deployed, or rollback window expired"
        )
    
    return _deployment_to_response(result)


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """Get deployment result by ID."""
    deployment = await manager.get_deployment_result(deployment_id)
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    
    return _deployment_to_response(deployment)


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: DependencyUpdateManager = Depends(get_update_manager),
    user: Dict = Depends(get_current_user)
):
    """Get dependency update statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        dependencies=stats["dependencies"],
        updates=stats["updates"],
        batches=stats["batches"],
        deployments=stats["deployments"]
    )


@router.get("/health")
async def health_check(
    manager: DependencyUpdateManager = Depends(get_update_manager)
):
    """Health check endpoint for dependency update service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "tracked_dependencies": len(manager.dependencies),
        "available_updates": len(manager.available_updates),
        "batches": len(manager.batches)
    }
