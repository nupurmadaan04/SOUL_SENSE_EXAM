"""API router for exam write operations."""
import logging
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
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
from ..models import User
from app.core import NotFoundError, InternalServerError, ValidationError
from ..utils.race_condition_protection import check_idempotency, complete_idempotency

logger = logging.getLogger(__name__)

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


@router.post("/submit", status_code=201)
async def submit_exam(
    request: Request,
    payload: ExamSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch exam submission endpoint — the primary write path for POST /api/v1/exams/submit.

    Uses idempotency keys to prevent duplicate submissions from concurrent requests.

    Two-layer validation is applied before any ML/scoring logic executes:

    Layer 1 – Pydantic model_validator (schema level, synchronous):
        ExamSubmit.check_question_uniqueness fires automatically during request
        parsing.  Any payload with duplicate question_id values is rejected with
        an HTTP 422 Unprocessable Entity before this function body is reached.

    Layer 2 – Router-level completeness check (async DB lookup):
        Unless is_draft=True, the submitted answer count must equal the total
        number of active questions in the database.  Incomplete submissions
        (e.g. only 3 answers for a 20-question exam) are rejected with HTTP 422.

    Draft safety:
        If is_draft=True the completeness gate is skipped entirely so that
        in-progress "Save Draft" payloads are accepted.  Duplicate detection
        is still enforced for drafts because duplicate IDs are always a
        structural error.
    """
    # Check for idempotency to prevent duplicate submissions
    cached_response = await check_idempotency(request, "exam_submit", ttl_seconds=600)  # 10 minutes
    if cached_response:
        logger.info(f"Returning cached exam submission response for user {current_user.id}")
        return cached_response

    try:
        # ------------------------------------------------------------------
        # Layer 2: Completeness validation — DB lookup to get expected count
        # ------------------------------------------------------------------
        if not payload.is_draft:
            expected_count: int = (
                db.query(Question)
                .filter(Question.is_active == 1)
                .count()
            )

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
                        "message": (
                            f"Submission is incomplete. Expected {expected_count} answers "
                            f"but received {submitted_count}. "
                            "Submit all answers or set is_draft=true to save a draft."
                        ),
                        "submitted": submitted_count,
                        "expected": expected_count,
                    },
                )

        # ------------------------------------------------------------------
        # Persist each individual response linked to the session
        # ------------------------------------------------------------------
        for answer in payload.answers:
            response_data = ExamResponseCreate(
                question_id=answer.question_id,
                value=answer.value,
                session_id=payload.session_id,
            )
            ExamService.save_response(db, current_user, payload.session_id, response_data)

        response_data = {
            "status": "accepted",
            "session_id": payload.session_id,
            "answer_count": len(payload.answers),
            "is_draft": payload.is_draft,
            "message": (
                "Draft saved. Submit with is_draft=false to score your exam."
                if payload.is_draft
                else "Exam submitted successfully. Proceed to /complete to record your score."
            ),
        }

        # Cache the successful response for idempotency
        await complete_idempotency(request, str(response_data))

        logger.info(
            "Batch exam submission accepted",
            extra={
                "user_id": current_user.id,
                "session_id": payload.session_id,
                "answer_count": len(payload.answers),
                "is_draft": payload.is_draft,
            },
        )

        return response_data

    except Exception as e:
        logger.error(
            "Failed to persist exam responses during batch submit",
            extra={
                "user_id": current_user.id,
                "session_id": payload.session_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to persist exam responses.")

    logger.info(
        "Batch exam submission accepted",
        extra={
            "user_id": current_user.id,
            "session_id": payload.session_id,
            "answer_count": len(payload.answers),
            "is_draft": payload.is_draft,
        },
    )

    # ------------------------------------------------------------------
    # Mark session as SUBMITTED if not a draft
    # ------------------------------------------------------------------
    if not payload.is_draft:
        ExamService.mark_as_submitted(db, current_user.id, payload.session_id)

    return {
        "status": "accepted",
        "session_id": payload.session_id,
        "answer_count": len(payload.answers),
        "is_draft": payload.is_draft,
        "message": (
            "Draft saved. Submit with is_draft=false to score your exam."
            if payload.is_draft
            else "Exam submitted successfully. Proceed to /complete to record your score."
        ),
    }


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
    request: Request,
    session_id: str,
    result_data: ExamResultCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a completed exam score linked to session.

    Uses idempotency to prevent duplicate score submissions.
    """
    # Check for idempotency to prevent duplicate score submissions
    cached_response = await check_idempotency(request, "exam_complete", ttl_seconds=3600)  # 1 hour
    if cached_response:
        logger.info(f"Returning cached exam completion response for user {current_user.id}")
        return cached_response

    try:
        score = await ExamService.save_score(db, current_user, session_id, result_data)
        response_data = AssessmentResponse.model_validate(score)

        # Cache the successful response for idempotency
        await complete_idempotency(request, response_data.model_dump_json())

        return response_data
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
        assessments, total = ExamService.get_history(db, current_user, skip, page_size)

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
            )
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
