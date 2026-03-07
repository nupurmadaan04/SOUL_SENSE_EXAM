"""
Onboarding Template API Router (#1439)

REST API endpoints for managing multi-tenant onboarding templates and executions.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.onboarding_template_generator import (
    get_template_generator,
    OnboardingTemplateGenerator,
    TemplateConfig,
    TemplateStatus,
    OnboardingStatus,
    ResourceType,
    ResourceConfig,
    OnboardingStep,
)
from .auth import require_admin, get_current_user


router = APIRouter(tags=["Onboarding Templates"], prefix="/onboarding")


# --- Pydantic Schemas ---

class ResourceConfigRequest(BaseModel):
    """Schema for resource configuration."""
    resource_type: ResourceType
    resource_name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    required: bool = Field(default=True)


class OnboardingStepRequest(BaseModel):
    """Schema for onboarding step."""
    name: str
    description: Optional[str] = None
    action_type: str = Field(..., pattern="^(validate|provision|configure|notify)$")
    config: Dict[str, Any]
    dependencies: List[str] = Field(default_factory=list)
    required: bool = Field(default=True)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    retry_count: int = Field(default=3, ge=0, le=10)


class TemplateConfigRequest(BaseModel):
    """Schema for template configuration."""
    resources: List[ResourceConfigRequest] = Field(default_factory=list)
    steps: List[OnboardingStepRequest] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    validations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemplateCreateRequest(BaseModel):
    """Schema for creating a template."""
    name: str = Field(..., description="Template name")
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    config: TemplateConfigRequest
    parent_template_id: Optional[str] = None


class TemplateResponse(BaseModel):
    """Schema for template response."""
    template_id: str
    name: str
    description: Optional[str]
    version: str
    config: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    created_by: Optional[str]
    parent_template_id: Optional[str]


class GenerateOnboardingRequest(BaseModel):
    """Schema for generating onboarding."""
    template_id: str
    tenant_data: Dict[str, Any]
    tenant_id: Optional[str] = None


class TenantOnboardingResponse(BaseModel):
    """Schema for tenant onboarding response."""
    onboarding_id: str
    template_id: str
    tenant_id: str
    tenant_name: str
    tenant_data: Dict[str, Any]
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress_percentage: float
    current_step: Optional[str]
    results: Dict[str, Any]
    errors: List[str]


class ValidationResultResponse(BaseModel):
    """Schema for validation result."""
    is_valid: bool
    issues: List[Dict[str, Any]]


class StepExecutionResponse(BaseModel):
    """Schema for step execution result."""
    step_id: str
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str]
    execution_time_ms: float
    retry_count: int


class OnboardingStatisticsResponse(BaseModel):
    """Schema for onboarding statistics."""
    total_templates: int
    active_templates: int
    total_onboardings: int
    status_breakdown: Dict[str, int]
    recent_completions_24h: int
    timestamp: str


# --- API Endpoints ---

@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create onboarding template",
    description="Creates a new onboarding template for multi-tenant setup."
)
async def create_template(
    request: TemplateCreateRequest,
    current_user: Any = Depends(require_admin)
) -> TemplateResponse:
    """Create a new onboarding template."""
    generator = await get_template_generator()
    
    # Build config
    resources = [
        ResourceConfig(
            resource_type=r.resource_type,
            resource_name=r.resource_name,
            config=r.config,
            dependencies=r.dependencies,
            required=r.required,
        )
        for r in request.config.resources
    ]
    
    steps = [
        OnboardingStep(
            step_id=f"step_{i}",
            name=s.name,
            description=s.description,
            action_type=s.action_type,
            config=s.config,
            dependencies=s.dependencies,
            required=s.required,
            timeout_seconds=s.timeout_seconds,
            retry_count=s.retry_count,
        )
        for i, s in enumerate(request.config.steps)
    ]
    
    config = TemplateConfig(
        resources=resources,
        steps=steps,
        settings=request.config.settings,
        validations=request.config.validations,
        metadata=request.config.metadata,
    )
    
    template = await generator.create_template(
        name=request.name,
        description=request.description,
        version=request.version,
        config=config,
        created_by=getattr(current_user, 'id', None) if current_user else None,
        parent_template_id=request.parent_template_id,
    )
    
    return TemplateResponse(**template.to_dict())


@router.get(
    "/templates",
    response_model=List[TemplateResponse],
    summary="List templates",
    description="Returns list of onboarding templates."
)
async def list_templates(
    status: Optional[TemplateStatus] = Query(None, description="Filter by status"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[TemplateResponse]:
    """List onboarding templates."""
    generator = await get_template_generator()
    templates = await generator.list_templates(status=status, limit=limit)
    return [TemplateResponse(**t.to_dict()) for t in templates]


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get template details",
    description="Returns details for a specific template."
)
async def get_template(
    template_id: str,
    current_user: Any = Depends(require_admin)
) -> TemplateResponse:
    """Get template details."""
    generator = await get_template_generator()
    template = await generator.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    return TemplateResponse(**template.to_dict())


@router.post(
    "/templates/{template_id}/activate",
    response_model=TemplateResponse,
    summary="Activate template",
    description="Activates a template for use."
)
async def activate_template(
    template_id: str,
    current_user: Any = Depends(require_admin)
) -> TemplateResponse:
    """Activate a template."""
    generator = await get_template_generator()
    
    success = await generator.activate_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not activate template {template_id}"
        )
    
    template = await generator.get_template(template_id)
    return TemplateResponse(**template.to_dict())


@router.post(
    "/generate",
    response_model=TenantOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate onboarding",
    description="Generates a new tenant onboarding from a template."
)
async def generate_onboarding(
    request: GenerateOnboardingRequest,
    current_user: Any = Depends(require_admin)
) -> TenantOnboardingResponse:
    """Generate a tenant onboarding."""
    generator = await get_template_generator()
    
    onboarding = await generator.generate_onboarding(
        template_id=request.template_id,
        tenant_data=request.tenant_data,
        tenant_id=request.tenant_id,
    )
    
    if not onboarding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not generate onboarding. Template may not exist or not be active."
        )
    
    return TenantOnboardingResponse(**onboarding.to_dict())


@router.post(
    "/{onboarding_id}/execute",
    response_model=TenantOnboardingResponse,
    summary="Execute onboarding",
    description="Executes the onboarding process."
)
async def execute_onboarding(
    onboarding_id: str,
    current_user: Any = Depends(require_admin)
) -> TenantOnboardingResponse:
    """Execute an onboarding."""
    generator = await get_template_generator()
    
    try:
        onboarding = await generator.execute_onboarding(onboarding_id)
        return TenantOnboardingResponse(**onboarding.to_dict())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/templates/{template_id}/validate",
    response_model=ValidationResultResponse,
    summary="Validate tenant data",
    description="Validates tenant data against template requirements."
)
async def validate_tenant_data(
    template_id: str,
    tenant_data: Dict[str, Any],
    current_user: Any = Depends(require_admin)
) -> ValidationResultResponse:
    """Validate tenant data."""
    generator = await get_template_generator()
    
    result = await generator.validate_tenant_data(template_id, tenant_data)
    return ValidationResultResponse(**result.to_dict())


@router.get(
    "/{onboarding_id}",
    response_model=TenantOnboardingResponse,
    summary="Get onboarding details",
    description="Returns details for a specific onboarding."
)
async def get_onboarding(
    onboarding_id: str,
    current_user: Any = Depends(require_admin)
) -> TenantOnboardingResponse:
    """Get onboarding details."""
    generator = await get_template_generator()
    onboarding = await generator.get_onboarding(onboarding_id)
    
    if not onboarding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Onboarding {onboarding_id} not found"
        )
    
    return TenantOnboardingResponse(**onboarding.to_dict())


@router.get(
    "",
    response_model=List[TenantOnboardingResponse],
    summary="List onboardings",
    description="Returns list of tenant onboardings."
)
async def list_onboardings(
    status: Optional[OnboardingStatus] = Query(None, description="Filter by status"),
    template_id: Optional[str] = Query(None, description="Filter by template"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[TenantOnboardingResponse]:
    """List tenant onboardings."""
    generator = await get_template_generator()
    onboardings = await generator.list_onboardings(
        status=status,
        template_id=template_id,
        limit=limit,
    )
    return [TenantOnboardingResponse(**o.to_dict()) for o in onboardings]


@router.get(
    "/{onboarding_id}/logs",
    response_model=List[Dict[str, Any]],
    summary="Get step logs",
    description="Returns step execution logs for an onboarding."
)
async def get_step_logs(
    onboarding_id: str,
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get step execution logs."""
    generator = await get_template_generator()
    logs = await generator.get_step_logs(onboarding_id)
    return logs


@router.get(
    "/statistics/global",
    response_model=OnboardingStatisticsResponse,
    summary="Get global statistics",
    description="Returns global onboarding statistics."
)
async def get_statistics(
    current_user: Any = Depends(require_admin)
) -> OnboardingStatisticsResponse:
    """Get global statistics."""
    generator = await get_template_generator()
    stats = await generator.get_statistics()
    return OnboardingStatisticsResponse(**stats)


@router.get(
    "/resource-types",
    response_model=List[Dict[str, str]],
    summary="List resource types",
    description="Returns available resource types."
)
async def list_resource_types(
    current_user: Any = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """List resource types."""
    return [
        {"value": r.value, "name": r.name.replace("_", " ").title()}
        for r in ResourceType
    ]


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize generator",
    description="Initializes the onboarding template generator."
)
async def initialize_generator(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize the template generator."""
    generator = await get_template_generator()
    await generator.initialize()
    return {"status": "initialized"}
