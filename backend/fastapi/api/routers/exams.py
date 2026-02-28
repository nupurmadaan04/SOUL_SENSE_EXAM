"""API router for exam write operations."""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.db_service import get_db
from ..services.exam_service import ExamService
from ..services.results_service import AssessmentResultsService
from ..schemas import ExamResponseCreate, ExamResultCreate, AssessmentResponse, AssessmentListResponse, DetailedExamResult
from .auth import get_current_user
from ..models import User
from ...app.core import NotFoundError, InternalServerError, ValidationError

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
            raise InternalServerError(message="Failed to save response")
        return {"status": "success"}
    except Exception as e:
        raise InternalServerError(message="Failed to save response", details=[{"error": str(e)}])

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
        raise InternalServerError(message="Failed to save exam results", details=[{"error": str(e)}])

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
        raise InternalServerError(message="Failed to retrieve exam history", details=[{"error": str(e)}])

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
        result = AssessmentResultsService.get_detailed_results(db, id, current_user.id)
        if result is None:
            logger.info(
                "Assessment result not found",
                extra={"assessment_id": id, "user_id": current_user.id},
            )
            raise HTTPException(
                status_code=404,
                detail="No result found. The requested assessment does not exist or has been removed.",
        result = await AssessmentResultsService.get_detailed_results(db, id, current_user.id)
        if not result:
            raise NotFoundError(
                resource="Assessment",
                resource_id=str(id),
                details=[{"message": "Assessment not found or access denied"}]
            )
        return result
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(
            "Error fetching detailed results",
            extra={"assessment_id": id, "user_id": current_user.id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Internal server error")
        logger.error(f"Error fetching detailed results for assessment {id}: {e}")
        raise InternalServerError(message="Failed to retrieve assessment results")
