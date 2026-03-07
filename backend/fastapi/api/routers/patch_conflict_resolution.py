"""
Idempotent PATCH Conflict Resolution API Routes

Provides REST API endpoints for idempotent PATCH operations
with conflict detection and resolution.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.patch_conflict_resolution import (
    ConflictStrategy, PatchStatus, ChangeType,
    FieldChange, ResourceVersion, PatchOperation, PatchRequest, PatchResult,
    PatchHistory, IdempotentPatchManager, get_patch_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/patch-operations", tags=["patch-operations"])


# Pydantic Models

class PatchOperationRequest(BaseModel):
    """Request for a patch operation."""
    op: str  # add, remove, replace
    path: str
    value: Any = None


class ResourceCreateRequest(BaseModel):
    """Request to create a resource."""
    resource_id: str
    resource_type: str
    data: Dict[str, Any]


class ResourceResponse(BaseModel):
    """Response model for resource."""
    resource_id: str
    resource_type: str
    data: Dict[str, Any]
    etag: str
    version: int
    last_modified_at: datetime


class PatchRequestModel(BaseModel):
    """Request model for PATCH operation."""
    operations: List[PatchOperationRequest]
    conflict_strategy: ConflictStrategy = ConflictStrategy.REJECT
    idempotency_key: str = ""


class PatchResultResponse(BaseModel):
    """Response model for PATCH result."""
    request_id: str
    status: PatchStatus
    new_etag: str
    new_version: int
    applied_changes: List[Dict[str, Any]]
    conflicted_changes: List[Dict[str, Any]]
    error_message: str
    error_code: str
    processing_time_ms: int


class PatchHistoryResponse(BaseModel):
    """Response model for patch history."""
    history_id: str
    operations: List[Dict[str, Any]]
    changes: List[Dict[str, Any]]
    previous_etag: str
    new_etag: str
    version_number: int
    applied_at: datetime
    applied_by: str


class ConflictInfoResponse(BaseModel):
    """Response model for conflict information."""
    field_path: str
    base_value: Any
    client_value: Any
    server_value: Any
    resolved: bool
    resolved_value: Any


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    resources: Dict[str, Any]
    patches: Dict[str, Any]


# Helper Functions

def _patch_operation_from_request(req: PatchOperationRequest) -> PatchOperation:
    """Convert PatchOperationRequest to PatchOperation."""
    return PatchOperation(
        op=req.op,
        path=req.path,
        value=req.value
    )


def _result_to_response(result: PatchResult) -> PatchResultResponse:
    """Convert PatchResult to response model."""
    return PatchResultResponse(
        request_id=result.request_id,
        status=result.status,
        new_etag=result.new_etag,
        new_version=result.new_version,
        applied_changes=[
            {
                "field_path": c.field_path,
                "change_type": c.change_type.value,
                "old_value": c.old_value,
                "new_value": c.new_value
            } for c in result.applied_changes
        ],
        conflicted_changes=[
            {
                "field_path": c.field_path,
                "change_type": c.change_type.value,
                "old_value": c.old_value,
                "new_value": c.new_value
            } for c in result.conflicted_changes
        ],
        error_message=result.error_message,
        error_code=result.error_code,
        processing_time_ms=result.processing_time_ms
    )


def _history_to_response(history: PatchHistory) -> PatchHistoryResponse:
    """Convert PatchHistory to response model."""
    return PatchHistoryResponse(
        history_id=history.history_id,
        operations=[
            {"op": op.op, "path": op.path, "value": op.value}
            for op in history.operations
        ],
        changes=[
            {
                "field_path": c.field_path,
                "change_type": c.change_type.value,
                "old_value": c.old_value,
                "new_value": c.new_value
            } for c in history.changes
        ],
        previous_etag=history.previous_etag,
        new_etag=history.new_etag,
        version_number=history.version_number,
        applied_at=history.applied_at,
        applied_by=history.applied_by
    )


# API Routes

@router.post("/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    request: ResourceCreateRequest,
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a new versioned resource.
    
    Requires admin privileges.
    """
    version = await manager.create_resource(
        resource_id=request.resource_id,
        resource_type=request.resource_type,
        data=request.data,
        created_by=user.get("email", "unknown")
    )
    
    return ResourceResponse(
        resource_id=version.resource_id,
        resource_type=version.resource_type,
        data=request.data,
        etag=version.etag,
        version=version.version_number,
        last_modified_at=version.last_modified_at
    )


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """Get resource by ID with version info."""
    data = await manager.get_resource(resource_id)
    version = await manager.get_resource_version(resource_id)
    
    if not data or not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found"
        )
    
    return ResourceResponse(
        resource_id=resource_id,
        resource_type=version.resource_type,
        data=data,
        etag=version.etag,
        version=version.version_number,
        last_modified_at=version.last_modified_at
    )


@router.patch("/resources/{resource_id}", response_model=PatchResultResponse)
async def apply_patch(
    resource_id: str,
    request: PatchRequestModel,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """
    Apply a PATCH operation to a resource.
    
    Supports optimistic concurrency control via If-Match header.
    Use Idempotency-Key header for idempotent requests.
    """
    version = await manager.get_resource_version(resource_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found"
        )
    
    # Build patch request
    patch_request = PatchRequest(
        request_id=f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{resource_id}",
        resource_id=resource_id,
        resource_type=version.resource_type,
        operations=[_patch_operation_from_request(op) for op in request.operations],
        expected_etag=if_match or "",
        idempotency_key=idempotency_key or "",
        client_id=user.get("email", "unknown"),
        conflict_strategy=request.conflict_strategy
    )
    
    result = await manager.apply_patch(patch_request)
    
    if result.status == PatchStatus.CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": result.error_message,
                "current_etag": result.new_etag,
                "current_version": result.new_version
            }
        )
    
    if result.status == PatchStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message
        )
    
    return _result_to_response(result)


@router.get("/resources/{resource_id}/history", response_model=List[PatchHistoryResponse])
async def get_patch_history(
    resource_id: str,
    limit: int = Query(50, ge=1, le=100),
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """Get patch history for a resource."""
    history = await manager.get_patch_history(resource_id, limit)
    return [_history_to_response(h) for h in history]


@router.get("/resources/{resource_id}/version", response_model=Dict[str, Any])
async def get_version_info(
    resource_id: str,
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """Get version information for a resource."""
    version = await manager.get_resource_version(resource_id)
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found"
        )
    
    return {
        "resource_id": version.resource_id,
        "resource_type": version.resource_type,
        "etag": version.etag,
        "version_number": version.version_number,
        "last_modified_at": version.last_modified_at,
        "last_modified_by": version.last_modified_by
    }


@router.post("/resources/{resource_id}/compare")
async def compare_versions(
    resource_id: str,
    base_version: int = Query(..., description="Base version number"),
    target_version: int = Query(..., description="Target version number"),
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """Compare two versions of a resource."""
    history = await manager.get_patch_history(resource_id)
    
    base_data = None
    target_data = None
    
    # Find the data at each version
    for h in history:
        if h.version_number == base_version:
            base_data = h
        if h.version_number == target_version:
            target_data = h
    
    if not base_data or not target_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both versions not found in history"
        )
    
    return {
        "resource_id": resource_id,
        "base_version": base_version,
        "target_version": target_version,
        "changes_between_versions": len([
            h for h in history
            if base_version < h.version_number <= target_version
        ])
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: IdempotentPatchManager = Depends(get_patch_manager),
    user: Dict = Depends(get_current_user)
):
    """Get PATCH operation statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        resources=stats["resources"],
        patches=stats["patches"]
    )


@router.get("/health")
async def health_check(
    manager: IdempotentPatchManager = Depends(get_patch_manager)
):
    """Health check endpoint for PATCH operations service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "tracked_resources": len(manager.resources),
        "patch_history_entries": sum(len(h) for h in manager.patch_history.values())
    }
