"""
Settings Synchronization Router
Migrated to Async SQLAlchemy 2.0.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, status

from ..schemas import (
    SyncSettingUpdate,
    SyncSettingResponse,
    SyncSettingBatchRequest,
    SyncSettingBatchResponse
)
from ..services.settings_sync_service import SettingsSyncService
from ..routers.auth import get_current_user
from ..services.db_service import get_db
from ..models import User
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from app.core import NotFoundError, ConflictError
except ImportError:
    from app.core import NotFoundError, ConflictError

router = APIRouter(tags=["Settings Sync"])


async def get_settings_sync_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get SettingsSyncService with async database session."""
    return SettingsSyncService(db)


# ============================================================================
# Settings Sync Endpoints
# ============================================================================

@router.get("/", response_model=List[SyncSettingResponse], summary="Get All Settings")
async def get_all_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """Get all sync settings for the authenticated user."""
    settings = await service.get_all_settings(current_user.id)
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
    """Get a single setting by key."""
    setting = await service.get_setting(current_user.id, key)
    if not setting:
        raise NotFoundError(resource="Setting", resource_id=key)
    
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
    """Create or update a setting by key."""
    setting, success, error = await service.upsert_setting(
        user_id=current_user.id,
        key=key,
        value=update.value,
        expected_version=update.expected_version
    )
    
    if not success:
        raise ConflictError(
            message=error or "Setting version conflict",
            code="SETTING_VERSION_CONFLICT",
            details=[{
                "key": key,
                "current_version": setting.version,
                "current_value": setting.value
            }]
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
    """Delete a setting by key."""
    deleted = await service.delete_setting(current_user.id, key)
    if not deleted:
        raise NotFoundError(resource="Setting", resource_id=key)
    return None


@router.post("/batch", response_model=SyncSettingBatchResponse, summary="Batch Upsert Settings")
async def batch_upsert_settings(
    batch: SyncSettingBatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SettingsSyncService, Depends(get_settings_sync_service)]
):
    """Batch create/update multiple settings."""
    settings_data = [
        {"key": s.key, "value": s.value}
        for s in batch.settings
    ]
    
    successful, conflicts = await service.batch_upsert_settings(
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
