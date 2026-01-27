"""Database service for assessments and questions."""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, Tuple
from datetime import datetime

# Import model classes from root_models module (handles namespace collision)
from app.root_models import Base, Score, Response, Question, QuestionCategory

from ..config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_type == "sqlite" else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AssessmentService:
    """Service for managing assessments (scores)."""
    
    @staticmethod
    def get_assessments(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        username: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> Tuple[List[Score], int]:
        """
        Get assessments with pagination and optional filters.
        """
        query = db.query(Score)
        
        # Apply filters
        if username:
            query = query.filter(Score.username == username)
        if age_group:
            query = query.filter(Score.detailed_age_group == age_group)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        assessments = query.order_by(Score.timestamp.desc()).offset(skip).limit(limit).all()
        
        return assessments, total
    
    @staticmethod
    def get_assessment_by_id(db: Session, assessment_id: int) -> Optional[Score]:
        """Get a single assessment by ID."""
        return db.query(Score).filter(Score.id == assessment_id).first()
    
    @staticmethod
    def get_assessment_stats(db: Session, username: Optional[str] = None) -> dict:
        """
        Get statistical summary of assessments.
        """
        query = db.query(Score)
        
        if username:
            query = query.filter(Score.username == username)
        
        # Calculate statistics
        stats = query.with_entities(
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.max(Score.total_score).label('max_score'),
            func.min(Score.total_score).label('min_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        ).first()
        
        # Get age group distribution
        age_distribution = db.query(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        )
        
        if username:
            age_distribution = age_distribution.filter(Score.username == username)
        
        age_distribution = age_distribution.group_by(Score.detailed_age_group).all()
        
        return {
            'total_assessments': stats.total or 0,
            'average_score': round(stats.avg_score or 0, 2),
            'highest_score': stats.max_score or 0,
            'lowest_score': stats.min_score or 0,
            'average_sentiment': round(stats.avg_sentiment or 0, 2),
            'age_group_distribution': {
                age_group: count for age_group, count in age_distribution if age_group
            }
        }
    
    @staticmethod
    def get_assessment_responses(db: Session, assessment_id: int) -> List[Response]:
        """Get all responses for a specific assessment."""
        assessment = db.query(Score).filter(Score.id == assessment_id).first()
        if not assessment:
            return []
        
        return db.query(Response).filter(
            Response.username == assessment.username,
            Response.timestamp == assessment.timestamp
        ).all()


class QuestionService:
    """Service for managing questions."""
    
    @staticmethod
    def get_questions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        category_id: Optional[int] = None,
        active_only: bool = True
    ) -> Tuple[List[Question], int]:
        """
        Get questions with pagination and filters.
        """
        query = db.query(Question)
        
        # Apply filters
        if active_only:
            query = query.filter(Question.is_active == 1)
        
        if category_id is not None:
            query = query.filter(Question.category_id == category_id)
        
        if min_age is not None:
            query = query.filter(Question.min_age <= min_age)
        
        if max_age is not None:
            query = query.filter(Question.max_age >= max_age)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        questions = query.order_by(Question.id).offset(skip).limit(limit).all()
        
        return questions, total
    
    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
        """Get a single question by ID."""
        return db.query(Question).filter(Question.id == question_id).first()
    
    @staticmethod
    def get_questions_by_age(
        db: Session,
        age: int,
        limit: Optional[int] = None
    ) -> List[Question]:
        """
        Get questions appropriate for a specific age.
        """
        query = db.query(Question).filter(
            Question.is_active == 1,
            Question.min_age <= age,
            Question.max_age >= age
        ).order_by(Question.id)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_categories(db: Session) -> List[QuestionCategory]:
        """Get all question categories."""
        return db.query(QuestionCategory).order_by(QuestionCategory.id).all()
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Optional[QuestionCategory]:
        """Get a category by ID."""
        return db.query(QuestionCategory).filter(QuestionCategory.id == category_id).first()
