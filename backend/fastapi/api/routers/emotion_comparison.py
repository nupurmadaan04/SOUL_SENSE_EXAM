"""
Emotion Comparison API Router.

Endpoints for comparing emotional patterns across different time periods.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from ..services.db_service import get_db
from ..services.emotion_comparison_service import EmotionComparisonService
from ..models import User
from .auth import get_current_user

router = APIRouter()


class ComparisonRequest(BaseModel):
    """Request model for emotion comparison."""
    period1_start: str
    period1_end: str
    period2_start: str
    period2_end: str


@router.post("/compare")
async def compare_emotions(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare emotional metrics between two time periods.
    
    Returns side-by-side comparison with:
    - Average sentiment, mood, stress levels
    - EQ scores
    - Activity metrics
    - Percentage changes
    """
    # Parse dates
    period1_start = datetime.fromisoformat(request.period1_start)
    period1_end = datetime.fromisoformat(request.period1_end)
    period2_start = datetime.fromisoformat(request.period2_start)
    period2_end = datetime.fromisoformat(request.period2_end)
    
    # Get comparison
    comparison = await EmotionComparisonService.compare_periods(
        db=db,
        user_id=current_user.id,
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end
    )
    
    return comparison


@router.get("/quick-compare")
async def quick_compare(
    period1: str = Query(..., description="Period 1: 'last_week', 'last_month', 'last_quarter'"),
    period2: str = Query(..., description="Period 2: 'this_week', 'this_month', 'this_quarter'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick comparison using predefined periods.
    
    Supported periods:
    - this_week, last_week
    - this_month, last_month
    - this_quarter, last_quarter
    """
    from datetime import timedelta
    
    now = datetime.now()
    
    # Define period mappings
    periods = {
        'this_week': (now - timedelta(days=now.weekday()), now),
        'last_week': (
            now - timedelta(days=now.weekday() + 7),
            now - timedelta(days=now.weekday() + 1)
        ),
        'this_month': (now.replace(day=1), now),
        'last_month': (
            (now.replace(day=1) - timedelta(days=1)).replace(day=1),
            now.replace(day=1) - timedelta(days=1)
        ),
        'this_quarter': (
            now.replace(month=((now.month - 1) // 3) * 3 + 1, day=1),
            now
        ),
        'last_quarter': (
            (now.replace(month=((now.month - 1) // 3) * 3 + 1, day=1) - timedelta(days=90)).replace(day=1),
            now.replace(month=((now.month - 1) // 3) * 3 + 1, day=1) - timedelta(days=1)
        )
    }
    
    if period1 not in periods or period2 not in periods:
        return {"error": "Invalid period specified"}
    
    p1_start, p1_end = periods[period1]
    p2_start, p2_end = periods[period2]
    
    comparison = await EmotionComparisonService.compare_periods(
        db=db,
        user_id=current_user.id,
        period1_start=p1_start,
        period1_end=p1_end,
        period2_start=p2_start,
        period2_end=p2_end
    )
    
    return comparison
