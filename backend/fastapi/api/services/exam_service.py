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

try:
    from .crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("api.exam")

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update

class ExamService:
    """
    Service for handling Exam write operations via API with strict business logic validation (Async).
    """

    EXAM_DURATION_MINUTES = 60

    @staticmethod
    async def start_exam(db: AsyncSession, user: User) -> str:
        """
        Initiates a new exam session (Async).
        """
        # 1. Check for existing active sessions
        stmt = select(ExamSession).filter(
            ExamSession.user_id == user.id,
            ExamSession.status.in_(['STARTED', 'IN_PROGRESS']),
            ExamSession.expires_at > datetime.now(UTC)
        )
        result = await db.execute(stmt)
        active_session = result.scalar_one_or_none()

        if active_session:
             logger.info(f"User resumed existing exam session", extra={
                 "user_id": user.id,
                 "session_id": active_session.session_id
             })
             return active_session.session_id

        # 2. Create new session
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
            await db.commit()
            logger.info(f"New exam session created", extra={
                "user_id": user.id,
                "session_id": session_id,
                "expires_at": expires_at.isoformat()
            })
            return session_id
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create exam session: {e}")
            raise APIException(ErrorCode.INTERNAL_SERVER_ERROR, "Failed to initiate exam")

    @staticmethod
    async def _get_valid_session(db: AsyncSession, user_id: int, session_id: str, allowed_statuses: List[str]) -> ExamSession:
        """Helper to fetch and validate an exam session (Async)."""
        stmt = select(ExamSession).filter(ExamSession.session_id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

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

        # Check for expiration
        if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            logger.warning(f"Exam session expired: {session_id}", extra={"user_id": user_id})
            session.status = 'ABANDONED'
            await db.commit()
            raise APIException(
                ErrorCode.WFK_SESSION_EXPIRED, 
                "Exam session has expired. Please start a new one."
            )

        return session

    @staticmethod
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response (Async)."""
        session = await ExamService._get_valid_session(db, user.id, session_id, ['STARTED', 'IN_PROGRESS'])

        try:
            if session.status == 'STARTED':
                session.status = 'IN_PROGRESS'

            new_response = Response(
                username=user.username,
                user_id=user.id,
                question_id=data.question_id,
                response_value=data.value,
                age_group=data.age_group,
                session_id=session_id,
                timestamp=datetime.now(UTC).isoformat()
            )
            db.add(new_response)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save response", extra={
                "user_id": user.id,
                "session_id": session_id,
                "question_id": data.question_id,
                "error": str(e)
            }, exc_info=True)
            raise e

    @staticmethod
    @retry_on_transient(retries=3)
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate):
        """Saves final exam score (Async)."""
        session = await ExamService._get_valid_session(db, user.id, session_id, ['SUBMITTED'])

        try:
            if session.completed_at:
                raise APIException(ErrorCode.WFK_REPLAY_ATTACK, "Exam score already recorded")

            reflection = data.reflection_text
            if CRYPTO_AVAILABLE and reflection:
                try:
                    reflection = EncryptionManager.encrypt(reflection)
                except Exception as ce:
                    logger.error(f"Encryption failed for reflection: {ce}")

            async with transactional(db) as tx_session:
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
                tx_session.add(new_score)
                await tx_session.flush()

                session.status = 'COMPLETED'
                session.completed_at = datetime.now(UTC)

                await GamificationService.award_xp(tx_session, user.id, 100, "Assessment completion")
                await GamificationService.update_streak(tx_session, user.id, "assessment")
                await GamificationService.check_achievements(tx_session, user.id, "assessment")

            await db.refresh(new_score)
            return new_score

        except Exception as e:
            if not isinstance(e, APIException):
                logger.error(f"Failed to save exam score: {e}")
            raise e

    @staticmethod
    async def mark_as_submitted(db: AsyncSession, user_id: int, session_id: str):
        """Transitions a session to SUBMITTED state (Async)."""
        session = await ExamService._get_valid_session(db, user_id, session_id, ['STARTED', 'IN_PROGRESS'])
        session.status = 'SUBMITTED'
        session.submitted_at = datetime.now(UTC)
        await db.commit()

    @staticmethod
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
        """Retrieves paginated history for user (Async)."""
        limit = min(limit, 100)
        stmt = select(Score).filter(Score.user_id == user.id)
        
        # Get count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Paginate
        stmt = stmt.order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total
