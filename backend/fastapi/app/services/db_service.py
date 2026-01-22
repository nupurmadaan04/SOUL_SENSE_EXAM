"""Database service for assessments and questions."""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, Tuple
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path to import models
import os
import importlib.util

# Get absolute path to SOUL_SENSE_EXAM/app/models.py
current_dir = os.path.dirname(__file__)
models_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..', 'app', 'models.py'))

# Load the models module
spec = importlib.util.spec_from_file_location("app.models", models_path)
models_module = importlib.util.module_from_spec(spec)
sys.modules['app.models'] = models_module
spec.loader.exec_module(models_module)

# Import the classes we need
Base = models_module.Base
Score = models_module.Score
Response = models_module.Response
Question = models_module.Question
QuestionCategory = models_module.QuestionCategory
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
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            username: Optional username filter
            age_group: Optional age group filter
            
        Returns:
            Tuple of (list of scores, total count)
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
        
        Args:
            db: Database session
            username: Optional username to filter stats
            
        Returns:
            Dictionary with statistical information
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
        # Get the assessment to find username and timestamp
        assessment = db.query(Score).filter(Score.id == assessment_id).first()
        if not assessment:
            return []
        
        # Get responses for this user around the same time
        # Since we don't have a direct link, we match by username and timestamp proximity
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
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            min_age: Filter questions suitable for this minimum age
            max_age: Filter questions suitable for this maximum age
            category_id: Filter by category
            active_only: Only return active questions
            
        Returns:
            Tuple of (list of questions, total count)
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
        
        Args:
            db: Database session
            age: User's age
            limit: Optional limit on number of questions
            
        Returns:
            List of questions
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
