import logging
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import status
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..models import User, Score, Response, ExamSession, Question
from ..exceptions import APIException
from ..constants.errors import ErrorCode
from .db_service import get_db
from .gamification_service import GamificationService
from ..utils.db_transaction import transactional, retry_on_transient
from datetime import datetime, UTC
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..models import User, Score, Response, UserSession
from .gamification_service import GamificationService
from ..utils.db_transaction import transactional, retry_on_transient
from ..utils.race_condition_protection import with_row_lock, generate_idempotency_key
import asyncio

try:
    from .crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("api.exam")

try:
    from .crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("api.exam")

class ExamService:
    """
    Service for handling Exam write operations via API with strict business logic validation.
    """

    EXAM_DURATION_MINUTES = 60  # Maximum time allowed for an exam

    @staticmethod
    def start_exam(db: Session, user: User) -> str:
        """
        Initiates a new exam session, persists it to DB, and returns session_id.
        Prevents multiple active sessions if necessary (policy decision).
        """
        # 1. Check for existing active sessions to prevent 'multiple attempts' bypass
        # (Optional: allow resumed sessions if they haven't expired)
        active_session = db.query(ExamSession).filter(
            ExamSession.user_id == user.id,
            ExamSession.status.in_(['STARTED', 'IN_PROGRESS']),
            ExamSession.expires_at > datetime.now(UTC)
        ).first()

        if active_session:
             logger.info(f"User resumed existing exam session", extra={
                 "user_id": user.id,
                 "session_id": active_session.session_id
             })
             return active_session.session_id

        # 2. Create new session
    async def start_exam(db: AsyncSession, user: User):
        """Standardizes session initiation and returns a new session_id."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=ExamService.EXAM_DURATION_MINUTES)
        
        new_session = ExamSession(
            session_id=session_id,
            user_id=user.id,
            status='STARTED',
            started_at=now,
            expires_at=expires_at
        )
        
        try:
            db.add(new_session)
            db.commit()
            logger.info(f"New exam session created", extra={
                "user_id": user.id,
                "session_id": session_id,
                "expires_at": expires_at.isoformat()
            })
            return session_id
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create exam session: {e}")
            raise APIException(ErrorCode.INTERNAL_SERVER_ERROR, "Failed to initiate exam")

    @staticmethod
    def _get_valid_session(db: Session, user_id: int, session_id: str, allowed_statuses: List[str]) -> ExamSession:
        """Helper to fetch and validate an exam session."""
        session = db.query(ExamSession).filter(
            ExamSession.session_id == session_id
        ).first()

        if not session:
            logger.warning(f"Exam session not found: {session_id}", extra={"user_id": user_id})
            raise APIException(
                ErrorCode.WFK_SESSION_NOT_FOUND, 
                "Exam session does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if session.user_id != user_id:
            logger.warning(f"Access denied for session {session_id}", extra={"user_id": user_id, "owner_id": session.user_id})
            raise APIException(
                ErrorCode.WFK_ACCESS_DENIED, 
                "You do not have access to this session",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if session.status not in allowed_statuses:
            logger.warning(f"Invalid state transition for session {session_id}: {session.status} -> {allowed_statuses}", 
                        extra={"user_id": user_id, "current_status": session.status})
            raise APIException(
                ErrorCode.WFK_INVALID_STATE, 
                f"Invalid workflow sequence. Current status: {session.status}"
            )

        # Check for expiration (Workflow validation)
        if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            logger.warning(f"Exam session expired: {session_id}", extra={"user_id": user_id})
            session.status = 'ABANDONED'
            db.commit()
            raise APIException(
                ErrorCode.WFK_SESSION_EXPIRED, 
                "Exam session has expired. Please start a new one."
            )

        return session

    @staticmethod
    def save_response(db: Session, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response with session state validation."""
        # 1. Validate session state
        session = ExamService._get_valid_session(db, user.id, session_id, ['STARTED', 'IN_PROGRESS'])

        try:
            # 2. Update session status to IN_PROGRESS if it was STARTED
            if session.status == 'STARTED':
                session.status = 'IN_PROGRESS'

            # 3. Save the response
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response linked to the user and session."""
        try:
            # Use row-level locking to prevent concurrent duplicate submissions
            await with_row_lock(
                db,
                "responses",
                "user_id = :user_id AND question_id = :question_id",
                {"user_id": user.id, "question_id": data.question_id}
            )

            # Double-check for existing response after acquiring lock
            existing_response = await db.execute(
                select(Response).filter(
                    Response.user_id == user.id,
                    Response.question_id == data.question_id
                )
            )
            existing = existing_response.scalar_one_or_none()

            if existing:
                raise ConflictError(
                    message="Duplicate response submission",
                    details=[{
                        "field": "question_id",
                        "error": "User has already submitted a response for this question",
                        "question_id": data.question_id,
                        "existing_response_id": existing.id
                    }]
                )

            new_response = Response(
                username=user.username,
                user_id=user.id,
                question_id=data.question_id,
                response_value=data.value,
                detailed_age_group=data.age_group,
                session_id=session_id,
                timestamp=datetime.now(UTC).isoformat()
            )
            db.add(new_response)
            await db.commit()
            return True
        except IntegrityError as e:
            # Handle database constraint violations (additional safety net)
            await db.rollback()
            if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(
                    message="Duplicate response submission",
                    details=[{
                        "field": "question_id",
                        "error": "User has already submitted a response for this question",
                        "question_id": data.question_id
                    }]
                )
            else:
                logger.error(f"Database integrity error for user_id={user.id}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to save response for user_id={user.id}: {e}")
            await db.rollback()
            raise e

    @staticmethod
    @retry_on_transient(retries=3)
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate):
        """
        Saves the final exam score with strict state checking.
        Requires session to be in 'SUBMITTED' state (via /api/v1/exams/submit).
        Saves the final exam score atomically together with gamification updates.

        Uses row-level locking and enhanced transaction handling to prevent:
        - Duplicate score submissions
        - Concurrent score miscalculations
        - Inconsistent gamification state
        """
        # 1. Validate session state (Must be SUBMITTED before scoring allowed)
        session = ExamService._get_valid_session(db, user.id, session_id, ['SUBMITTED'])

        try:
            # Check for Replay Attack (Already completed)
            if session.completed_at:
                raise APIException(ErrorCode.WFK_REPLAY_ATTACK, "Exam score already recorded")
            # Use row-level locking on user_session to prevent concurrent score submissions
            await with_row_lock(
                db,
                "user_sessions",
                "session_id = :session_id AND user_id = :user_id",
                {"session_id": session_id, "user_id": user.id}
            )

            # Check if score already exists for this session
            existing_score_stmt = select(Score).filter(
                Score.session_id == session_id,
                Score.user_id == user.id
            )
            existing_score_result = await db.execute(existing_score_stmt)
            existing_score = existing_score_result.scalar_one_or_none()

            if existing_score:
                logger.warning(f"Duplicate score submission attempt for session {session_id}, user {user.id}")
                raise ConflictError(
                    message="Score already submitted for this exam session",
                    details=[{
                        "field": "session_id",
                        "error": "A score has already been recorded for this exam session",
                        "session_id": session_id,
                        "existing_score_id": existing_score.id
                    }]
                )

            # Validate that all questions have been answered
            ExamService._validate_complete_responses(db, user, session_id, data.age)

            # Encrypt reflection text for privacy
            reflection = data.reflection_text
            if CRYPTO_AVAILABLE and reflection:
                try:
                    reflection = EncryptionManager.encrypt(reflection)
                except Exception as ce:
                    logger.error(f"Encryption failed for reflection: {ce}")

            # ── ATOMIC WRITE ─────────────────────────────────────────────────
            with transactional(db):
            # ── ATOMIC SCORE + GAMIFICATION WRITE ─────────────────────────────
            # All operations must succeed together to prevent inconsistent state
            async with db.begin():  # Use async transaction context manager
                new_score = Score(
                    username=user.username,
                    user_id=user.id,
                    age=data.age,
                    total_score=data.total_score,
                    sentiment_score=data.sentiment_score,
                    reflection_text=reflection,
                    is_rushed=data.is_rushed,
                    is_inconsistent=data.is_inconsistent,
                    timestamp=datetime.now(UTC).isoformat(),
                    detailed_age_group=data.detailed_age_group,
                    session_id=session_id
                )
                db.add(new_score)
                db.flush()

                # Update session state
                session.status = 'COMPLETED'
                session.completed_at = datetime.now(UTC)
                await db.flush()  # Assign new_score.id before gamification

                # Execute gamification updates atomically
                try:
                    await GamificationService.award_xp(db, user.id, 100, "Assessment completion")
                    await GamificationService.update_streak(db, user.id, "assessment")
                    await GamificationService.check_achievements(db, user.id, "assessment")
                except Exception as ge:
                    logger.error(f"Gamification update failed for user_id={user.id}: {ge}")
                    # Don't fail the entire transaction for gamification errors
                    # The score is still valid, gamification can be retried separately

                await db.refresh(new_score)
            # ─────────────────────────────────────────────────────────────────

            logger.info(f"Exam completed successfully", extra={
            logger.info(f"Exam score saved successfully", extra={
                "user_id": user.id,
                "session_id": session_id,
                "score": data.total_score
            })
            return new_score

        except Exception as e:
            if not isinstance(e, APIException):
                logger.error(f"Failed to save exam score", extra={
                    "user_id": user.id,
                    "session_id": session_id,
                    "error": str(e)
                }, exc_info=True)
            raise e

    @staticmethod
    def mark_as_submitted(db: Session, user_id: int, session_id: str):
        """Transitions a session to SUBMITTED state."""
        session = ExamService._get_valid_session(db, user_id, session_id, ['STARTED', 'IN_PROGRESS'])
        session.status = 'SUBMITTED'
        session.submitted_at = datetime.now(UTC)
        db.commit()
        logger.info(f"Exam session marked as SUBMITTED", extra={"user_id": user_id, "session_id": session_id})

    @staticmethod
    def get_history(db: Session, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
        """Retrieves paginated exam history for the specified user."""
        limit = min(limit, 100)
        query = db.query(Score).filter(Score.user_id == user.id)
        total = query.count()
        results = query.order_by(Score.timestamp.desc()).offset(skip).limit(limit).all()
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10):
        """Retrieves paginated exam history for the specified user."""
        limit = min(limit, 100)  # Guard: cap at 100 to prevent unbounded queries
        
        # Count total
        count_stmt = select(func.count(Score.id)).join(UserSession, Score.session_id == UserSession.session_id).filter(UserSession.user_id == user.id)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0
        
        # Get results
        stmt = select(Score).join(UserSession, Score.session_id == UserSession.session_id).filter(UserSession.user_id == user.id).order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        results = list(result.scalars().all())
        
        return results, total
