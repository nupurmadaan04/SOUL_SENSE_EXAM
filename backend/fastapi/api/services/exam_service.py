import logging
import uuid
from datetime import datetime, UTC, timedelta
from typing import List, Tuple, Optional
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

    @staticmethod
    async def start_exam(db: AsyncSession, user: User) -> str:
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
        
        db.add(new_session)
        await db.commit()
        logger.info(f"New exam session created: {session_id} for user {user.id}")
        return session_id

    @staticmethod
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
        count_stmt = select(func.count(Score.id)).filter(Score.user_id == user.id)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0
        
        stmt = select(Score).filter(Score.user_id == user.id).order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        results = list(result.scalars().all())
        return results, total
