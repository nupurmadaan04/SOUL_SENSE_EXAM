"""API router for exam write operations."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..services.db_service import get_db
from ..services.exam_service import ExamService
from ..services.results_service import AssessmentResultsService
from ..schemas import (
    ExamResponseCreate,
    ExamResultCreate,
    AssessmentResponse,
    AssessmentListResponse,
    DetailedExamResult,
    ExamSubmit,
    AnswerSubmit,
)
from .auth import get_current_user
from ..models import User, Question

logger = logging.getLogger(__name__)

router = APIRouter()


from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/start", status_code=201)
async def start_exam(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new exam session and return session_id."""
    session_id = await ExamService.start_exam(db, current_user)
    return {"session_id": session_id}


@router.post("/submit", status_code=201)
async def submit_exam(
    payload: ExamSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Completeness validation
    if not payload.is_draft:
        stmt = select(func.count(Question.id)).filter(Question.is_active == 1)
        result = await db.execute(stmt)
        expected_count = result.scalar() or 0

        submitted_count = len(payload.answers)

        if submitted_count != expected_count:
            logger.warning(
                "Incomplete exam submission rejected",
                extra={
                    "user_id": current_user.id,
                    "session_id": payload.session_id,
                    "submitted": submitted_count,
                    "expected": expected_count,
                },
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "EXAM_INCOMPLETE",
                    "message": f"Expected {expected_count} answers but got {submitted_count}.",
                },
            )

    try:
        # Save responses
        for answer in payload.answers:
            response_data = ExamResponseCreate(
                question_id=answer.question_id,
                value=answer.value,
                session_id=payload.session_id,
            )
            await ExamService.save_response(db, current_user, payload.session_id, response_data)
        
        if not payload.is_draft:
            await ExamService.mark_as_submitted(db, current_user.id, payload.session_id)
            
    except Exception as e:
        logger.error(f"Failed to persist batch submit: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist exam responses.")

    return {
        "status": "accepted",
        "session_id": payload.session_id,
        "is_draft": payload.is_draft,
    }


@router.post("/{session_id}/responses", status_code=201)
async def save_response(
    session_id: str,
    response_data: ExamResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        success = await ExamService.save_response(db, current_user, session_id, response_data)
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
    skip = (page - 1) * page_size
    assessments, total = await ExamService.get_history(db, current_user, skip, page_size)

    return AssessmentListResponse(
        total=total,
        assessments=[AssessmentResponse.model_validate(a) for a in assessments],
        page=page,
        page_size=page_size
    )


@router.get("/{id}/results", response_model=DetailedExamResult)
async def get_detailed_results(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await AssessmentResultsService.get_detailed_results(db, id, current_user.id)
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
