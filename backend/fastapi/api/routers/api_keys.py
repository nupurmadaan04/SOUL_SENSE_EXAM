# api_keys.py
"""
API Key Management Routes (#1264)

Provides endpoints for:
- Creating API keys with specific scopes
- Listing user's API keys
- Revoking API keys
- Updating API key scopes
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..services.api_key_service import ApiKeyService
from ..services.db_router import get_db
from ..middleware.rbac_middleware import oauth2_scheme
from ..models import ApiKeyScope
from ..utils.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Pydantic models for API requests/responses
class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for the API key", max_length=100)
    scopes: List[str] = Field(..., description="List of scopes to grant", min_items=1)
    expires_in_days: Optional[int] = Field(None, description="Optional expiration in days from now", ge=1, le=365)


class CreateApiKeyResponse(BaseModel):
    api_key: str = Field(..., description="The generated API key (only shown once)")
    key_info: dict = Field(..., description="Information about the created key")


class ApiKeyInfo(BaseModel):
    id: int
    name: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UpdateScopesRequest(BaseModel):
    scopes: List[str] = Field(..., description="New list of scopes", min_items=1)


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """Extract user ID from JWT token."""
    from ..config import get_settings_instance
    from jose import JWTError, jwt

    settings = get_settings_instance()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("uid") or payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("", response_model=CreateApiKeyResponse)
@limiter.limit("10/minute")
async def create_api_key(
    request: CreateApiKeyRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key with specified scopes.

    The API key will be returned only once - store it securely.
    """
    # Validate scopes
    valid_scopes = {scope.value for scope in ApiKeyScope}
    invalid_scopes = [scope for scope in request.scopes if scope not in valid_scopes]
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {invalid_scopes}. Valid scopes: {sorted(valid_scopes)}"
        )

    # Calculate expiration date
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create the API key
    api_key_service = ApiKeyService(db)
    try:
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=user_id,
            name=request.name,
            scopes=request.scopes,
            expires_at=expires_at
        )

        return CreateApiKeyResponse(
            api_key=plain_key,
            key_info=key_record.to_dict()
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[ApiKeyInfo])
@limiter.limit("30/minute")
async def list_api_keys(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys for the current user."""
    api_key_service = ApiKeyService(db)
    keys = await api_key_service.get_user_api_keys(user_id)

    return [ApiKeyInfo(**key.to_dict()) for key in keys]


@router.delete("/{key_id}")
@limiter.limit("10/minute")
async def revoke_api_key(
    key_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an API key."""
    api_key_service = ApiKeyService(db)
    success = await api_key_service.revoke_api_key(key_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or not owned by you"
        )

    return {"message": "API key revoked successfully"}


@router.put("/{key_id}/scopes", response_model=ApiKeyInfo)
@limiter.limit("10/minute")
async def update_api_key_scopes(
    key_id: int,
    request: UpdateScopesRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update the scopes of an API key."""
    # Validate scopes
    valid_scopes = {scope.value for scope in ApiKeyScope}
    invalid_scopes = [scope for scope in request.scopes if scope not in valid_scopes]
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {invalid_scopes}. Valid scopes: {sorted(valid_scopes)}"
        )

    api_key_service = ApiKeyService(db)
    try:
        success = await api_key_service.update_api_key_scopes(
            key_id=key_id,
            user_id=user_id,
            new_scopes=request.scopes
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or not owned by you"
            )

        # Get updated key info
        keys = await api_key_service.get_user_api_keys(user_id)
        updated_key = next((k for k in keys if k.id == key_id), None)

        if not updated_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated key"
            )

        return ApiKeyInfo(**updated_key.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/scopes")
async def list_available_scopes():
    """List all available API key scopes."""
    scopes = {scope.value: scope.value for scope in ApiKeyScope}

    # Group scopes by category
    grouped = {
        "general": ["read", "write", "admin"],
        "resource_specific": {
            "users": ["users:read", "users:write"],
            "payments": ["payments:read", "payments:write"],
            "analytics": ["analytics:read", "analytics:write"],
            "exams": ["exams:read", "exams:write"],
            "journal": ["journal:read", "journal:write"],
            "surveys": ["surveys:read", "surveys:write"],
            "notifications": ["notifications:read", "notifications:write"],
            "settings": ["settings:read", "settings:write"],
        }
    }

    return {
        "available_scopes": list(scopes.keys()),
        "grouped_scopes": grouped,
        "descriptions": {
            "read": "Read access to general resources",
            "write": "Write access to general resources",
            "admin": "Full administrative access",
            "users:read": "Read access to user management",
            "users:write": "Write access to user management",
            "payments:read": "Read access to payment data",
            "payments:write": "Write access to payment data",
            "analytics:read": "Read access to analytics data",
            "analytics:write": "Write access to analytics data",
            "exams:read": "Read access to exam data",
            "exams:write": "Write access to exam data",
            "journal:read": "Read access to journal entries",
            "journal:write": "Write access to journal entries",
            "surveys:read": "Read access to survey data",
            "surveys:write": "Write access to survey data",
            "notifications:read": "Read access to notifications",
            "notifications:write": "Write access to notifications",
            "settings:read": "Read access to settings",
            "settings:write": "Write access to settings",
        }
    }


@router.get("/stats")
@limiter.limit("30/minute")
async def get_api_key_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about the user's API keys."""
    api_key_service = ApiKeyService(db)
    stats = await api_key_service.get_api_key_stats(user_id)
    return stats