"""
Ephemeral Preview Environments API Routes

Provides REST API endpoints for managing ephemeral preview environments
for pull requests and feature branches.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.ephemeral_environments import (
    EnvironmentStatus, EnvironmentSize, EnvironmentType, AccessLevel,
    ResourceAllocation, DeploymentConfig, DomainConfig, EnvironmentMetrics,
    PreviewEnvironment, EnvironmentTemplate, EnvironmentBudget, EnvironmentEvent,
    EphemeralEnvironmentManager, get_ephemeral_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/ephemeral-environments", tags=["ephemeral-environments"])


# Pydantic Models

class DeploymentConfigRequest(BaseModel):
    """Request for deployment configuration."""
    image_repository: str
    image_tag: str
    container_port: int = 8080
    env_vars: Dict[str, str] = Field(default_factory=dict)
    secrets: List[str] = Field(default_factory=list)
    health_check_path: str = "/health"
    readiness_timeout_seconds: int = 60
    min_replicas: int = 1
    max_replicas: int = 1


class EnvironmentCreateRequest(BaseModel):
    """Request to create ephemeral environment."""
    name: str
    environment_type: EnvironmentType
    repository_url: str
    branch_name: str
    commit_sha: str
    deployment_config: DeploymentConfigRequest
    pull_request_number: Optional[int] = None
    size: Optional[EnvironmentSize] = None
    template_id: str = "default"
    access_level: Optional[AccessLevel] = None
    ttl_hours: int = 24
    auto_destroy_on_pr_close: bool = True
    auto_destroy_after_inactive_minutes: int = 480


class EnvironmentResponse(BaseModel):
    """Response model for environment."""
    environment_id: str
    name: str
    environment_type: EnvironmentType
    repository_url: str
    branch_name: str
    commit_sha: str
    pull_request_number: Optional[int] = None
    size: EnvironmentSize
    status: EnvironmentStatus
    status_message: str
    url: str
    admin_url: str
    created_at: datetime
    ready_at: Optional[datetime] = None
    last_deployed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    labels: Dict[str, str]


class TemplateCreateRequest(BaseModel):
    """Request to create environment template."""
    template_id: str
    name: str
    description: str = ""
    default_size: EnvironmentSize = EnvironmentSize.MEDIUM
    default_ttl_hours: int = 24
    domain_suffix: str = "preview.example.com"


class TemplateResponse(BaseModel):
    """Response model for template."""
    template_id: str
    name: str
    description: str
    default_size: EnvironmentSize
    default_ttl_hours: int
    domain_suffix: str


class BudgetResponse(BaseModel):
    """Response model for budget."""
    budget_id: str
    name: str
    max_environments: int
    max_concurrent_running: int
    max_monthly_cost_usd: float
    current_environments: int
    current_running: int
    current_monthly_cost_usd: float


class MetricsResponse(BaseModel):
    """Response model for metrics."""
    cpu_usage_percent: float
    memory_usage_mb: int
    storage_usage_gb: float
    request_count: int
    error_count: int
    avg_response_time_ms: float
    total_uptime_minutes: int
    last_activity_at: Optional[datetime] = None
    estimated_cost_usd: float


class EventResponse(BaseModel):
    """Response model for event."""
    event_id: str
    event_type: str
    message: str
    timestamp: datetime
    actor: str
    metadata: Dict[str, Any]


class PRWebhookRequest(BaseModel):
    """Request for PR webhook."""
    action: str
    pull_request_number: int
    branch_name: str
    commit_sha: str
    repository_url: str
    sender: str = ""


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    environments: Dict[str, Any]
    resources: Dict[str, Any]
    cost: Dict[str, float]


# Helper Functions

def _deployment_config_from_request(req: DeploymentConfigRequest) -> DeploymentConfig:
    """Convert DeploymentConfigRequest to DeploymentConfig."""
    return DeploymentConfig(
        image_repository=req.image_repository,
        image_tag=req.image_tag,
        container_port=req.container_port,
        env_vars=req.env_vars,
        secrets=req.secrets,
        health_check_path=req.health_check_path,
        readiness_timeout_seconds=req.readiness_timeout_seconds,
        min_replicas=req.min_replicas,
        max_replicas=req.max_replicas
    )


def _environment_to_response(env: PreviewEnvironment) -> EnvironmentResponse:
    """Convert PreviewEnvironment to response model."""
    return EnvironmentResponse(
        environment_id=env.environment_id,
        name=env.name,
        environment_type=env.environment_type,
        repository_url=env.repository_url,
        branch_name=env.branch_name,
        commit_sha=env.commit_sha,
        pull_request_number=env.pull_request_number,
        size=env.size,
        status=env.status,
        status_message=env.status_message,
        url=env.url,
        admin_url=env.admin_url,
        created_at=env.created_at,
        ready_at=env.ready_at,
        last_deployed_at=env.last_deployed_at,
        expires_at=env.expires_at,
        labels=env.labels
    )


# API Routes

@router.post("/environments", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    request: EnvironmentCreateRequest,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a new ephemeral preview environment.
    
    Requires admin privileges.
    """
    deployment_config = _deployment_config_from_request(request.deployment_config)
    
    env = await manager.create_environment(
        name=request.name,
        environment_type=request.environment_type,
        repository_url=request.repository_url,
        branch_name=request.branch_name,
        commit_sha=request.commit_sha,
        deployment_config=deployment_config,
        pull_request_number=request.pull_request_number,
        size=request.size,
        template_id=request.template_id,
        access_level=request.access_level,
        ttl_hours=request.ttl_hours,
        created_by=user.get("email", "unknown")
    )
    
    if not env:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create environment. Check budget limits and template configuration."
        )
    
    return _environment_to_response(env)


@router.get("/environments", response_model=List[EnvironmentResponse])
async def list_environments(
    status: Optional[EnvironmentStatus] = None,
    environment_type: Optional[EnvironmentType] = None,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """List ephemeral environments with optional filtering."""
    environments = await manager.list_environments(
        status=status,
        environment_type=environment_type
    )
    
    return [_environment_to_response(e) for e in environments]


@router.get("/environments/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get environment by ID."""
    env = await manager.get_environment(environment_id)
    
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    return _environment_to_response(env)


@router.post("/environments/{environment_id}/deploy")
async def deploy_environment(
    environment_id: str,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(require_admin)
):
    """
    Deploy or redeploy environment.
    
    Requires admin privileges.
    """
    result = await manager.deploy_environment(
        environment_id=environment_id,
        deployed_by=user.get("email", "unknown")
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Environment not found or not in deployable state"
        )
    
    env = await manager.get_environment(environment_id)
    return _environment_to_response(env)


@router.delete("/environments/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_environment(
    environment_id: str,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(require_admin)
):
    """
    Destroy an ephemeral environment.
    
    Requires admin privileges.
    """
    result = await manager.destroy_environment(
        environment_id=environment_id,
        destroyed_by=user.get("email", "unknown"),
        reason="Manual destruction via API"
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment {environment_id} not found"
        )
    
    return None


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: TemplateCreateRequest,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create an environment template.
    
    Requires admin privileges.
    """
    template = await manager.create_template(
        template_id=request.template_id,
        name=request.name,
        description=request.description,
        default_size=request.default_size,
        default_ttl_hours=request.default_ttl_hours,
        domain_suffix=request.domain_suffix
    )
    
    return TemplateResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        default_size=template.default_size,
        default_ttl_hours=template.default_ttl_hours,
        domain_suffix=template.domain_suffix
    )


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """List environment templates."""
    templates = await manager.list_templates()
    
    return [
        TemplateResponse(
            template_id=t.template_id,
            name=t.name,
            description=t.description,
            default_size=t.default_size,
            default_ttl_hours=t.default_ttl_hours,
            domain_suffix=t.domain_suffix
        ) for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get environment template by ID."""
    template = await manager.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    return TemplateResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        default_size=template.default_size,
        default_ttl_hours=template.default_ttl_hours,
        domain_suffix=template.domain_suffix
    )


@router.get("/environments/{environment_id}/metrics", response_model=MetricsResponse)
async def get_environment_metrics(
    environment_id: str,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get environment metrics."""
    metrics = await manager.get_metrics(environment_id)
    
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics for environment {environment_id} not found"
        )
    
    return MetricsResponse(
        cpu_usage_percent=metrics.cpu_usage_percent,
        memory_usage_mb=metrics.memory_usage_mb,
        storage_usage_gb=metrics.storage_usage_gb,
        request_count=metrics.request_count,
        error_count=metrics.error_count,
        avg_response_time_ms=metrics.avg_response_time_ms,
        total_uptime_minutes=metrics.total_uptime_minutes,
        last_activity_at=metrics.last_activity_at,
        estimated_cost_usd=metrics.estimated_cost_usd
    )


@router.get("/environments/{environment_id}/events", response_model=List[EventResponse])
async def get_environment_events(
    environment_id: str,
    event_type: Optional[str] = None,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get events for an environment."""
    events = await manager.get_environment_events(environment_id, event_type)
    
    return [
        EventResponse(
            event_id=e.event_id,
            event_type=e.event_type,
            message=e.message,
            timestamp=e.timestamp,
            actor=e.actor,
            metadata=e.metadata
        ) for e in events
    ]


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get environment budget."""
    budget = await manager.get_budget("default")
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    return BudgetResponse(
        budget_id=budget.budget_id,
        name=budget.name,
        max_environments=budget.max_environments,
        max_concurrent_running=budget.max_concurrent_running,
        max_monthly_cost_usd=budget.max_monthly_cost_usd,
        current_environments=budget.current_environments,
        current_running=budget.current_running,
        current_monthly_cost_usd=budget.current_monthly_cost_usd
    )


@router.post("/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: PRWebhookRequest,
    background_tasks: BackgroundTasks,
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager)
):
    """
    GitHub webhook endpoint for PR events.
    
    Handles PR opened, synchronized, and closed events to automatically
    manage ephemeral preview environments.
    """
    # Handle event in background
    background_tasks.add_task(
        manager.handle_pr_event,
        action=request.action,
        pull_request_number=request.pull_request_number,
        branch_name=request.branch_name,
        commit_sha=request.commit_sha,
        repository_url=request.repository_url,
        sender=request.sender
    )
    
    return {
        "status": "accepted",
        "action": request.action,
        "pull_request_number": request.pull_request_number,
        "message": f"Processing {request.action} event for PR #{request.pull_request_number}"
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager),
    user: Dict = Depends(get_current_user)
):
    """Get ephemeral environment statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        environments=stats["environments"],
        resources=stats["resources"],
        cost=stats["cost"]
    )


@router.get("/health")
async def health_check(
    manager: EphemeralEnvironmentManager = Depends(get_ephemeral_manager)
):
    """Health check endpoint for ephemeral environments service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "total_environments": len(manager.environments),
        "running_environments": len([
            e for e in manager.environments.values()
            if e.status == EnvironmentStatus.RUNNING
        ])
    }
