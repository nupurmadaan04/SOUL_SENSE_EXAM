"""API router for exam write operations."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.db_service import get_db
from ..services.exam_service import ExamService
from ..services.results_service import AssessmentResultsService
from ..schemas import ExamResponseCreate, ExamResultCreate, AssessmentResponse, AssessmentListResponse, DetailedExamResult
from .auth import get_current_user
from ..root_models import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/start", status_code=201)
async def start_exam(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new exam session and return session_id."""
    session_id = await ExamService.start_exam(db, current_user)
    return {"session_id": session_id}

@router.post("/{session_id}/responses", status_code=201)
async def save_response(
    session_id: str,
    response_data: ExamResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a single question response (click) linked to session.
    """
    try:
        success = await ExamService.save_response(db, current_user, session_id, response_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save response")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/complete", response_model=AssessmentResponse)
async def complete_exam(
    session_id: str,
    result_data: ExamResultCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a completed exam score linked to session.
    """
    try:
        score = await ExamService.save_score(db, current_user, session_id, result_data)
        return AssessmentResponse.model_validate(score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=AssessmentListResponse)
async def get_exam_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated history of exam results for current user.
    """
    try:
        skip = (page - 1) * page_size
        assessments, total = await ExamService.get_history(db, current_user, skip, page_size)
        
        return AssessmentListResponse(
            total=total,
            assessments=[AssessmentResponse.model_validate(a) for a in assessments],
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/results", response_model=DetailedExamResult)
async def get_detailed_results(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed breakdown for a specific assessment.
    """
    try:
        result = await AssessmentResultsService.get_detailed_results(db, id, current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="Assessment not found or access denied")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching detailed results for assessment {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
