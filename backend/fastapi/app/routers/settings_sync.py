"""
Settings Synchronization Router

REST API endpoints for syncing user preferences and settings across clients.
Implements Issue #396: Create Settings Synchronization API

Endpoints:
    GET    /api/sync/settings       - Get all settings for authenticated user
    GET    /api/sync/settings/{key} - Get single setting by key
    PUT    /api/sync/settings/{key} - Upsert setting (with optional conflict detection)
    DELETE /api/sync/settings/{key} - Delete a setting
    POST   /api/sync/settings/batch - Batch upsert settings
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.schemas import (
    SyncSettingCreate,
    SyncSettingUpdate,
    SyncSettingResponse,
    SyncSettingBatchRequest,
    SyncSettingBatchResponse,
    SyncSettingConflictResponse
)
from ..services.settings_sync_service import SettingsSyncService
from ..routers.auth import get_current_user
from ..services.db_service import get_db
from app.models import User

router = APIRouter(prefix="/settings", tags=["Settings Sync"])


def get_settings_sync_service():
    """Dependency to get SettingsSyncService with database session."""
    db = next(get_db())
    try:
        yield SettingsSyncService(db)
    finally:
        db.close()


# ============================================================================
# Settings Sync Endpoints
# ============================================================================

@router.get("/", response_model=List[SyncSettingResponse], summary="Get All Settings")
async def get_all_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """
    Get all sync settings for the authenticated user.
    
    Returns a list of all key-value settings stored for the user.
    
    **Authentication Required**
    """
    settings = service.get_all_settings(current_user.id)
    return [
        SyncSettingResponse(
            key=s.key,
            value=s.value,
            version=s.version,
            updated_at=s.updated_at
        )
        for s in settings
    ]


@router.get("/{key}", response_model=SyncSettingResponse, summary="Get Setting by Key")
async def get_setting(
    key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """
    Get a single setting by key.
    
    **Path Parameters:**
    - key: The setting key to retrieve
    
    **Authentication Required**
    """
    setting = service.get_setting(current_user.id, key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    return SyncSettingResponse(
        key=setting.key,
        value=setting.value,
        version=setting.version,
        updated_at=setting.updated_at
    )


@router.put("/{key}", response_model=SyncSettingResponse, summary="Upsert Setting")
async def upsert_setting(
    key: str,
    update: SyncSettingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """
    Create or update a setting by key.
    
    **Path Parameters:**
    - key: The setting key
    
    **Request Body:**
    - value: The setting value (any JSON-serializable value)
    - expected_version: Optional. If provided, update only succeeds if current 
      version matches. Returns 409 Conflict if versions don't match.
    
    **Conflict Detection:**
    Use the `expected_version` field for optimistic locking. When provided,
    the server will only update if the current version matches the expected version.
    This prevents concurrent updates from overwriting each other.
    
    **Authentication Required**
    """
    setting, success, error = service.upsert_setting(
        user_id=current_user.id,
        key=key,
        value=update.value,
        expected_version=update.expected_version
    )
    
    if not success:
        # Return 409 Conflict with current value
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": error,
                "key": key,
                "current_version": setting.version,
                "current_value": setting.value
            }
        )
    
    return SyncSettingResponse(
        key=setting.key,
        value=setting.value,
        version=setting.version,
        updated_at=setting.updated_at
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Setting")
async def delete_setting(
    key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """
    Delete a setting by key.
    
    **Path Parameters:**
    - key: The setting key to delete
    
    **Authentication Required**
    """
    deleted = service.delete_setting(current_user.id, key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    return None


@router.post("/batch", response_model=SyncSettingBatchResponse, summary="Batch Upsert Settings")
async def batch_upsert_settings(
    batch: SyncSettingBatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """
    Batch create/update multiple settings.
    
    **Request Body:**
    - settings: List of settings with 'key' and 'value' fields
    
    **Behavior:**
    - Processes all settings, continuing even if some have conflicts
    - Returns successfully updated settings and list of conflicting keys
    - Each setting is version-incremented independently
    
    **Authentication Required**
    """
    settings_data = [
        {"key": s.key, "value": s.value}
        for s in batch.settings
    ]
    
    successful, conflicts = service.batch_upsert_settings(
        user_id=current_user.id,
        settings=settings_data
    )
    
    return SyncSettingBatchResponse(
        settings=[
            SyncSettingResponse(
                key=s.key,
                value=s.value,
                version=s.version,
                updated_at=s.updated_at
            )
            for s in successful
        ],
        conflicts=conflicts
    )
