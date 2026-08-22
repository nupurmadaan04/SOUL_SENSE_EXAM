"""
Users Router (Async Version)
Provides authenticated CRUD endpoints for user management and onboarding.
"""

from typing import Annotated, List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import APIRouter, Depends, status, UploadFile, File, Request, HTTPException
from pathlib import Path
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
from ..models import User, PersonalProfile
import aiofiles

router = APIRouter(tags=["Users"])


async def get_user_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get UserService with database session."""
    return UserService(db)


async def get_profile_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get ProfileService with database session."""
    return ProfileService(db)


# ============================================================================
# User CRUD Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse, summary="Get Current User")
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get information about the currently authenticated user."""
    from sqlalchemy import select
    stmt = select(PersonalProfile).filter(PersonalProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=profile.email if profile else None,
        created_at=normalize_utc_iso(current_user.created_at, fallback_now=True),
        onboarding_completed=getattr(current_user, "onboarding_completed", False),
        is_admin=getattr(current_user, "is_admin", False)
    )


@router.get("/me/detail", response_model=UserDetail, summary="Get Current User Details")
async def get_current_user_details(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Get detailed information about the currently authenticated user."""
    detail = await user_service.get_user_detail(current_user.id)
    return UserDetail(**detail)


@router.get("/me/complete", response_model=CompleteProfileResponse, summary="Get Complete Profile")
async def get_complete_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """Get complete user profile including all sub-profiles."""
    return await profile_service.get_complete_profile(current_user.id)


@router.put("/me", response_model=UserResponse, summary="Update Current User")
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Update the currently authenticated user's information."""
    updated_user = await user_service.update_user(
        user_id=current_user.id,
        username=user_update.username,
        password=user_update.password
    )
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        created_at=normalize_utc_iso(updated_user.created_at, fallback_now=True),
        onboarding_completed=getattr(updated_user, "onboarding_completed", False),
        is_admin=getattr(updated_user, "is_admin", False)
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Current User")
async def delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Delete the currently authenticated user account."""
    await user_service.delete_user(current_user.id)
    return None


@router.get("/me/audit-logs", response_model=List[AuditLogResponse], summary="Get Current User Audit Logs")
async def get_my_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20
):
    """Get audit logs for the currently authenticated user."""
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
    """List all users with pagination (Admin only)."""
    if limit > 100:
        limit = 100
        
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            created_at=normalize_utc_iso(user.created_at, fallback_now=True),
            onboarding_completed=getattr(user, "onboarding_completed", False),
            is_admin=getattr(user, "is_admin", False)
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse, summary="Get User by ID")
async def get_user(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Get a specific user by ID (Admin only)."""
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=normalize_utc_iso(user.created_at, fallback_now=True),
        onboarding_completed=getattr(user, "onboarding_completed", False),
        is_admin=getattr(user, "is_admin", False)
    )


@router.get("/{user_id}/detail", response_model=UserDetail, summary="Get User Details by ID")
async def get_user_detail(
    user_id: int,
    admin_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Get detailed information about a specific user (Admin only)."""
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
        try:
            await profile_service.update_personal_profile(current_user.id, personal_profile_data)
        except Exception:
            pass
    
    strengths_data = {}
    if onboarding_data.primary_goal is not None:
        strengths_data["primary_goal"] = onboarding_data.primary_goal
    if onboarding_data.focus_areas is not None:
        strengths_data["focus_areas"] = onboarding_data.focus_areas
    if strengths_data:
        try:
            await profile_service.update_user_strengths(current_user.id, strengths_data)
        except Exception:
            pass
    
    await db.execute(
        update(User).where(User.id == current_user.id).values(onboarding_completed=True)
    )
    await db.commit()
    
    return OnboardingCompleteResponse(
        message="Onboarding completed successfully",
        onboarding_completed=True
    )


@router.get("/me/onboarding/status", response_model=Dict[str, bool], summary="Get Onboarding Status")
async def get_onboarding_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Check if the current user has completed onboarding."""
    stmt = select(User.onboarding_completed).where(User.id == current_user.id)
    res = await db.execute(stmt)
    is_done = res.scalar()
    return {
        "onboarding_completed": bool(is_done)
    }


@router.post("/me/avatar", response_model=AvatarUploadResponse, summary="Upload User Avatar")
async def upload_user_avatar(
    file: Annotated[UploadFile, File(description="Avatar image file (PNG, JPG, JPEG) - max 5MB")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Upload an avatar image for the current user."""
    allowed_types = ["image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PNG, JPG, and JPEG files are allowed."
        )

    content = await file.read()
    file_size = len(content)

    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save avatar file: {e}")

    try:
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update profile: {e}")

    return AvatarUploadResponse(
        message="Avatar uploaded successfully",
        avatar_path=str(avatar_filename)
    )
