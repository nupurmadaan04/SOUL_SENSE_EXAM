import logging
import uuid
from datetime import datetime, UTC
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..root_models import User, Score, Response
from .db_service import get_db
from .gamification_service import GamificationService
try:
    from app.auth.crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ExamService:
    """
    Service for handling Exam write operations via API (Async).
    Uses 'Storage-First' approach: Client calculates, API validates and saves.
    """

    @staticmethod
    async def start_exam(db: AsyncSession, user: User):
        """Standardizes session initiation and returns a new session_id."""
        session_id = str(uuid.uuid4())
        logger.info(f"Exam session started for user_id={user.id}: {session_id}")
        return session_id

    @staticmethod
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response linked to the user and session."""
        try:
            new_response = Response(
                username=user.username,
                question_id=data.question_id,
                response_value=data.value,
                detailed_age_group=getattr(data, "age_group", None), # Usegetattr for safety
                session_id=session_id,
                timestamp=datetime.now(UTC).isoformat()
            )
            db.add(new_response)
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save response for user_id={user.id}: {e}")
            await db.rollback()
            raise e

    @staticmethod
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate):
        """
        Saves the final exam score.
        Encrypts reflection_text if crypto is available.
        """
        try:
            # Encrypt reflection text for privacy
            reflection = data.reflection_text
            if CRYPTO_AVAILABLE and reflection:
                try:
                    reflection = EncryptionManager.encrypt(reflection)
                except Exception as ce:
                    logger.error(f"Encryption failed for reflection: {ce}")
                    pass

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
            await db.commit()
            await db.refresh(new_score)
            
            # Trigger Gamification (Assuming these are also made async)
            try:
                await GamificationService.award_xp(db, user.id, 100, "Assessment completion")
                await GamificationService.update_streak(db, user.id, "assessment")
                await GamificationService.check_achievements(db, user.id, "assessment")
            except Exception as e:
                logger.error(f"Gamification update failed for user_id={user.id}: {e}")

            logger.info(f"Exam saved for user_id={user.id}. Score: {data.total_score}")
            return new_score
            
        except Exception as e:
            logger.error(f"Failed to save exam score for user_id={user.id}: {e}")
            await db.rollback()
            raise e

    @staticmethod
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
        """Retrieves paginated exam history for the specified user."""
        limit = min(limit, 100)
        query = select(Score).filter(Score.user_id == user.id)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get results
        query = query.order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        results = result.scalars().all()
        
        return results, total
