"""
Manifest Validation API Router

Provides REST API endpoints for deployment manifest validation including:
- Manifest validation against golden policies
- Policy management
- Validation history
- Compliance reporting
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.manifest_validation import (
    ManifestValidationManager,
    get_validation_manager,
    ValidationSeverity,
    ValidationStatus,
    ResourceType,
    PolicyRuleType,
    GoldenPolicy,
    ValidationRule,
    ManifestValidationResult
)

router = APIRouter(prefix="/manifest-validation", tags=["manifest-validation"])


# Pydantic Models

class ValidationRuleCreate(BaseModel):
    name: str
    description: str
    rule_type: PolicyRuleType
    resource_types: List[ResourceType]
    severity: ValidationSeverity
    enabled: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PolicyCreate(BaseModel):
    name: str
    description: str
    rules: List[ValidationRuleCreate]


class PolicyResponse(BaseModel):
    policy_id: str
    name: str
    description: str
    version: str
    rule_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ManifestValidateRequest(BaseModel):
    manifest_content: str
    manifest_format: str = "yaml"
    policy_id: Optional[str] = None
    manifest_name: str = "unnamed"


class FindingResponse(BaseModel):
    finding_id: str
    rule_id: str
    severity: str
    message: str
    resource_type: Optional[str]
    resource_name: Optional[str]
    resource_namespace: Optional[str]
    field_path: Optional[str]
    suggested_fix: Optional[str]


class ValidationResultResponse(BaseModel):
    validation_id: str
    manifest_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    error_count: int
    warning_count: int
    info_count: int
    findings: List[FindingResponse]
    policy_version: str


class ImageScanRequest(BaseModel):
    image_name: str
    image_tag: str


class ImageScanResponse(BaseModel):
    image_name: str
    image_tag: str
    digest: Optional[str]
    scan_status: str
    scan_completed_at: Optional[datetime]
    allowed: bool
    vulnerabilities_count: int


# Policy Management Endpoints

@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: PolicyCreate,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Create a new validation policy."""
    # Convert rules
    rules = []
    for r in data.rules:
        rules.append(ValidationRule(
            rule_id=f"rule_{hash(r.name) % 1000000:06x}",
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            resource_types=r.resource_types,
            severity=r.severity,
            enabled=r.enabled,
            parameters=r.parameters
        ))
    
    policy = await manager.create_policy(
        name=data.name,
        description=data.description,
        rules=rules
    )
    return _policy_to_response(policy)


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    active_only: bool = True,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """List validation policies."""
    policies = await manager.list_policies(active_only=active_only)
    return [_policy_to_response(p) for p in policies]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Get a policy by ID."""
    policy = await manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_response(policy)


# Validation Endpoints

@router.post("/validate", response_model=ValidationResultResponse)
async def validate_manifest(
    data: ManifestValidateRequest,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Validate a manifest against golden policies."""
    result = await manager.validate_manifest(
        manifest_content=data.manifest_content,
        manifest_format=data.manifest_format,
        policy_id=data.policy_id,
        manifest_name=data.manifest_name
    )
    return _result_to_response(result)


@router.post("/validate/file")
async def validate_manifest_file(
    file: UploadFile = File(...),
    policy_id: Optional[str] = Form(None),
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Validate a manifest file upload."""
    content = await file.read()
    manifest_content = content.decode('utf-8')
    
    # Detect format from filename
    manifest_format = "yaml"
    if file.filename and file.filename.endswith('.json'):
        manifest_format = "json"
    
    result = await manager.validate_manifest(
        manifest_content=manifest_content,
        manifest_format=manifest_format,
        policy_id=policy_id,
        manifest_name=file.filename or "uploaded"
    )
    
    return _result_to_response(result)


@router.get("/validations/{validation_id}", response_model=ValidationResultResponse)
async def get_validation_result(
    validation_id: str,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Get validation result by ID."""
    result = await manager.get_validation_result(validation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Validation result not found")
    return _result_to_response(result)


# Image Scanning Endpoints

@router.post("/scan-image", response_model=ImageScanResponse)
async def scan_image(
    data: ImageScanRequest,
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Scan a container image."""
    result = await manager.scan_image(
        image_name=data.image_name,
        image_tag=data.image_tag
    )
    
    return {
        "image_name": result.image_name,
        "image_tag": result.image_tag,
        "digest": result.digest,
        "scan_status": result.scan_status,
        "scan_completed_at": result.scan_completed_at,
        "allowed": result.allowed,
        "vulnerabilities_count": len(result.vulnerabilities)
    }


# Statistics Endpoints

@router.get("/statistics")
async def get_validation_statistics(
    manager: ManifestValidationManager = Depends(get_validation_manager)
):
    """Get validation statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/severities")
async def list_severities():
    """List validation severity levels."""
    return {
        "severities": [
            {"id": s.value, "name": s.value.upper(), "level": idx}
            for idx, s in enumerate(ValidationSeverity)
        ]
    }


@router.get("/resource-types")
async def list_resource_types():
    """List supported resource types."""
    return {
        "resource_types": [
            {"id": rt.value, "name": rt.value}
            for rt in ResourceType
        ]
    }


@router.get("/rule-types")
async def list_rule_types():
    """List policy rule types."""
    return {
        "rule_types": [
            {"id": rt.value, "name": rt.value.replace("_", " ").title()}
            for rt in PolicyRuleType
        ]
    }


# Helper Functions

def _policy_to_response(policy: GoldenPolicy) -> Dict[str, Any]:
    """Convert GoldenPolicy to response dict."""
    return {
        "policy_id": policy.policy_id,
        "name": policy.name,
        "description": policy.description,
        "version": policy.version,
        "rule_count": len(policy.rules),
        "is_active": policy.is_active,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at
    }


def _finding_to_response(finding) -> Dict[str, Any]:
    """Convert ValidationFinding to response dict."""
    return {
        "finding_id": finding.finding_id,
        "rule_id": finding.rule_id,
        "severity": finding.severity.value,
        "message": finding.message,
        "resource_type": finding.resource_type,
        "resource_name": finding.resource_name,
        "resource_namespace": finding.resource_namespace,
        "field_path": finding.field_path,
        "suggested_fix": finding.suggested_fix
    }


def _result_to_response(result: ManifestValidationResult) -> Dict[str, Any]:
    """Convert ManifestValidationResult to response dict."""
    return {
        "validation_id": result.validation_id,
        "manifest_name": result.manifest_name,
        "status": result.status.value,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "info_count": result.info_count,
        "findings": [_finding_to_response(f) for f in result.findings],
        "policy_version": result.policy_version
    }
