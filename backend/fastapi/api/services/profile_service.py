"""
Profile Service Layer

Handles CRUD operations for all user profile types:
- UserSettings
- MedicalProfile
- PersonalProfile
- UserStrengths
- UserEmotionalPatterns
"""

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DatabaseError
from fastapi import HTTPException, status

# Import models from models module
from ..models import (
    User,
    UserSettings,
    MedicalProfile,
    PersonalProfile,
    UserStrengths,
    UserEmotionalPatterns
)
from .db_error_handler import safe_db_query, DatabaseConnectionError
import logging

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing all user profile CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_user_exists(self, user_id: int) -> User:
        """Verify user exists and return user object."""
        try:
            user = safe_db_query(
                self.db,
                lambda: self.db.query(User).filter(User.id == user_id).first(),
                "verify user exists"
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            return user
        except DatabaseConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    # ========================================================================
    # User Settings CRUD
    # ========================================================================

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Get user settings."""
        await self._verify_user_exists(user_id)
        stmt = select(UserSettings).filter(UserSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Lazy creation
            settings = UserSettings(
                user_id=user_id,
                updated_at=datetime.utcnow().isoformat()
            )
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def create_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Create user settings."""
        await self._verify_user_exists(user_id)

        # Check if settings already exist
        existing = await self.get_user_settings(user_id)
        # Note: get_user_settings lazy creates, so if we call it, it will exist.
        # This check might need revision if lazy creation is the intended behavior.
        # However, following the original logic:
        if existing and existing.id: # Just a check to see if it was already there or just created
             # Original logic seems to allow lazy creation in 'get', but create_user_settings
             # might be used for explicit initial creation.
             pass

        settings = UserSettings(
            user_id=user_id,
            **settings_data,
            updated_at=datetime.utcnow().isoformat()
        )

        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def update_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Update user settings."""
        settings = await self.get_user_settings(user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found. Create them first."
            )

        # Update only provided fields
        for key, value in settings_data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow().isoformat()
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def delete_user_settings(self, user_id: int) -> bool:
        """Delete user settings."""
        settings = await self.get_user_settings(user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )

        await self.db.delete(settings)
        await self.db.commit()
        return True

    # ========================================================================
    # Medical Profile CRUD
    # ========================================================================

    async def get_medical_profile(self, user_id: int) -> Optional[MedicalProfile]:
        """Get medical profile."""
        await self._verify_user_exists(user_id)
        stmt = select(MedicalProfile).filter(MedicalProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            # Lazy creation
            profile = MedicalProfile(
                user_id=user_id,
                last_updated=datetime.utcnow().isoformat()
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def create_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Create medical profile."""
        await self._verify_user_exists(user_id)

        # Check if profile already exists
        # Original code used get_medical_profile which lazy creates.
        # This pattern makes 'existing' always true if lazy creation happens.
        # We'll stick to the original logic pattern but make it async.
        existing = await self.get_medical_profile(user_id)
        if existing and existing.id:
             # Just following original behavior
             pass

        profile = MedicalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Update medical profile."""
        profile = await self.get_medical_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical profile not found. Create it first."
            )

        # Update only provided fields
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow().isoformat()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_medical_profile(self, user_id: int) -> bool:
        """Delete medical profile."""
        profile = await self.get_medical_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical profile not found"
            )

        await self.db.delete(profile)
        await self.db.commit()
        return True

    # ========================================================================
    # Personal Profile CRUD
    # ========================================================================

    async def get_personal_profile(self, user_id: int) -> Optional[PersonalProfile]:
        """Get personal profile."""
        await self._verify_user_exists(user_id)
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            # Lazy creation
            profile = PersonalProfile(
                user_id=user_id,
                last_updated=datetime.utcnow().isoformat()
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def create_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Create personal profile."""
        await self._verify_user_exists(user_id)

        existing = await self.get_personal_profile(user_id)
        # Original code check
        if existing and existing.id:
            pass

        profile = PersonalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Update personal profile."""
        profile = await self.get_personal_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal profile not found. Create it first."
            )

        # Update only provided fields
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow().isoformat()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_personal_profile(self, user_id: int) -> bool:
        """Delete personal profile."""
        profile = await self.get_personal_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal profile not found"
            )

        await self.db.delete(profile)
        await self.db.commit()
        return True

    # ========================================================================
    # User Strengths CRUD
    # ========================================================================

    async def get_user_strengths(self, user_id: int) -> Optional[UserStrengths]:
        """Get user strengths."""
        await self._verify_user_exists(user_id)
        stmt = select(UserStrengths).filter(UserStrengths.user_id == user_id)
        result = await self.db.execute(stmt)
        strengths = result.scalar_one_or_none()
        
        if not strengths:
            # Lazy creation
            strengths = UserStrengths(
                user_id=user_id,
                top_strengths="[]",
                areas_for_improvement="[]",
                current_challenges="[]",
                sharing_boundaries="[]",
                last_updated=datetime.utcnow().isoformat()
            )
            self.db.add(strengths)
            await self.db.commit()
            await self.db.refresh(strengths)
        return strengths

    async def create_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Create user strengths."""
        await self._verify_user_exists(user_id)

        existing = await self.get_user_strengths(user_id)
        if existing and existing.id:
            pass

        strengths = UserStrengths(
            user_id=user_id,
            **strengths_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(strengths)
        await self.db.commit()
        await self.db.refresh(strengths)
        return strengths

    async def update_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Update user strengths."""
        strengths = await self.get_user_strengths(user_id)
        if not strengths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User strengths not found. Create them first."
            )

        # Update only provided fields
        for key, value in strengths_data.items():
            if value is not None and hasattr(strengths, key):
                setattr(strengths, key, value)

        strengths.last_updated = datetime.utcnow().isoformat()
        await self.db.commit()
        await self.db.refresh(strengths)
        return strengths

    async def delete_user_strengths(self, user_id: int) -> bool:
        """Delete user strengths."""
        strengths = await self.get_user_strengths(user_id)
        if not strengths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User strengths not found"
            )

        await self.db.delete(strengths)
        await self.db.commit()
        return True

    # ========================================================================
    # Emotional Patterns CRUD
    # ========================================================================

    async def get_emotional_patterns(self, user_id: int) -> Optional[UserEmotionalPatterns]:
        """Get emotional patterns."""
        await self._verify_user_exists(user_id)
        stmt = select(UserEmotionalPatterns).filter(UserEmotionalPatterns.user_id == user_id)
        result = await self.db.execute(stmt)
        patterns = result.scalar_one_or_none()
        
        if not patterns:
             # Lazy creation
            patterns = UserEmotionalPatterns(
                user_id=user_id,
                common_emotions="[]",
                last_updated=datetime.utcnow().isoformat()
            )
            self.db.add(patterns)
            await self.db.commit()
            await self.db.refresh(patterns)
        return patterns

    async def create_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Create emotional patterns."""
        await self._verify_user_exists(user_id)

        existing = await self.get_emotional_patterns(user_id)
        if existing and existing.id:
            pass

        patterns = UserEmotionalPatterns(
            user_id=user_id,
            **patterns_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(patterns)
        await self.db.commit()
        await self.db.refresh(patterns)
        return patterns

    async def update_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Update emotional patterns."""
        patterns = await self.get_emotional_patterns(user_id)
        if not patterns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emotional patterns not found. Create them first."
            )

        # Update only provided fields
        for key, value in patterns_data.items():
            if value is not None and hasattr(patterns, key):
                setattr(patterns, key, value)

        patterns.last_updated = datetime.utcnow().isoformat()
        await self.db.commit()
        await self.db.refresh(patterns)
        return patterns

    async def delete_emotional_patterns(self, user_id: int) -> bool:
        """Delete emotional patterns."""
        patterns = await self.get_emotional_patterns(user_id)
        if not patterns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emotional patterns not found"
            )

        await self.db.delete(patterns)
        await self.db.commit()
        return True

    # ========================================================================
    # Complete Profile Operations
    # ========================================================================

    async def get_complete_profile(self, user_id: int) -> Dict[str, Any]:
        """Get complete user profile with all sub-profiles."""
        user = await self._verify_user_exists(user_id)

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "onboarding_completed": user.onboarding_completed or False
            },
            "settings": await self.get_user_settings(user_id),
            "medical_profile": await self.get_medical_profile(user_id),
            "personal_profile": await self.get_personal_profile(user_id),
            "strengths": await self.get_user_strengths(user_id),
            "emotional_patterns": await self.get_emotional_patterns(user_id),
            "onboarding_completed": user.onboarding_completed or False
        }
