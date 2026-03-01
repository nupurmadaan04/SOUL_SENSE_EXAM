"""Database service for assessments and questions."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from typing import List, Optional, Tuple, AsyncGenerator
from datetime import datetime
import logging
import traceback

# Import model classes from models module
from ..models import Base, Score, Response, Question, QuestionCategory

from ..config import get_settings_instance, get_settings

settings = get_settings_instance()

# Create async engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False} if settings.database_type == "sqlite" else {}
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency to get database session."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


class AssessmentService:
    """Service for managing assessments (scores)."""
    
    @staticmethod
    async def get_assessments(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> Tuple[List[Score], int]:
        """
        Get assessments with pagination and optional filters.
        When user_id is provided, results are scoped to that user only.
        """
        stmt = select(Score)
        
        # Apply filters
        if username:
            stmt = stmt.filter(Score.username == username)
        if age_group:
            stmt = stmt.filter(Score.detailed_age_group == age_group)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        assessments = result.scalars().all()
        
        return list(assessments), total
    
    @staticmethod
    async def get_assessment_by_id(db: AsyncSession, assessment_id: int) -> Optional[Score]:
        """Get a single assessment by ID."""
        stmt = select(Score).filter(Score.id == assessment_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_assessment_stats(db: AsyncSession, username: Optional[str] = None) -> dict:
        """
        Get statistical summary of assessments.
        """
        stmt = select(
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.max(Score.total_score).label('max_score'),
            func.min(Score.total_score).label('min_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        )
        
        if username:
            stmt = stmt.filter(Score.username == username)
        
        result = await db.execute(stmt)
        stats = result.first()
        
        # Get age group distribution
        age_stmt = select(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        )
        
        if username:
            age_stmt = age_stmt.filter(Score.username == username)
        
        age_stmt = age_stmt.group_by(Score.detailed_age_group)
        age_result = await db.execute(age_stmt)
        age_distribution = age_result.all()
        
        return {
            'total_assessments': stats.total if stats else 0,
            'average_score': round(stats.avg_score or 0, 2) if stats else 0,
            'highest_score': stats.max_score if stats else 0,
            'lowest_score': stats.min_score if stats else 0,
            'average_sentiment': round(stats.avg_sentiment or 0, 2) if stats else 0,
            'age_group_distribution': {
                age_group: count for age_group, count in age_distribution if age_group
            }
        }
    
    @staticmethod
    async def get_assessment_responses(db: AsyncSession, assessment_id: int) -> List[Response]:
        """Get all responses for a specific assessment."""
        stmt = select(Score).filter(Score.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            return []
        
        resp_stmt = select(Response).filter(
            Response.username == assessment.username,
            Response.timestamp == assessment.timestamp
        )
        resp_result = await db.execute(resp_stmt)
        return list(resp_result.scalars().all())


class QuestionService:
    """Service for managing questions."""
    
    @staticmethod
    async def get_questions(
        db: AsyncSession,
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
        stmt = select(Question)
        
        # Apply filters
        if active_only:
            stmt = stmt.filter(Question.is_active == 1)
        
        if category_id is not None:
            stmt = stmt.filter(Question.category_id == category_id)
        
        if min_age is not None:
            stmt = stmt.filter(Question.min_age <= min_age)
        
        if max_age is not None:
            stmt = stmt.filter(Question.max_age >= max_age)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Apply pagination
        stmt = stmt.order_by(Question.id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        questions = result.scalars().all()
        
        return list(questions), total
    
    @staticmethod
    async def get_question_by_id(db: AsyncSession, question_id: int) -> Optional[Question]:
        """Get a single question by ID."""
        stmt = select(Question).filter(Question.id == question_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_questions_by_age(
        db: AsyncSession,
        age: int,
        limit: Optional[int] = None
    ) -> List[Question]:
        """
        Get questions appropriate for a specific age.
        """
        stmt = select(Question).filter(
            Question.is_active == 1,
            Question.min_age <= age,
            Question.max_age >= age
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_random_questions(
        db: AsyncSession,
        age: int,
        count: int = 10
    ) -> List[Question]:
        """
        Get random questions appropriate for age.
        """
        stmt = select(Question).filter(
            Question.is_active == 1,
            Question.min_age <= age,
            Question.max_age >= age
        ).order_by(func.random()).limit(count)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())


class ResponseService:
    """Service for managing responses."""
    
    @staticmethod
    async def get_responses(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        username: Optional[str] = None,
        question_id: Optional[int] = None
    ) -> Tuple[List[Response], int]:
        """
        Get responses with pagination and filters.
        """
        stmt = select(Response)
        
        if username:
            stmt = stmt.filter(Response.username == username)
        if question_id:
            stmt = stmt.filter(Response.question_id == question_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Apply pagination
        stmt = stmt.order_by(Response.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        responses = result.scalars().all()
        
        return list(responses), total


# Export all services
__all__ = [
    'AssessmentService',
    'QuestionService',
    'ResponseService',
    'get_db',
    'engine',
    'AsyncSessionLocal'
]
