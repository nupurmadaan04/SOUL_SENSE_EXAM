import time
import statistics
import logging
from datetime import datetime, UTC
from typing import List, Tuple, Optional, Any
from sqlalchemy import desc
from app.db import safe_db_context
from app.models import Score, Response, User, AssessmentResult
from app.exceptions import DatabaseError

# Try importing NLTK sentiment analyzer
try:
    from nltk.sentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None

logger = logging.getLogger(__name__)

class ExamService:
    """
    Service layer for Exam interactions.
    Handles all Database operations for Exams and Scores.
    """
    
    @staticmethod
    def get_assessment_results(
        user_id: int, 
        result_ids: Optional[List[int]] = None, 
        minutes_lookback: int = 15
    ) -> List[AssessmentResult]:
        """
        Fetches assessment results for deep dive insights.
        Args:
            user_id: The ID of the user
            result_ids: Optional list of specific result IDs to fetch
            minutes_lookback: If no IDs provided, fetch results from last N minutes
        """
        try:
            with safe_db_context() as session:
                session.expire_on_commit = False
                query = session.query(AssessmentResult).filter(AssessmentResult.user_id == user_id)
                
                if result_ids:
                    query = query.filter(AssessmentResult.id.in_(result_ids))
                else:
                    # Fallback to recent results
                    # Timestamp in model is String (ISO format), so we need strict string comparison or conversion
                    # The UI used datetime.now().timestamp() - 900 (15 mins) and compared.
                    # Model stores string.
                    from datetime import timedelta
                    cutoff = (datetime.now(UTC) - timedelta(minutes=minutes_lookback)).isoformat()
                    query = query.filter(AssessmentResult.timestamp >= cutoff)
                
                return query.order_by(desc(AssessmentResult.timestamp)).all()
        except Exception as e:
            logger.error(f"Failed to fetch assessment results: {e}")
            return []

    @staticmethod
    def save_score(
        username: str,
        age: int,
        age_group: str,
        score: int,
        sentiment_score: float,
        reflection_text: str,
        is_rushed: bool,
        is_inconsistent: bool,
        detailed_age_group: str
    ) -> bool:
        """Saves a completed exam score to the database."""
        try:
            timestamp = datetime.now(UTC).isoformat()
            
            with safe_db_context() as session:
                # Resolve User ID
                user = session.query(User).filter_by(username=username).first()
                user_id = user.id if user else None
                
                new_score = Score(
                    username=username,
                    user_id=user_id,
                    age=age,
                    total_score=score,
                    sentiment_score=sentiment_score,
                    reflection_text=reflection_text,
                    is_rushed=is_rushed,
                    is_inconsistent=is_inconsistent,
                    timestamp=timestamp,
                    detailed_age_group=detailed_age_group
                )
                session.add(new_score)
                # Commit handled by context
                
            logger.info(f"Exam saved. Score: {score}, User: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save exam score: {e}", exc_info=True)
            return False

    @staticmethod
    def save_response(
        username: str,
        question_id: int,
        value: int,
        age_group: str
    ) -> None:
        """Saves a single question response."""
        try:
            with safe_db_context() as session:
                # users = session.query(User).filter_by(username=username).first()
                # user_id = users.id if users else None
                # Response model technically has user_id but we might not query it every single click for performance.
                # Just saving username/question info is usually sufficient for analytics unless linked.
                
                resp = Response(
                    username=username,
                    question_id=question_id,
                    response_value=value,
                    age_group=age_group,
                    timestamp=datetime.now(UTC).isoformat()
                )
                session.add(resp)
        except Exception as e:
            logger.error(f"Failed to save response: {e}")

    @staticmethod
    def get_recent_scores(username: str, limit: int = 10) -> List[int]:
        """Fetches recent total scores for consistency checks."""
        try:
            with safe_db_context() as session:
                scores = session.query(Score.total_score)\
                    .filter_by(username=username)\
                    .order_by(desc(Score.timestamp))\
                    .limit(limit)\
                    .all()
                return [s[0] for s in scores]
        except Exception as e:
            logger.warning(f"Failed to fetch recent scores: {e}")
            return []


class ExamSession:
    """
    Core engine for the Exam functionality.
    Manages state, timing, scoring, and persistence via ExamService.
    """

    def __init__(self, username: str, age: int, age_group: str, questions: List[Tuple[Any, ...]]) -> None:
        self.username = username
        self.age = age
        self.age_group = age_group
        self.questions = questions
        
        # State
        self.current_question_index = 0
        self.responses: List[int] = []
        self.response_times: List[float] = []
        
        # Timing
        self.question_start_time: Optional[float] = None
        
        # Results
        self.score = 0
        self.sentiment_score = 0.0
        self.reflection_text = ""
        self.is_rushed = False
        self.is_inconsistent = False

    def start_exam(self) -> None:
        """Initialize or reset exam state"""
        self.current_question_index = 0
        self.responses = []
        self.response_times = []
        self.score = 0
        self.sentiment_score = 0.0
        self.reflection_text = ""
        self.start_question_timer()
        logger.info(f"Exam session started for user: {self.username}")

    def start_question_timer(self) -> None:
        """Mark the start time for the current question"""
        self.question_start_time = time.time()

    def get_current_question(self) -> Optional[Tuple[str, Optional[str]]]:
        """Return (text, tooltip) for current question or None."""
        if self.current_question_index >= len(self.questions):
            return None
            
        q_data = self.questions[self.current_question_index]
        
        # Format 1: (id, text, tooltip, min, max) -> DB
        if len(q_data) >= 3 and isinstance(q_data[0], int):
             return (q_data[1], q_data[2])
        # Format 2: (text, tooltip)
        elif isinstance(q_data, tuple):
            return (q_data[0], q_data[1] if len(q_data) > 1 else None)
        else:
            return (str(q_data), None)

    def submit_answer(self, value: int) -> None:
        """Submit answer (1-4) and advance."""
        if not (1 <= value <= 4):
            raise ValueError("Answer must be between 1 and 4")

        # Record metrics
        duration = 0.0
        if self.question_start_time:
            duration = time.time() - self.question_start_time
        
        if self.current_question_index < len(self.responses):
            self.responses[self.current_question_index] = value
            self.response_times[self.current_question_index] = duration
        else:
            self.responses.append(value)
            self.response_times.append(duration)
            
        # Async/Fire-and-forget save to DB
        self._save_response_to_db(value)

        # Advance
        self.current_question_index += 1
        self.start_question_timer()

    def go_back(self):
        """Return to previous question"""
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.start_question_timer()
            return True
        return False

    def get_progress(self) -> Tuple[int, int, float]:
        """Return (current, total, percentage)"""
        total = len(self.questions)
        pct = (self.current_question_index / total * 100) if total > 0 else 0
        return (self.current_question_index + 1, total, pct)

    def is_finished(self) -> bool:
        return self.current_question_index >= len(self.questions)

    def submit_reflection(self, text: str, analyzer: Any = None):
        """Analyze reflection text sentiment."""
        self.reflection_text = text.strip()
        
        if not self.reflection_text:
            self.sentiment_score = 0.0
            return

        try:
            sia = analyzer
            if not sia and SentimentIntensityAnalyzer:
                sia = SentimentIntensityAnalyzer()
            
            if sia:
                scores = sia.polarity_scores(self.reflection_text)
                self.sentiment_score = scores['compound'] * 100
            else:
                self.sentiment_score = 0.0
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            self.sentiment_score = 0.0

    def calculate_metrics(self):
        """Calculate score and behavioral metrics."""
        self.score = sum(self.responses)
        self.is_rushed = False
        self.is_inconsistent = False

        # 1. Rushed Detection
        if self.response_times:
            avg_time = statistics.mean(self.response_times)
            if avg_time < 2.0:
                self.is_rushed = True

        # 2. Inconsistent Detection (Internal Variance)
        if len(self.responses) > 1:
            variance = statistics.variance(self.responses)
            if variance > 2.0:
                self.is_inconsistent = True

        # 3. Inconsistent (Historical) - via Service
        past_scores = ExamService.get_recent_scores(self.username)
        if past_scores:
            avg_past = statistics.mean(past_scores)
            if avg_past > 0 and abs(self.score - avg_past) / avg_past > 0.2:
                self.is_inconsistent = True

    def finish_exam(self) -> bool:
        """Finalize exam and save via Service."""
        self.calculate_metrics()
        
        return ExamService.save_score(
            username=self.username,
            age=self.age,
            age_group=self.age_group,
            score=self.score,
            sentiment_score=self.sentiment_score,
            reflection_text=self.reflection_text,
            is_rushed=self.is_rushed,
            is_inconsistent=self.is_inconsistent,
            detailed_age_group=self.age_group
        )

    def _save_response_to_db(self, answer_value: int):
        """Helper to save single response via Service"""
        # Map index to correct ID if possible
        q_data = self.questions[self.current_question_index]
        q_id = q_data[0] if (isinstance(q_data, tuple) and isinstance(q_data[0], int)) else (self.current_question_index + 1)
        
        ExamService.save_response(self.username, q_id, answer_value, self.age_group)
