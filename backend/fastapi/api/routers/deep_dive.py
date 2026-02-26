from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..services.deep_dive_service import DeepDiveService
from ..schemas import (
    DeepDiveType, 
    DeepDiveQuestion, 
    DeepDiveSubmission, 
    DeepDiveResultResponse
)
from ..root_models import User
from .auth import get_current_user

router = APIRouter()

@router.get("/types", response_model=List[DeepDiveType])
async def get_deep_dive_types():
    """List all available deep dive assessments."""
    return DeepDiveService.get_available_types()

@router.get("/recommendations", response_model=List[str])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommended deep dives based on user's recent performance.
    Returns list of Deep Dive IDs (e.g. ['strengths_deep_dive']).
    """
    return await DeepDiveService.get_recommendations(db, current_user)

@router.get("/{assessment_type}/questions", response_model=List[DeepDiveQuestion])
async def get_questions(
    assessment_type: str,
    count: int = Query(10, ge=5, le=20, description="Number of questions to fetch")
):
    """
    Fetch questions for a specific assessment.
    """
    try:
        return DeepDiveService.get_questions(assessment_type, count)
    except Exception:
        raise HTTPException(status_code=404, detail="Assessment type not found")

@router.post("/submit", response_model=DeepDiveResultResponse)
async def submit_deep_dive(
    submission: DeepDiveSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit answers for a deep dive assessment.
    """
    # Rate limiting could be added here (omitted for MVP speed, covered in plan audit as 'strict' but doing basic impl first)
    return await DeepDiveService.submit_assessment(db, current_user, submission)

@router.get("/history", response_model=List[DeepDiveResultResponse])
async def get_deep_dive_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get past deep dive results."""
    return await DeepDiveService.get_history(db, current_user)
