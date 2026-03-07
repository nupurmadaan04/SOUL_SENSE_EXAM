"""
Artifact Provenance and Signature Verification API Routes

Provides REST API endpoints for artifact provenance tracking,
signature generation and verification, and supply chain security.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.artifact_provenance import (
    ArtifactType, SignatureAlgorithm, VerificationStatus, ProvenanceLevel,
    BuildMetadata, Signature, ProvenanceAttestation, Artifact, VerificationPolicy,
    VerificationResult, ArtifactChain, ArtifactProvenanceManager, get_provenance_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/artifact-provenance", tags=["artifact-provenance"])


# Pydantic Models

class BuildMetadataRequest(BaseModel):
    """Request for build metadata."""
    build_id: str
    builder_id: str
    build_type: str
    build_invocation_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    repository_url: Optional[str] = None
    repository_commit: Optional[str] = None
    repository_branch: Optional[str] = None
    repository_tag: Optional[str] = None
    build_config: Dict[str, Any] = Field(default_factory=dict)
    build_params: Dict[str, Any] = Field(default_factory=dict)
    build_environment: Dict[str, str] = Field(default_factory=dict)
    builder_version: Optional[str] = None


class ArtifactRegisterRequest(BaseModel):
    """Request to register an artifact."""
    name: str
    version: str
    artifact_type: ArtifactType
    digest: str
    digest_algorithm: str = "sha256"
    size_bytes: int = 0
    storage_location: Optional[str] = None
    storage_provider: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    """Response model for artifact."""
    artifact_id: str
    name: str
    version: str
    artifact_type: ArtifactType
    digest: str
    digest_algorithm: str
    size_bytes: int
    storage_location: Optional[str] = None
    storage_provider: Optional[str] = None
    created_at: datetime
    created_by: str
    labels: Dict[str, str]
    verification_status: VerificationStatus
    last_verified_at: Optional[datetime] = None
    is_deployed: bool
    deployment_count: int
    last_deployed_at: Optional[datetime] = None


class ProvenanceCreateRequest(BaseModel):
    """Request to create provenance attestation."""
    artifact_id: str
    build_metadata: BuildMetadataRequest
    level: ProvenanceLevel = ProvenanceLevel.LEVEL_1
    materials: List[Dict[str, Any]] = Field(default_factory=list)
    products: List[Dict[str, Any]] = Field(default_factory=list)


class ProvenanceResponse(BaseModel):
    """Response model for provenance attestation."""
    attestation_id: str
    artifact_id: str
    level: ProvenanceLevel
    created_at: datetime
    created_by: str
    json_representation: str


class SignatureRequest(BaseModel):
    """Request to sign an artifact."""
    artifact_id: str
    private_key_pem: str
    algorithm: SignatureAlgorithm
    signer_id: str
    expires_at: Optional[datetime] = None


class SignatureResponse(BaseModel):
    """Response model for signature."""
    signature_id: str
    algorithm: SignatureAlgorithm
    signed_by: str
    signed_at: datetime
    expires_at: Optional[datetime] = None
    content_hash: str
    verification_status: VerificationStatus
    verified_at: Optional[datetime] = None


class VerificationRequest(BaseModel):
    """Request to verify an artifact."""
    artifact_id: str
    policy_id: str = "default"


class VerificationResponse(BaseModel):
    """Response model for verification result."""
    result_id: str
    artifact_id: str
    policy_id: str
    status: VerificationStatus
    verified_at: datetime
    signature_valid: bool
    signature_message: str
    provenance_valid: bool
    provenance_message: str
    policy_compliant: bool
    policy_violations: List[str]
    errors: List[str]


class PolicyCreateRequest(BaseModel):
    """Request to create verification policy."""
    policy_id: str
    name: str
    description: str = ""
    require_signature: bool = True
    require_provenance: bool = True
    minimum_provenance_level: ProvenanceLevel = ProvenanceLevel.LEVEL_1
    enforcement_mode: str = "enforce"


class PolicyResponse(BaseModel):
    """Response model for verification policy."""
    policy_id: str
    name: str
    description: str
    require_signature: bool
    require_provenance: bool
    minimum_provenance_level: ProvenanceLevel
    enforcement_mode: str


class DeploymentRecordRequest(BaseModel):
    """Request to record deployment."""
    artifact_id: str
    deployment_location: str
    deployment_details: Optional[Dict[str, Any]] = None


class ChainOfCustodyResponse(BaseModel):
    """Response model for chain of custody."""
    chain_id: str
    artifact_id: str
    events: List[Dict[str, Any]]
    current_location: Optional[str] = None
    current_status: str


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    artifacts: Dict[str, Any]
    policies: Dict[str, int]
    verifications: Dict[str, int]


# Helper Functions

def _build_metadata_from_request(req: BuildMetadataRequest) -> BuildMetadata:
    """Convert BuildMetadataRequest to BuildMetadata."""
    return BuildMetadata(
        build_id=req.build_id,
        builder_id=req.builder_id,
        build_type=req.build_type,
        build_invocation_id=req.build_invocation_id,
        started_at=req.started_at,
        completed_at=req.completed_at,
        repository_url=req.repository_url,
        repository_commit=req.repository_commit,
        repository_branch=req.repository_branch,
        repository_tag=req.repository_tag,
        build_config=req.build_config,
        build_params=req.build_params,
        build_environment=req.build_environment,
        builder_version=req.builder_version
    )


def _artifact_to_response(artifact: Artifact) -> ArtifactResponse:
    """Convert Artifact to response model."""
    return ArtifactResponse(
        artifact_id=artifact.artifact_id,
        name=artifact.name,
        version=artifact.version,
        artifact_type=artifact.artifact_type,
        digest=artifact.digest,
        digest_algorithm=artifact.digest_algorithm,
        size_bytes=artifact.size_bytes,
        storage_location=artifact.storage_location,
        storage_provider=artifact.storage_provider,
        created_at=artifact.created_at,
        created_by=artifact.created_by,
        labels=artifact.labels,
        verification_status=artifact.verification_status,
        last_verified_at=artifact.last_verified_at,
        is_deployed=artifact.is_deployed,
        deployment_count=artifact.deployment_count,
        last_deployed_at=artifact.last_deployed_at
    )


# API Routes

@router.post("/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def register_artifact(
    request: ArtifactRegisterRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Register a new artifact.
    
    Requires admin privileges.
    """
    artifact = await manager.register_artifact(
        name=request.name,
        version=request.version,
        artifact_type=request.artifact_type,
        digest=request.digest,
        size_bytes=request.size_bytes,
        storage_location=request.storage_location,
        storage_provider=request.storage_provider,
        created_by=user.get("email", "unknown"),
        labels=request.labels
    )
    
    return _artifact_to_response(artifact)


@router.get("/artifacts", response_model=List[ArtifactResponse])
async def list_artifacts(
    artifact_type: Optional[ArtifactType] = None,
    verification_status: Optional[VerificationStatus] = None,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """List artifacts with optional filtering."""
    artifacts = await manager.list_artifacts(
        artifact_type=artifact_type,
        verification_status=verification_status
    )
    
    return [_artifact_to_response(a) for a in artifacts]


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """Get artifact by ID."""
    artifact = await manager.get_artifact(artifact_id)
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    return _artifact_to_response(artifact)


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: str,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Delete an artifact.
    
    Requires admin privileges.
    """
    result = await manager.delete_artifact(artifact_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    return None


@router.post("/provenance", response_model=ProvenanceResponse, status_code=status.HTTP_201_CREATED)
async def create_provenance(
    request: ProvenanceCreateRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create provenance attestation for an artifact.
    
    Requires admin privileges.
    """
    build_metadata = _build_metadata_from_request(request.build_metadata)
    
    attestation = await manager.create_provenance(
        artifact_id=request.artifact_id,
        build_metadata=build_metadata,
        level=request.level,
        materials=request.materials,
        products=request.products,
        created_by=user.get("email", "unknown")
    )
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {request.artifact_id} not found"
        )
    
    return ProvenanceResponse(
        attestation_id=attestation.attestation_id,
        artifact_id=attestation.artifact_id,
        level=attestation.level,
        created_at=attestation.created_at,
        created_by=attestation.created_by,
        json_representation=attestation.to_json()
    )


@router.get("/artifacts/{artifact_id}/provenance", response_model=ProvenanceResponse)
async def get_provenance(
    artifact_id: str,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """Get provenance attestation for an artifact."""
    provenance = await manager.get_provenance(artifact_id)
    
    if not provenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provenance for artifact {artifact_id} not found"
        )
    
    return ProvenanceResponse(
        attestation_id=provenance.attestation_id,
        artifact_id=provenance.artifact_id,
        level=provenance.level,
        created_at=provenance.created_at,
        created_by=provenance.created_by,
        json_representation=provenance.to_json()
    )


@router.post("/sign", response_model=SignatureResponse, status_code=status.HTTP_201_CREATED)
async def sign_artifact(
    request: SignatureRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Sign an artifact.
    
    Requires admin privileges.
    """
    signature = await manager.sign_artifact(
        artifact_id=request.artifact_id,
        private_key_pem=request.private_key_pem,
        algorithm=request.algorithm,
        signer_id=request.signer_id,
        expires_at=request.expires_at
    )
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {request.artifact_id} not found"
        )
    
    return SignatureResponse(
        signature_id=signature.signature_id,
        algorithm=signature.algorithm,
        signed_by=signature.signed_by,
        signed_at=signature.signed_at,
        expires_at=signature.expires_at,
        content_hash=signature.content_hash,
        verification_status=signature.verification_status,
        verified_at=signature.verified_at
    )


@router.post("/verify", response_model=VerificationResponse)
async def verify_artifact(
    request: VerificationRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Verify an artifact against a policy.
    
    Requires admin privileges.
    """
    result = await manager.verify_artifact(
        artifact_id=request.artifact_id,
        policy_id=request.policy_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact or policy not found"
        )
    
    return VerificationResponse(
        result_id=result.result_id,
        artifact_id=result.artifact_id,
        policy_id=result.policy_id,
        status=result.status,
        verified_at=result.verified_at,
        signature_valid=result.signature_valid,
        signature_message=result.signature_message,
        provenance_valid=result.provenance_valid,
        provenance_message=result.provenance_message,
        policy_compliant=result.policy_compliant,
        policy_violations=result.policy_violations,
        errors=result.errors
    )


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    request: PolicyCreateRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a verification policy.
    
    Requires admin privileges.
    """
    policy = await manager.create_policy(
        policy_id=request.policy_id,
        name=request.name,
        description=request.description,
        require_signature=request.require_signature,
        require_provenance=request.require_provenance,
        minimum_provenance_level=request.minimum_provenance_level,
        enforcement_mode=request.enforcement_mode
    )
    
    return PolicyResponse(
        policy_id=policy.policy_id,
        name=policy.name,
        description=policy.description,
        require_signature=policy.require_signature,
        require_provenance=policy.require_provenance,
        minimum_provenance_level=policy.minimum_provenance_level,
        enforcement_mode=policy.enforcement_mode
    )


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """List all verification policies."""
    policies = await manager.list_policies()
    
    return [
        PolicyResponse(
            policy_id=p.policy_id,
            name=p.name,
            description=p.description,
            require_signature=p.require_signature,
            require_provenance=p.require_provenance,
            minimum_provenance_level=p.minimum_provenance_level,
            enforcement_mode=p.enforcement_mode
        ) for p in policies
    ]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """Get verification policy by ID."""
    policy = await manager.get_policy(policy_id)
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found"
        )
    
    return PolicyResponse(
        policy_id=policy.policy_id,
        name=p.name,
        description=p.description,
        require_signature=p.require_signature,
        require_provenance=p.require_provenance,
        minimum_provenance_level=p.minimum_provenance_level,
        enforcement_mode=p.enforcement_mode
    )


@router.post("/deployments", status_code=status.HTTP_201_CREATED)
async def record_deployment(
    request: DeploymentRecordRequest,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(require_admin)
):
    """
    Record an artifact deployment.
    
    Requires admin privileges.
    """
    result = await manager.record_deployment(
        artifact_id=request.artifact_id,
        deployment_location=request.deployment_location,
        deployed_by=user.get("email", "unknown"),
        deployment_details=request.deployment_details
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {request.artifact_id} not found"
        )
    
    return {
        "artifact_id": request.artifact_id,
        "deployment_location": request.deployment_location,
        "recorded_at": datetime.utcnow().isoformat(),
        "recorded_by": user.get("email", "unknown")
    }


@router.get("/artifacts/{artifact_id}/chain-of-custody", response_model=ChainOfCustodyResponse)
async def get_chain_of_custody(
    artifact_id: str,
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """Get chain of custody for an artifact."""
    chain = await manager.get_chain_of_custody(artifact_id)
    
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chain of custody for artifact {artifact_id} not found"
        )
    
    return ChainOfCustodyResponse(
        chain_id=chain.chain_id,
        artifact_id=chain.artifact_id,
        events=chain.events,
        current_location=chain.current_location,
        current_status=chain.current_status
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager),
    user: Dict = Depends(get_current_user)
):
    """Get artifact provenance statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        artifacts=stats["artifacts"],
        policies=stats["policies"],
        verifications=stats["verifications"]
    )


@router.get("/health")
async def health_check(
    manager: ArtifactProvenanceManager = Depends(get_provenance_manager)
):
    """Health check endpoint for artifact provenance service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "total_artifacts": len(manager.artifacts),
        "total_policies": len(manager.policies)
    }
