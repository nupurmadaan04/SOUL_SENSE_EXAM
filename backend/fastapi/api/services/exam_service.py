import logging
import uuid
from datetime import datetime, UTC
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..models import User, Score, Response, UserSession
from .gamification_service import GamificationService
import asyncio

try:
    from .crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("api.exam")

class ExamService:
    """
    Service for handling Exam write operations via API.
    Uses 'Storage-First' approach: Client calculates, API validates and saves.
    """

    @staticmethod
    async def start_exam(db: AsyncSession, user: User):
        """Standardizes session initiation and returns a new session_id."""
        session_id = str(uuid.uuid4())
        logger.info(f"Exam session started", extra={
            "user_id": user.id,
            "session_id": session_id
        })
        return session_id

    @staticmethod
    async def save_response(db: AsyncSession, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response linked to the user and session."""
        try:
            # Check if user has already answered this question
            existing_response = db.query(Response).filter(
                Response.user_id == user.id,
                Response.question_id == data.question_id
            ).first()
            
            if existing_response:
                raise ConflictError(
                    message="Duplicate response submission",
                    details=[{
                        "field": "question_id",
                        "error": "User has already submitted a response for this question",
                        "question_id": data.question_id,
                        "existing_response_id": existing_response.id
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
            db.rollback()
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
    async def save_score(db: AsyncSession, user: User, session_id: str, data: ExamResultCreate):
        """
        Saves the final exam score.
        Validates that all questions have been answered before saving.
        Encrypts reflection_text if crypto is available.
        """
        try:
            # Validate that all questions have been answered
            ExamService._validate_complete_responses(db, user, session_id, data.age)
            
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
            
            # Trigger Gamification
            try:
                await GamificationService.award_xp(db, user.id, 100, "Assessment completion")
                await GamificationService.update_streak(db, user.id, "assessment")
                await GamificationService.check_achievements(db, user.id, "assessment")
            except Exception as e:
                logger.error(f"Gamification update failed for user_id={user.id}: {e}")

            logger.info(f"Exam saved successfully", extra={
                "user_id": user.id,
                "session_id": session_id,
                "score": data.total_score,
                "sentiment_score": data.sentiment_score
            })
            return new_score
            
        except Exception as e:
            logger.error(f"Failed to save exam score for user_id={user.id}: {e}")
            await db.rollback()
            raise e

    @staticmethod
    async def get_history(db: AsyncSession, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
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
