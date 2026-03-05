from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..routers.auth import get_current_user
from ..models import User
from ..schemas import (
    GamificationSummary, 
    AchievementResponse, 
    UserXPResponse, 
    UserStreakResponse,
    LeaderboardEntry,
    ChallengeResponse
)
from ..services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["gamification"])

@router.get("/summary", response_model=GamificationSummary)
async def get_gamification_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a summary of user's XP, streaks, and recent achievements."""
    summary = await GamificationService.get_user_summary(db, current_user.id)
    return summary

@router.get("/achievements", response_model=List[AchievementResponse])
async def get_my_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all achievements and user's progress on them."""
    # This would normally join Achievement and UserAchievement
    # For now, let's return a basic list
    summary = await GamificationService.get_user_summary(db, current_user.id)
    return summary["recent_achievements"]

@router.get("/streak", response_model=List[UserStreakResponse])
async def get_my_streaks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current streaks."""
    summary = await GamificationService.get_user_summary(db, current_user.id)
    return summary["streaks"]

@router.get("/xp", response_model=UserXPResponse)
async def get_my_xp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's XP and level info."""
    summary = await GamificationService.get_user_summary(db, current_user.id)
    return summary["xp"]

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get the anonymized global leaderboard."""
    return await GamificationService.get_leaderboard(db, limit)

@router.get("/challenges", response_model=List[ChallengeResponse])
async def get_challenges(
    db: AsyncSession = Depends(get_db)
):
    """Get available challenges."""
    # Implementation pending Phase 3
    return []

@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_achievements(
    db: AsyncSession = Depends(get_db)
):
    """Seed initial achievements (Admin only in production)."""
    await GamificationService.seed_initial_achievements(db)
    return {"message": "Achievements seeded"}
