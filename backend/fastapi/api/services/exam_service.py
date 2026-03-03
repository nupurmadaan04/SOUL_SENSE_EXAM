import logging
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Tuple, Optional
<<<<<<< HEAD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, text
from sqlalchemy.exc import IntegrityError
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..models import User, Score, Response, ExamSession, Question, UserSession

logger = logging.getLogger("api.exam")

class ExamService:
    """
    Service for handling Exam operations with strict business logic validation.
    """
    EXAM_DURATION_MINUTES = 60
=======
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from fastapi import status

from ..schemas import ExamResponseCreate, ExamResultCreate
from ..models import User, Score, Response, ExamSession, Question
from ..exceptions import APIException
from ..constants.errors import ErrorCode
from .gamification_service import GamificationService
from ..utils.db_transaction import transactional, retry_on_transient
from ..utils.race_condition_protection import with_row_lock

# Mock ConflictError if not found in core, though it should be there in a proper project
try:
    from app.core import ConflictError
except ImportError:
    class ConflictError(APIException):
        def __init__(self, message, details=None):
            super().__init__(ErrorCode.BUSINESS_VIO, message, status_code=409, details=details)

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
    Service for handling Exam operations via Async API.
    Refactored for SQLAlchemy 2.0 Async reliability.
    """

    EXAM_DURATION_MINUTES = 60 
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af

    @staticmethod
    async def start_exam(db: AsyncSession, user: User) -> str:
        """Standardizes session initiation and returns a new session_id."""
<<<<<<< HEAD
=======
        # Check for existing active sessions
        stmt = select(ExamSession).filter(
            ExamSession.user_id == user.id,
            ExamSession.status.in_(['STARTED', 'IN_PROGRESS']),
            ExamSession.expires_at > datetime.now(UTC)
        )
        res = await db.execute(stmt)
        active_session = res.scalar_one_or_none()

        if active_session:
             logger.info(f"User resumed existing exam session", extra={
                 "user_id": user.id,
                 "session_id": active_session.session_id
             })
             return active_session.session_id

>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
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
        
        db.add(new_session)
        await db.commit()
        logger.info(f"New exam session created: {session_id} for user {user.id}")
        return session_id

    @staticmethod
<<<<<<< HEAD
    async def get_valid_session(db: AsyncSession, user_id: int, session_id: str, allowed_statuses: List[str]) -> ExamSession:
        result = await db.execute(select(ExamSession).filter(ExamSession.session_id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            raise Exception("Session not found")
        if session.user_id != user_id:
            raise Exception("Access denied")
        if session.status not in allowed_statuses:
            raise Exception(f"Invalid state: {session.status}")
        if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            session.status = 'ABANDONED'
            await db.commit()
            raise Exception("Session expired")
        return session

    @staticmethod
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate) -> bool:
        session = await ExamService.get_valid_session(db, user.id, session_id, ['STARTED', 'IN_PROGRESS'])
        if session.status == 'STARTED':
            session.status = 'IN_PROGRESS'
        
        new_response = Response(
            username=user.username,
            user_id=user.id,
            question_id=data.question_id,
            response_value=data.value,
            session_id=session_id,
            timestamp=datetime.now(UTC).isoformat()
        )
        db.add(new_response)
        await db.commit()
        return True

    @staticmethod
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate) -> Score:
        session = await ExamService.get_valid_session(db, user.id, session_id, ['SUBMITTED'])
        
        new_score = Score(
            username=user.username,
            user_id=user.id,
            age=data.age,
            total_score=data.total_score,
            sentiment_score=data.sentiment_score,
            reflection_text=data.reflection_text,
            is_rushed=data.is_rushed,
            is_inconsistent=data.is_inconsistent,
            timestamp=datetime.now(UTC).isoformat(),
            detailed_age_group=data.detailed_age_group,
            session_id=session_id
        )
        db.add(new_score)
        session.status = 'COMPLETED'
        session.completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(new_score)
        return new_score

    @staticmethod
    async def mark_as_submitted(db: AsyncSession, user_id: int, session_id: str):
        session = await ExamService.get_valid_session(db, user_id, session_id, ['STARTED', 'IN_PROGRESS'])
        session.status = 'SUBMITTED'
        session.submitted_at = datetime.now(UTC)
        await db.commit()

    @staticmethod
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
        limit = min(limit, 100)
=======
    async def _get_valid_session(db: AsyncSession, user_id: int, session_id: str, allowed_statuses: List[str]) -> ExamSession:
        """Helper to fetch and validate an exam session (Async)."""
        """Helper to fetch and validate an exam session."""
        stmt = select(ExamSession).filter(ExamSession.session_id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            throw_err = APIException(ErrorCode.INTERNAL_SERVER_ERROR, "Exam session does not exist", status_code=404)
            raise throw_err

        if session.user_id != user_id:
            raise APIException(ErrorCode.INTERNAL_SERVER_ERROR, "Access denied", status_code=403)

        if session.status not in allowed_statuses:
            raise APIException(ErrorCode.INTERNAL_SERVER_ERROR, f"Invalid state: {session.status}", status_code=400)

        if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            session.status = 'ABANDONED'
            await db.commit()
            raise APIException(ErrorCode.INTERNAL_SERVER_ERROR, "Session expired", status_code=400)

        return session

    @staticmethod
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response with session state validation."""
        session = await ExamService._get_valid_session(db, user.id, session_id, ['STARTED', 'IN_PROGRESS'])

        if session.status == 'STARTED':
            session.status = 'IN_PROGRESS'

        try:
            # Check for existing
            stmt = select(Response).filter(Response.user_id == user.id, Response.question_id == data.question_id, Response.session_id == session_id)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                return True # Idempotent

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
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save response: {e}")
            raise e

    @staticmethod
    @async_retry_on_transient(retries=3)
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate):
        """Saves the final exam score and updates session state."""
        session = await ExamService._get_valid_session(db, user.id, session_id, ['SUBMITTED', 'IN_PROGRESS', 'STARTED'])

        # Atomic transaction for score + gamification
        try:
            reflection = data.reflection_text
            if CRYPTO_AVAILABLE and reflection:
                reflection = EncryptionManager.encrypt(reflection)

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
            
            session.status = 'COMPLETED'
            session.completed_at = datetime.now(UTC)

            await db.flush()

            # Award XP
            await GamificationService.award_xp(db, user.id, 100, "Exam Completion")
            
            await db.commit()
            return new_score
        except Exception as e:
            await db.rollback()
            logger.error(f"Score submission failed: {e}")
            raise e

    @staticmethod
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10):
        """Retrieves paginated history."""
        stmt = select(Score).filter(Score.user_id == user.id).order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        results = res.scalars().all()
        
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
        count_stmt = select(func.count(Score.id)).filter(Score.user_id == user.id)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0
        
<<<<<<< HEAD
        stmt = select(Score).filter(Score.user_id == user.id).order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        results = list(result.scalars().all())
=======
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
        return results, total
