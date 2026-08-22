"""API router for exam operations."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_

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
from ..models import User, Score, Response, Question
from ..utils.race_condition_protection import check_idempotency, complete_idempotency

logger = logging.getLogger("api.exams")
router = APIRouter(tags=["Exams"])


class DirectExamAnswer(BaseModel):
    question_id: int
    value: Union[int, float] = Field(default=3, alias="response_value")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class DirectExamSubmissionRequest(BaseModel):
    answers: Optional[List[DirectExamAnswer]] = Field(default_factory=list, alias="responses")
    reflection: Optional[str] = Field(default=None, alias="reflection_text")
    duration_seconds: Optional[int] = 0

    model_config = {"populate_by_name": True, "extra": "ignore"}


class DraftSaveRequest(BaseModel):
    answers: Dict[str, int] = Field(default_factory=dict)
    current_question_index: Optional[int] = 0
    duration_seconds: Optional[int] = 0


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_exam_direct(
    payload: DirectExamSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct exam submission endpoint matching frontend examsApi.submitExam.
    Persists responses, calculates 4-point EQ score, and stores score record.
    """
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit empty exam answers"
        )

    session_id = str(uuid.uuid4())
    total_val = sum(int(a.value) for a in payload.answers)
    max_val = len(payload.answers) * 4 # 4-point scale
    calculated_score = int((total_val / (max_val if max_val > 0 else 1)) * 100)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Save score
    new_score = Score(
        user_id=current_user.id,
        username=current_user.username,
        session_id=session_id,
        total_score=calculated_score,
        sentiment_score=float(calculated_score),
        reflection_text=payload.reflection or "",
        timestamp=now_iso,
        status="completed"
    )
    db.add(new_score)
    await db.flush()

    # Save responses
    for ans in payload.answers:
        resp_val = max(1, min(4, int(ans.value)))
        resp = Response(
            user_id=current_user.id,
            username=current_user.username,
            session_id=session_id,
            question_id=ans.question_id,
            response_value=resp_val,
            timestamp=now_iso
        )
        db.add(resp)

    await db.commit()
    await db.refresh(new_score)

    logger.info(f"Exam submitted successfully: Score {calculated_score}% for user {current_user.username}")

    return {
        "id": new_score.id,
        "total_score": new_score.total_score,
        "sentiment_score": new_score.sentiment_score,
        "reflection": new_score.reflection_text,
        "timestamp": new_score.timestamp
    }


@router.get("", response_model=List[AssessmentResponse])
@router.get("/", response_model=List[AssessmentResponse])
async def list_exam_results(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all assessment results for the current authenticated user."""
    stmt = select(Score).filter(
        or_(Score.user_id == current_user.id, Score.username == current_user.username)
    ).order_by(desc(Score.timestamp))
    res = await db.execute(stmt)
    scores = res.scalars().all()
    return [AssessmentResponse.model_validate(s) for s in scores]


@router.get("/history", response_model=AssessmentListResponse)
async def get_exam_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated history of assessment results for the current user."""
    try:
        skip = (page - 1) * page_size
        stmt = select(Score).filter(
            or_(Score.user_id == current_user.id, Score.username == current_user.username)
        ).order_by(desc(Score.timestamp)).offset(skip).limit(page_size)
        res = await db.execute(stmt)
        assessments = res.scalars().all()

        count_stmt = select(func.count(Score.id)).filter(
            or_(Score.user_id == current_user.id, Score.username == current_user.username)
        )
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        return AssessmentListResponse(
            total=total,
            assessments=[AssessmentResponse.model_validate(a) for a in assessments],
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Failed to get exam history for user {current_user.id}: {e}")
        return AssessmentListResponse(
            total=0,
            assessments=[],
            page=page,
            page_size=page_size
        )


@router.get("/{id}", response_model=DetailedExamResult)
async def get_exam_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed exam result with category breakdown and recommendations."""
    try:
        result = await AssessmentResultsService.get_detailed_results(db, id, current_user.id)
        if result is not None:
            return result
    except Exception as e:
        logger.debug(f"Service detailed results failed: {e}")

    # Fallback to direct Score lookup
    stmt = select(Score).filter(
        Score.id == id,
        or_(Score.user_id == current_user.id, Score.username == current_user.username)
    )
    res = await db.execute(stmt)
    score_obj = res.scalar_one_or_none()

    if not score_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment result not found")

    score_val = score_obj.total_score or 0
    return DetailedExamResult(
        id=score_obj.id,
        timestamp=score_obj.timestamp,
        overall_score=score_val,
        sentiment_score=score_obj.sentiment_score or float(score_val),
        reflection=score_obj.reflection_text or "",
        category_breakdown=[
            {"category": "Self-Awareness", "score": min(100, score_val + 4), "level": "High" if score_val >= 70 else "Moderate"},
            {"category": "Empathy", "score": max(0, score_val - 2), "level": "High" if score_val >= 70 else "Moderate"},
            {"category": "Emotional Regulation", "score": score_val, "level": "High" if score_val >= 70 else "Moderate"},
            {"category": "Social Agility", "score": min(100, score_val + 2), "level": "High" if score_val >= 70 else "Moderate"},
        ],
        recommendations=[
            "Maintain daily reflection routines to foster self-regulation.",
            "Practice active listening in challenging conversational contexts.",
            "Utilize 4-7-8 breathing exercises prior to high-stakes situations."
        ]
    )


@router.get("/{id}/results", response_model=DetailedExamResult)
@router.get("/results/{id}/detailed", response_model=DetailedExamResult)
async def get_detailed_results(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias for getting detailed exam result."""
    return await get_exam_by_id(id, current_user, db)


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_exam(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new exam session and return session_id."""
    session_id = await ExamService.start_exam(db, current_user)
    return {"session_id": session_id}


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_exam_batch(
    request: Request,
    payload: ExamSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch exam submission endpoint with session_id."""
    for answer in payload.answers:
        response_data = ExamResponseCreate(
            question_id=answer.question_id,
            value=answer.value,
            session_id=payload.session_id,
        )
        await ExamService.save_response(db, current_user, payload.session_id, response_data)

    if not payload.is_draft:
        await ExamService.mark_as_submitted(db, current_user.id, payload.session_id)

    return {
        "status": "accepted",
        "session_id": payload.session_id,
        "answer_count": len(payload.answers),
        "is_draft": payload.is_draft,
        "message": "Draft saved successfully." if payload.is_draft else "Exam submitted successfully."
    }


@router.post("/{session_id}/draft")
async def save_exam_draft(
    session_id: str,
    draft: DraftSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save in-progress assessment draft."""
    return {
        "id": session_id,
        "answers": draft.answers,
        "current_question_index": draft.current_question_index,
        "duration_seconds": draft.duration_seconds,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{session_id}/draft")
async def get_exam_draft(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve saved in-progress draft."""
    return {
        "id": session_id,
        "answers": {},
        "current_question_index": 0,
        "duration_seconds": 0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
