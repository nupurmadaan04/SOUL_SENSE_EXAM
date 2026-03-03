"""
Users Router (Async Version)

Provides authenticated CRUD endpoints for user management.
"""

from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, UploadFile, File, Request
from pathlib import Path
from ..utils.limiter import limiter
from ..utils.timestamps import normalize_utc_iso

from ..schemas import (
    UserResponse,
    UserUpdate,
    UserDetail,
    CompleteProfileResponse,
    AuditLogResponse,
    OnboardingData,
    OnboardingCompleteResponse,
    AvatarUploadResponse
)
from ..services.audit_service import AuditService
from ..services.user_service import UserService
from ..services.profile_service import ProfileService
from ..routers.auth import get_current_user, require_admin
from ..services.db_service import get_db
from ..models import User
from app.core import NotFoundError, ValidationError, InternalServerError
import aiofiles


router = APIRouter(tags=["Users"])


async def get_user_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get UserService with async database session."""
    """Dependency to get UserService with database session."""
    return UserService(db)


async def get_profile_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get ProfileService with async database session."""
    """Dependency to get ProfileService with database session."""
    return ProfileService(db)


# ============================================================================
# User CRUD Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse, summary="Get Current User")
@limiter.limit("100/minute")
async def get_current_user_info(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get information about the currently authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=normalize_utc_iso(current_user.created_at, fallback_now=True),
        last_login=current_user.last_login
    )


@router.get("/me/detail", response_model=UserDetail, summary="Get Current User Details")
@limiter.limit("100/minute")
async def get_current_user_details(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get detailed information about the currently authenticated user.
    """
    detail = await user_service.get_user_detail(current_user.id)
    return UserDetail(**detail)


@router.get("/me/complete", response_model=CompleteProfileResponse, summary="Get Complete Profile")
@limiter.limit("100/minute")
async def get_complete_user_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get complete user profile including all sub-profiles.
    
    **Authentication Required**
    """
    return await profile_service.get_complete_profile(current_user.id)


@router.put("/me", response_model=UserResponse, summary="Update Current User")
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Update the currently authenticated user's information.
    
    **Authentication Required**
    """
    updated_user = await user_service.update_user(
        user_id=current_user.id,
        username=user_update.username,
        password=user_update.password
    )
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        created_at=normalize_utc_iso(updated_user.created_at, fallback_now=True),
        last_login=updated_user.last_login
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Current User")
async def delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Delete the currently authenticated user account.
    
    **Authentication Required**
    """
    await user_service.delete_user(current_user.id)
    return None


@router.get("/me/audit-logs", response_model=List[AuditLogResponse], summary="Get Current User Audit Logs")
async def get_my_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20
):
    """
    Get audit logs for the currently authenticated user.
    """
    if per_page > 50:
        per_page = 50
        
    return await AuditService.get_user_logs(current_user.id, page=page, per_page=per_page, db_session=db)


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/", response_model=List[UserResponse], summary="List All Users")
async def list_users(
    admin_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: int = 0,
    limit: int = 100
):
    """
    List all users with pagination.
    
    **Authentication Required**
    List all users with pagination (Admin only).
    """
    if limit > 100:
        limit = 100
        
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            created_at=normalize_utc_iso(user.created_at, fallback_now=True),
            last_login=user.last_login
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse, summary="Get User by ID")
async def get_user(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get a specific user by ID.
    
    **Authentication Required**
    Get a specific user by ID (Admin only).
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise NotFoundError(resource="User", resource_id=str(user_id))
    
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=normalize_utc_iso(user.created_at, fallback_now=True),
        last_login=user.last_login
    )


@router.get("/{user_id}/detail", response_model=UserDetail, summary="Get User Details by ID")
async def get_user_detail(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get detailed information about a specific user (Admin only).
    """
    detail = await user_service.get_user_detail(user_id)
    return UserDetail(**detail)


# ============================================================================
# Onboarding Endpoints
# ============================================================================

@router.post("/me/onboarding/complete", response_model=OnboardingCompleteResponse, summary="Complete User Onboarding")
async def complete_onboarding(
    onboarding_data: OnboardingData,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Complete the onboarding wizard and save all profile data.
    """
    personal_profile_data = {
        "sleep_hours": onboarding_data.sleep_hours,
        "exercise_freq": onboarding_data.exercise_freq,
        "dietary_patterns": onboarding_data.dietary_patterns,
        "has_therapist": onboarding_data.has_therapist,
        "support_network_size": onboarding_data.support_network_size,
        "primary_support_type": onboarding_data.primary_support_type,
    }
    personal_profile_data = {k: v for k, v in personal_profile_data.items() if v is not None}
    if personal_profile_data:
        await profile_service.update_personal_profile(current_user.id, personal_profile_data)
    
    strengths_data = {}
    if onboarding_data.primary_goal is not None:
        strengths_data["primary_goal"] = onboarding_data.primary_goal
    if onboarding_data.focus_areas is not None:
        strengths_data["focus_areas"] = onboarding_data.focus_areas
    if strengths_data:
        await profile_service.update_user_strengths(current_user.id, strengths_data)
    
    **Authentication Required**
    """
    detail = await user_service.get_user_detail(user_id)
    return UserDetail(**detail)
    current_user.onboarding_completed = True
    await db.commit()
    
    return OnboardingCompleteResponse(
        message="Onboarding completed successfully",
        onboarding_completed=True
    )


@router.get("/me/onboarding/status", response_model=Dict[str, bool], summary="Get Onboarding Status")
async def get_onboarding_status(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Check if the current user has completed onboarding.
    """
    return {
        "onboarding_completed": current_user.onboarding_completed or False
    }


@router.post("/me/avatar", response_model=AvatarUploadResponse, summary="Upload User Avatar")
async def upload_user_avatar(
    file: Annotated[UploadFile, File(description="Avatar image file (PNG, JPG, JPEG) - max 5MB")],
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Upload an avatar image for the current user.
    """
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise ValidationError(
            message="Invalid file type. Only PNG, JPG, and JPEG files are allowed.",
            details=[{"field": "file", "error": "Invalid file type"}]
        )

    content = await file.read()
    file_size = len(content)

    if file_size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError(
            message="File too large. Maximum size is 5MB.",
            details=[{"field": "file", "error": "File size exceeds 5MB limit"}]
        )

    avatars_dir = Path("app_data/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)

    file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    avatar_filename = f"{current_user.username}_avatar.{file_extension}"
    avatar_path = avatars_dir / avatar_filename

    try:
        async with aiofiles.open(avatar_path, "wb") as buffer:
            await buffer.write(content)
    except Exception as e:
        raise InternalServerError(
            message="Failed to save avatar file",
            details=[{"error": str(e)}]
        )

    try:
        from ..models import PersonalProfile
        from sqlalchemy import select
        
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == current_user.id)
        result = await db.execute(stmt)
        personal_profile = result.scalar_one_or_none()

        if not personal_profile:
            personal_profile = PersonalProfile(user_id=current_user.id)
            db.add(personal_profile)

        personal_profile.avatar_path = str(avatar_filename)
        await db.commit()

    except Exception as e:
        if avatar_path.exists():
            avatar_path.unlink()
        raise InternalServerError(
            message="Failed to update profile",
            details=[{"error": str(e)}]
        )

    return AvatarUploadResponse(
        message="Avatar uploaded successfully",
        avatar_path=str(avatar_filename)
    )
