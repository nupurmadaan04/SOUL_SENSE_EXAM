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
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.limiter import limiter
from app.core import NotFoundError

from ..schemas import (
    # User Settings
    UserSettingsCreate,
    UserSettingsUpdate,
    UserSettingsResponse,
    # Data Consent
    DataConsentUpdate,
    DataConsentResponse,
    # Crisis Settings
    CrisisSettingsUpdate,
    CrisisSettingsResponse,
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
from ..models import User

router = APIRouter(tags=["Profiles"])


async def get_profile_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get ProfileService (Async)."""
    """Dependency to get ProfileService."""
    return ProfileService(db)


# ============================================================================
# User Settings Endpoints
# ============================================================================

@router.get("/settings", response_model=UserSettingsResponse, summary="Get User Settings")
@limiter.limit("100/minute")
async def get_settings(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's settings.
    """
    settings = await profile_service.get_user_settings(current_user.id)
    if not settings:
        raise NotFoundError(
            resource="User settings",
            details=[{"message": "Create settings first using POST /profiles/settings"}]
        )
    return settings


@router.post("/settings", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED, summary="Create User Settings")
@limiter.limit("10/minute")
async def create_settings(
    request: Request,
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
    settings = await profile_service.create_user_settings(
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
    """
    settings = await profile_service.update_user_settings(
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
    """
    await profile_service.delete_user_settings(current_user.id)
    return None


# ============================================================================
# Data Consent Endpoints
# ============================================================================

@router.get("/consent", response_model=DataConsentResponse, summary="Get Data Consent Settings")
async def get_consent(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's data consent settings.
    """
    settings = await profile_service.get_user_settings(current_user.id)
    if not settings:
        raise NotFoundError(resource="User settings")
    return DataConsentResponse(
        consent_ml_training=settings.consent_ml_training,
        consent_aggregated_research=settings.consent_aggregated_research
    )


@router.patch("/consent", response_model=DataConsentResponse, summary="Update Data Consent Settings")
async def update_consent(
    consent_data: DataConsentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's data consent settings.
    """
    settings = await profile_service.update_user_settings(
        user_id=current_user.id,
        settings_data=consent_data.model_dump(exclude_unset=True)
    )
    return DataConsentResponse(
        consent_ml_training=settings.consent_ml_training,
        consent_aggregated_research=settings.consent_aggregated_research
    )


# ============================================================================
# Crisis Settings Endpoints
# ============================================================================

@router.get("/crisis_settings", response_model=CrisisSettingsResponse, summary="Get Crisis Settings")
async def get_crisis_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Get the current user's crisis settings.
    """
    settings = await profile_service.get_user_settings(current_user.id)
    if not settings:
        raise NotFoundError(resource="User settings")
    return CrisisSettingsResponse(
        crisis_mode_enabled=settings.crisis_mode_enabled
    )


@router.patch("/crisis_settings", response_model=CrisisSettingsResponse, summary="Update Crisis Settings")
async def update_crisis_settings(
    crisis_data: CrisisSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)]
):
    """
    Update the current user's crisis settings.
    """
    settings = await profile_service.update_user_settings(
        user_id=current_user.id,
        settings_data=crisis_data.model_dump()
    )
    return CrisisSettingsResponse(
        crisis_mode_enabled=settings.crisis_mode_enabled
    )


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
    """
    profile = await profile_service.get_medical_profile(current_user.id)
    if not profile:
        raise NotFoundError(
            resource="Medical profile",
            details=[{"message": "Create medical profile first using POST /profiles/medical"}]
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
    profile = await profile_service.create_medical_profile(
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
    """
    profile = await profile_service.update_medical_profile(
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
    """
    await profile_service.delete_medical_profile(current_user.id)
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
    """
    profile = await profile_service.get_personal_profile(current_user.id)
    if not profile:
        raise NotFoundError(
            resource="Personal profile",
            details=[{"message": "Create personal profile first using POST /profiles/personal"}]
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
    profile = await profile_service.create_personal_profile(
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
    """
    profile = await profile_service.update_personal_profile(
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
    """
    await profile_service.delete_personal_profile(current_user.id)
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
    """
    strengths = await profile_service.get_user_strengths(current_user.id)
    if not strengths:
        raise NotFoundError(
            resource="User strengths",
            details=[{"message": "Create strengths first using POST /profiles/strengths"}]
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
    strengths = await profile_service.create_user_strengths(
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
    """
    strengths = await profile_service.update_user_strengths(
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
    """
    await profile_service.delete_user_strengths(current_user.id)
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
    """
    patterns = await profile_service.get_emotional_patterns(current_user.id)
    if not patterns:
        raise NotFoundError(
            resource="Emotional patterns",
            details=[{"message": "Create emotional patterns first using POST /profiles/emotional-patterns"}]
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
    patterns = await profile_service.create_emotional_patterns(
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
    """
    patterns = await profile_service.update_emotional_patterns(
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
    """
    await profile_service.delete_emotional_patterns(current_user.id)
    return None
