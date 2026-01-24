"""
Profiles Router

Provides authenticated CRUD endpoints for all user profile types:
- User Settings
- Medical Profile
- Personal Profile  
- User Strengths
- Emotional Patterns
"""

from typing import Annotated
from fastapi import APIRouter, Depends, status

from ..models.schemas import (
    # User Settings
    UserSettingsCreate,
    UserSettingsUpdate,
    UserSettingsResponse,
    # Medical Profile
    MedicalProfileCreate,
    MedicalProfileUpdate,
    MedicalProfileResponse,
    # Personal Profile
    PersonalProfileCreate,
    PersonalProfileUpdate,
    PersonalProfileResponse,
    # User Strengths
    UserStrengthsCreate,
    UserStrengthsUpdate,
    UserStrengthsResponse,
    # Emotional Patterns
    UserEmotionalPatternsCreate,
    UserEmotionalPatternsUpdate,
    UserEmotionalPatternsResponse,
)
from ..services.profile_service import ProfileService
from ..routers.auth import get_current_user
from ..services.db_service import get_db
from app.models import User

router = APIRouter(tags=["Profiles"])


def get_profile_service():
    """Dependency to get ProfileService with database session."""
    db = next(get_db())
    try:
        yield ProfileService(db)
    finally:
        db.close()


# ============================================================================
# User Settings Endpoints
# ============================================================================

@router.get("/settings", response_model=UserSettingsResponse, summary="Get User Settings")
async def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's settings.
    
    **Authentication Required**
    """
    settings = profile_service.get_user_settings(current_user.id)
    if not settings:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found. Create them first."
        )
    return settings


@router.post("/settings", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED, summary="Create User Settings")
async def create_settings(
    settings_data: UserSettingsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Create settings for the current user.
    
    **Fields:**
    - theme: 'light' or 'dark' (default: 'light')
    - question_count: Number of questions per assessment, 5-50 (default: 10)
    - sound_enabled: Enable sound effects (default: true)
    - notifications_enabled: Enable notifications (default: true)
    - language: Language code, e.g., 'en', 'es' (default: 'en')
    
    **Authentication Required**
    """
    settings = profile_service.create_user_settings(
        user_id=current_user.id,
        settings_data=settings_data.model_dump(exclude_unset=True)
    )
    return settings


@router.put("/settings", response_model=UserSettingsResponse, summary="Update User Settings")
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's settings.
    Only provided fields will be updated.
    
    **Authentication Required**
    """
    settings = profile_service.update_user_settings(
        user_id=current_user.id,
        settings_data=settings_data.model_dump(exclude_unset=True)
    )
    return settings


@router.delete("/settings", status_code=status.HTTP_204_NO_CONTENT, summary="Delete User Settings")
async def delete_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Delete the current user's settings.
    
    **Authentication Required**
    """
    profile_service.delete_user_settings(current_user.id)
    return None


# ============================================================================
# Medical Profile Endpoints
# ============================================================================

@router.get("/medical", response_model=MedicalProfileResponse, summary="Get Medical Profile")
async def get_medical_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's medical profile.
    
    **Authentication Required**
    """
    profile = profile_service.get_medical_profile(current_user.id)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical profile not found. Create it first."
        )
    return profile


@router.post("/medical", response_model=MedicalProfileResponse, status_code=status.HTTP_201_CREATED, summary="Create Medical Profile")
async def create_medical_profile(
    profile_data: MedicalProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Create a medical profile for the current user.
    
    **Fields (all optional):**
    - blood_type: Blood type (e.g., 'A+', 'O-')
    - allergies: Known allergies
    - medications: Current medications
    - medical_conditions: Medical conditions
    - surgeries: History of surgeries
    - therapy_history: Past counselling/therapy
    - ongoing_health_issues: Current health concerns
    - emergency_contact_name: Emergency contact name
    - emergency_contact_phone: Emergency contact phone
    
    **Authentication Required**
    """
    profile = profile_service.create_medical_profile(
        user_id=current_user.id,
        profile_data=profile_data.model_dump(exclude_unset=True)
    )
    return profile


@router.put("/medical", response_model=MedicalProfileResponse, summary="Update Medical Profile")
async def update_medical_profile(
    profile_data: MedicalProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's medical profile.
    Only provided fields will be updated.
    
    **Authentication Required**
    """
    profile = profile_service.update_medical_profile(
        user_id=current_user.id,
        profile_data=profile_data.model_dump(exclude_unset=True)
    )
    return profile


@router.delete("/medical", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Medical Profile")
async def delete_medical_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Delete the current user's medical profile.
    
    **Authentication Required**
    """
    profile_service.delete_medical_profile(current_user.id)
    return None


# ============================================================================
# Personal Profile Endpoints
# ============================================================================

@router.get("/personal", response_model=PersonalProfileResponse, summary="Get Personal Profile")
async def get_personal_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's personal profile.
    
    **Authentication Required**
    """
    profile = profile_service.get_personal_profile(current_user.id)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personal profile not found. Create it first."
        )
    return profile


@router.post("/personal", response_model=PersonalProfileResponse, status_code=status.HTTP_201_CREATED, summary="Create Personal Profile")
async def create_personal_profile(
    profile_data: PersonalProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Create a personal profile for the current user.
    
    **Fields (all optional):**
    - occupation: Current occupation
    - education: Education level/background
    - marital_status: Marital status
    - hobbies: Hobbies and interests
    - bio: Personal biography (max 1000 chars)
    - life_events: Significant life events (JSON format)
    - email: Email address
    - phone: Phone number
    - date_of_birth: Date of birth (YYYY-MM-DD)
    - gender: Gender
    - address: Physical address
    - society_contribution: Community contributions
    - life_pov: Personal philosophy/perspective
    - high_pressure_events: Recent high-pressure events
    - avatar_path: Path to avatar image
    
    **Authentication Required**
    """
    profile = profile_service.create_personal_profile(
        user_id=current_user.id,
        profile_data=profile_data.model_dump(exclude_unset=True)
    )
    return profile


@router.put("/personal", response_model=PersonalProfileResponse, summary="Update Personal Profile")
async def update_personal_profile(
    profile_data: PersonalProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's personal profile.
    Only provided fields will be updated.
    
    **Authentication Required**
    """
    profile = profile_service.update_personal_profile(
        user_id=current_user.id,
        profile_data=profile_data.model_dump(exclude_unset=True)
    )
    return profile


@router.delete("/personal", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Personal Profile")
async def delete_personal_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Delete the current user's personal profile.
    
    **Authentication Required**
    """
    profile_service.delete_personal_profile(current_user.id)
    return None


# ============================================================================
# User Strengths Endpoints
# ============================================================================

@router.get("/strengths", response_model=UserStrengthsResponse, summary="Get User Strengths")
async def get_strengths(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's strengths profile.
    
    **Authentication Required**
    """
    strengths = profile_service.get_user_strengths(current_user.id)
    if not strengths:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User strengths not found. Create them first."
        )
    return strengths


@router.post("/strengths", response_model=UserStrengthsResponse, status_code=status.HTTP_201_CREATED, summary="Create User Strengths")
async def create_strengths(
    strengths_data: UserStrengthsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Create a strengths profile for the current user.
    
    **Fields:**
    - top_strengths: JSON array of top strengths (default: "[]")
    - areas_for_improvement: JSON array of areas to improve (default: "[]")
    - current_challenges: JSON array of current challenges (default: "[]")
    - learning_style: Preferred learning style (optional)
    - communication_preference: Communication preference (optional)
    - comm_style: Detailed communication style (optional)
    - sharing_boundaries: JSON array of sharing boundaries (default: "[]")
    - goals: Personal goals (optional)
    
    **Authentication Required**
    """
    strengths = profile_service.create_user_strengths(
        user_id=current_user.id,
        strengths_data=strengths_data.model_dump(exclude_unset=True)
    )
    return strengths


@router.put("/strengths", response_model=UserStrengthsResponse, summary="Update User Strengths")
async def update_strengths(
    strengths_data: UserStrengthsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's strengths profile.
    Only provided fields will be updated.
    
    **Authentication Required**
    """
    strengths = profile_service.update_user_strengths(
        user_id=current_user.id,
        strengths_data=strengths_data.model_dump(exclude_unset=True)
    )
    return strengths


@router.delete("/strengths", status_code=status.HTTP_204_NO_CONTENT, summary="Delete User Strengths")
async def delete_strengths(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Delete the current user's strengths profile.
    
    **Authentication Required**
    """
    profile_service.delete_user_strengths(current_user.id)
    return None


# ============================================================================
# Emotional Patterns Endpoints
# ============================================================================

@router.get("/emotional-patterns", response_model=UserEmotionalPatternsResponse, summary="Get Emotional Patterns")
async def get_emotional_patterns(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's emotional patterns.
    
    **Authentication Required**
    """
    patterns = profile_service.get_emotional_patterns(current_user.id)
    if not patterns:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emotional patterns not found. Create them first."
        )
    return patterns


@router.post("/emotional-patterns", response_model=UserEmotionalPatternsResponse, status_code=status.HTTP_201_CREATED, summary="Create Emotional Patterns")
async def create_emotional_patterns(
    patterns_data: UserEmotionalPatternsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Create emotional patterns for the current user.
    
    **Fields:**
    - common_emotions: JSON array of common emotions (default: "[]")
    - emotional_triggers: What causes these emotions (optional)
    - coping_strategies: User's coping strategies (optional)
    - preferred_support: Preferred support style during distress (optional)
    
    **Authentication Required**
    """
    patterns = profile_service.create_emotional_patterns(
        user_id=current_user.id,
        patterns_data=patterns_data.model_dump(exclude_unset=True)
    )
    return patterns


@router.put("/emotional-patterns", response_model=UserEmotionalPatternsResponse, summary="Update Emotional Patterns")
async def update_emotional_patterns(
    patterns_data: UserEmotionalPatternsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's emotional patterns.
    Only provided fields will be updated.
    
    **Authentication Required**
    """
    patterns = profile_service.update_emotional_patterns(
        user_id=current_user.id,
        patterns_data=patterns_data.model_dump(exclude_unset=True)
    )
    return patterns


@router.delete("/emotional-patterns", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Emotional Patterns")
async def delete_emotional_patterns(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Delete the current user's emotional patterns.
    
    **Authentication Required**
    """
    profile_service.delete_emotional_patterns(current_user.id)
    return None
