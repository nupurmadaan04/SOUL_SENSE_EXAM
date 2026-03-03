from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from ..dependencies import get_db, get_current_user
from ..services.badge_service import BadgeService
from ..models import User

router = APIRouter(prefix="/badges", tags=["badges"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all badges for the current user with progress."""
    return await BadgeService.get_user_badges(current_user.id, db)

@router.post("/check")
async def check_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check and unlock eligible badges for the current user."""
    unlocked = await BadgeService.check_and_unlock_badges(current_user.id, db)
    return {
        "unlocked_count": len(unlocked),
        "badges": [{"name": b.name, "icon": b.icon} for b in unlocked]
    }
