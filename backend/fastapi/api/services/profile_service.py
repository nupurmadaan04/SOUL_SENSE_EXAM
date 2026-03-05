"""
Profile Service Layer (Async)

Handles CRUD operations for all user profile types using AsyncSession.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from ..models import (
    User,
    UserSettings,
    MedicalProfile,
    PersonalProfile,
    UserStrengths,
    UserEmotionalPatterns
)

class ProfileService:
    """Service for managing all user profile CRUD operations (Async)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_user_exists(self, user_id: int) -> User:
        """Verify user exists and return user object (Async)."""
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    # ========================================================================
    # User Settings CRUD
    # ========================================================================

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Get user settings (Async)."""
        await self._verify_user_exists(user_id)
        stmt = select(UserSettings).filter(UserSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalar_one_or_none()
        if not settings:
            # Lazy creation
            settings = UserSettings(
                user_id=user_id,
                updated_at=datetime.now(UTC).isoformat()
            )
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def create_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Create user settings (Async)."""
        await self._verify_user_exists(user_id)

        # Check if settings already exist
        existing = await self.get_user_settings(user_id)
        # Note: get_user_settings already creates one if it doesn't exist, 
        # so this logic might need adjustment if we want a clean 'create'.
        # For now, keeping original logic's intent.

        settings = UserSettings(
            user_id=user_id,
            **settings_data,
            updated_at=datetime.now(UTC).isoformat()
        )

        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def update_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Update user settings (Async)."""
        settings = await self.get_user_settings(user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found. Create them first."
            )

        # Update fields
        for key, value in settings_data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def delete_user_settings(self, user_id: int) -> bool:
        """Delete user settings (Async)."""
        settings = await self.get_user_settings(user_id)
        await self.db.delete(settings)
        await self.db.commit()
        return True

    # ========================================================================
    # Medical Profile CRUD
    # ========================================================================

    async def get_medical_profile(self, user_id: int) -> Optional[MedicalProfile]:
        """Get medical profile (Async)."""
        await self._verify_user_exists(user_id)
        stmt = select(MedicalProfile).filter(MedicalProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            # Lazy creation
            profile = MedicalProfile(
                user_id=user_id,
                last_updated=datetime.now(UTC).isoformat()
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def create_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Create medical profile (Async)."""
        await self._verify_user_exists(user_id)

        profile = MedicalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.now(UTC).isoformat()
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Update medical profile (Async)."""
        profile = await self.get_medical_profile(user_id)
        
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_medical_profile(self, user_id: int) -> bool:
        """Delete medical profile (Async)."""
        profile = await self.get_medical_profile(user_id)
        await self.db.delete(profile)
        await self.db.commit()
        return True

    # ========================================================================
    # Personal Profile CRUD
    # ========================================================================

    async def get_personal_profile(self, user_id: int) -> Optional[PersonalProfile]:
        """Get personal profile (Async)."""
        await self._verify_user_exists(user_id)
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            # Lazy creation
            profile = PersonalProfile(
                user_id=user_id,
                last_updated=datetime.now(UTC).isoformat()
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def create_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Create personal profile (Async)."""
        await self._verify_user_exists(user_id)

        profile = PersonalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.now(UTC).isoformat()
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Update personal profile (Async)."""
        profile = await self.get_personal_profile(user_id)
        
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_personal_profile(self, user_id: int) -> bool:
        """Delete personal profile (Async)."""
        profile = await self.get_personal_profile(user_id)
        await self.db.delete(profile)
        await self.db.commit()
        return True

    # ========================================================================
    # User Strengths CRUD
    # ========================================================================

    async def get_user_strengths(self, user_id: int) -> Optional[UserStrengths]:
        """Get user strengths (Async)."""
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
                last_updated=datetime.now(UTC).isoformat()
            )
            self.db.add(strengths)
            await self.db.commit()
            await self.db.refresh(strengths)
        return strengths

    async def create_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Create user strengths (Async)."""
        await self._verify_user_exists(user_id)

        strengths = UserStrengths(
            user_id=user_id,
            **strengths_data,
            last_updated=datetime.now(UTC).isoformat()
        )

        self.db.add(strengths)
        await self.db.commit()
        await self.db.refresh(strengths)
        return strengths

    async def update_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Update user strengths (Async)."""
        strengths = await self.get_user_strengths(user_id)
        
        for key, value in strengths_data.items():
            if value is not None and hasattr(strengths, key):
                setattr(strengths, key, value)

        strengths.last_updated = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(strengths)
        return strengths

    async def delete_user_strengths(self, user_id: int) -> bool:
        """Delete user strengths (Async)."""
        strengths = await self.get_user_strengths(user_id)
        await self.db.delete(strengths)
        await self.db.commit()
        return True

    # ========================================================================
    # Emotional Patterns CRUD
    # ========================================================================

    async def get_emotional_patterns(self, user_id: int) -> Optional[UserEmotionalPatterns]:
        """Get emotional patterns (Async)."""
        await self._verify_user_exists(user_id)
        stmt = select(UserEmotionalPatterns).filter(UserEmotionalPatterns.user_id == user_id)
        result = await self.db.execute(stmt)
        patterns = result.scalar_one_or_none()
        if not patterns:
             # Lazy creation
            patterns = UserEmotionalPatterns(
                user_id=user_id,
                common_emotions="[]",
                last_updated=datetime.now(UTC).isoformat()
            )
            self.db.add(patterns)
            await self.db.commit()
            await self.db.refresh(patterns)
        return patterns

    async def create_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Create emotional patterns (Async)."""
        await self._verify_user_exists(user_id)

        patterns = UserEmotionalPatterns(
            user_id=user_id,
            **patterns_data,
            last_updated=datetime.now(UTC).isoformat()
        )

        self.db.add(patterns)
        await self.db.commit()
        await self.db.refresh(patterns)
        return patterns

    async def update_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Update emotional patterns (Async)."""
        patterns = await self.get_emotional_patterns(user_id)
        
        for key, value in patterns_data.items():
            if value is not None and hasattr(patterns, key):
                setattr(patterns, key, value)

        patterns.last_updated = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(patterns)
        return patterns

    async def delete_emotional_patterns(self, user_id: int) -> bool:
        """Delete emotional patterns (Async)."""
        patterns = await self.get_emotional_patterns(user_id)
        await self.db.delete(patterns)
        await self.db.commit()
        return True

    # ========================================================================
    # Complete Profile Operations
    # ========================================================================

    async def get_complete_profile(self, user_id: int) -> Dict[str, Any]:
        """Get complete user profile with all sub-profiles (Async)."""
        user = await self._verify_user_exists(user_id)

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "created_at": user.created_at,
                "last_login": user.last_login
            },
            "settings": await self.get_user_settings(user_id),
            "medical_profile": await self.get_medical_profile(user_id),
            "personal_profile": await self.get_personal_profile(user_id),
            "strengths": await self.get_user_strengths(user_id),
            "emotional_patterns": await self.get_emotional_patterns(user_id)
        }
