"""
Users Router

Provides authenticated CRUD endpoints for user management.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.schemas import (
    UserResponse,
    UserUpdate,
    UserDetail,
    CompleteProfileResponse
)
from ..services.user_service import UserService
from ..services.profile_service import ProfileService
from ..routers.auth import get_current_user
from ..services.db_service import get_db
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service():
    """Dependency to get UserService with database session."""
    db = next(get_db())
    try:
        yield UserService(db)
    finally:
        db.close()


def get_profile_service():
    """Dependency to get ProfileService with database session."""
    db = next(get_db())
    try:
        yield ProfileService(db)
    finally:
        db.close()


# ============================================================================
# User CRUD Endpoints
# ============================================================================

@router.get("/me", response_model=UserResponse, summary="Get Current User")
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get information about the currently authenticated user.
    
    **Authentication Required**
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.get("/me/detail", response_model=UserDetail, summary="Get Current User Details")
async def get_current_user_details(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get detailed information about the currently authenticated user,
    including profile completion status and assessment count.
    
    **Authentication Required**
    """
    detail = user_service.get_user_detail(current_user.id)
    return UserDetail(**detail)


@router.get("/me/complete", response_model=CompleteProfileResponse, summary="Get Complete Profile")
async def get_complete_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get complete user profile including all sub-profiles:
    - User settings
    - Medical profile
    - Personal profile
    - Strengths
    - Emotional patterns
    
    **Authentication Required**
    """
    return profile_service.get_complete_profile(current_user.id)


@router.put("/me", response_model=UserResponse, summary="Update Current User")
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Update the currently authenticated user's information.
    
    **Updatable Fields:**
    - username: Must be unique and 3-50 characters
    - password: Minimum 8 characters (will be hashed)
    
    **Authentication Required**
    """
    updated_user = user_service.update_user(
        user_id=current_user.id,
        username=user_update.username,
        password=user_update.password
    )
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Current User")
async def delete_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Delete the currently authenticated user account.
    
    **Warning:** This action is irreversible and will delete:
    - User account
    - All profiles (settings, medical, personal, strengths, emotional)
    - All assessment scores and responses
    
    **Authentication Required**
    """
    user_service.delete_user(current_user.id)
    return None


# ============================================================================
# Admin Endpoints (Future: Add admin role check)
# ============================================================================

@router.get("/", response_model=List[UserResponse], summary="List All Users")
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: int = 0,
    limit: int = 100
):
    """
    List all users with pagination.
    
    **Query Parameters:**
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100, max: 100)
    
    **Note:** Currently available to all authenticated users.
    Future versions will require admin role.
    
    **Authentication Required**
    """
    if limit > 100:
        limit = 100
        
    users = user_service.get_all_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse, summary="Get User by ID")
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get a specific user by ID.
    
    **Note:** Currently available to all authenticated users.
    Future versions will require admin role or ownership.
    
    **Authentication Required**
    """
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.get("/{user_id}/detail", response_model=UserDetail, summary="Get User Details by ID")
async def get_user_detail(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Get detailed information about a specific user.
    
    **Note:** Currently available to all authenticated users.
    Future versions will require admin role or ownership.
    
    **Authentication Required**
    """
    detail = user_service.get_user_detail(user_id)
    return UserDetail(**detail)
