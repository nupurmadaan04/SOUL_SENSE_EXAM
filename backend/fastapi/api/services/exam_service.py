import logging
import uuid
from datetime import datetime, UTC
from typing import List, Tuple
from sqlalchemy.orm import Session
from ..schemas import ExamResponseCreate, ExamResultCreate
from ..root_models import User, Score, Response
from .db_service import get_db
try:
    from app.auth.crypto import EncryptionManager
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ExamService:
    """
    Service for handling Exam write operations via API.
    Uses 'Storage-First' approach: Client calculates, API validates and saves.
    """

    @staticmethod
    def start_exam(db: Session, user: User):
        """Standardizes session initiation and returns a new session_id."""
        session_id = str(uuid.uuid4())
        logger.info(f"Exam session started for {user.username}: {session_id}")
        return session_id

    @staticmethod
    def save_response(db: Session, user: User, session_id: str, data: ExamResponseCreate):
        """Saves a single question response linked to the user and session."""
        try:
            new_response = Response(
                username=user.username,
                question_id=data.question_id,
                response_value=data.value,
                age_group=data.age_group,
                session_id=session_id,
                timestamp=datetime.now(UTC).isoformat()
            )
            db.add(new_response)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save response for {user.username}: {e}")
            db.rollback()
            raise e

    @staticmethod
    def save_score(db: Session, user: User, session_id: str, data: ExamResultCreate):
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
                    # Fallback to plain text or empty depending on policy? 
                    # For now, log error and save plain (or maybe fail safe)
                    # Let's fallback to plain but log warning
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
            db.commit()
            db.refresh(new_score)
            
            logger.info(f"Exam saved for {user.username}. Score: {data.total_score}")
            return new_score
            
        except Exception as e:
            logger.error(f"Failed to save exam score for {user.username}: {e}")
            db.rollback()
            raise e

    @staticmethod
    def get_history(db: Session, user: User, skip: int = 0, limit: int = 10) -> Tuple[List[Score], int]:
        """Retrieves paginated exam history for the specified user."""
        query = db.query(Score).filter(Score.user_id == user.id)
        total = query.count()
        results = query.order_by(Score.timestamp.desc()).offset(skip).limit(limit).all()
        return results, total
