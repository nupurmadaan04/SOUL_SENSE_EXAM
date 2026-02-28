"""API router for assessment endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Annotated
from ..services.db_service import get_db, AssessmentService
from ...app.core import NotFoundError, AuthorizationError
from ..schemas import (
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentDetailResponse,
    AssessmentStatsResponse
)
from .auth import get_current_user
from ..models import User

router = APIRouter(tags=["Assessments"])


@router.get("/", response_model=AssessmentListResponse)
async def get_assessments(
    username: Optional[str] = Query(None, description="Filter by username (Admin only)"),
    age_group: Optional[str] = Query(None, description="Filter by age group"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a paginated list of assessments.

    - **username**: Optional filter by username (Admins can filter by any user, non-admins are restricted to their own)
    - **age_group**: Optional filter by age group (e.g., "18-25", "26-35")
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    """
    skip = (page - 1) * page_size
    
    # Enforce ownership: Non-admins can only see their own assessments
    if not getattr(current_user, "is_admin", False):
        username = current_user.username
    
    assessments, total = await AssessmentService.get_assessments(
        db=db,
        skip=skip,
        limit=page_size,
        user_id=current_user.id
    )
    
    return AssessmentListResponse(
        total=total,
        assessments=[AssessmentResponse.model_validate(a) for a in assessments],
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=AssessmentStatsResponse)
async def get_assessment_stats(
    username: Optional[str] = Query(None, description="Filter stats by username (Admin only)"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistical summary of assessments.

    - **username**: Optional filter to get stats for a specific user (Admin only)
    """
    # Enforce ownership: Non-admins can only see their own stats
    if not getattr(current_user, "is_admin", False):
        username = current_user.username
        
    stats = await AssessmentService.get_assessment_stats(db=db, username=username)
    
    return AssessmentStatsResponse(**stats)


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
async def get_assessment(
    assessment_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific assessment owned by the authenticated user.

    - **assessment_id**: The ID of the assessment to retrieve
    """
    assessment = await AssessmentService.get_assessment_by_id(db=db, assessment_id=assessment_id)

    if not assessment:
        raise NotFoundError(resource="Assessment", resource_id=str(assessment_id))

    # Ownership Check: Only owner or admin can view details
    if assessment.username != current_user.username and not getattr(current_user, "is_admin", False):
        raise AuthorizationError(message="Not authorized to view this assessment's details")

    responses = await AssessmentService.get_assessment_responses(db=db, assessment_id=assessment_id)
    
    assessment_dict = {
        "id": assessment.id,
        "username": assessment.username,
        "total_score": assessment.total_score,
        "sentiment_score": assessment.sentiment_score,
        "reflection_text": assessment.reflection_text,
        "is_rushed": assessment.is_rushed,
        "is_inconsistent": assessment.is_inconsistent,
        "age": assessment.age,
        "detailed_age_group": assessment.detailed_age_group,
        "timestamp": assessment.timestamp,
        "responses_count": len(responses)
    }
    
    return AssessmentDetailResponse(**assessment_dict)

