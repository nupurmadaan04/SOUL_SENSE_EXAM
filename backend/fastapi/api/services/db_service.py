"""Database service for assessments and questions (Async Version)."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import List, Optional, Tuple
from datetime import datetime

# Import model classes from root_models module (handles namespace collision)
from ..root_models import Base, Score, Response, Question, QuestionCategory

from ..config import get_settings

settings = get_settings()

# Update database URL for asyncpg if it's postgresql
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("sqlite:///"):
    # SQLite async requires aiosqlite
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

# Create engine
engine = create_async_engine(
    db_url,
    connect_args={"check_same_thread": False} if settings.database_type == "sqlite" else {}
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    """Dependency to get database session."""
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
        username: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> Tuple[List[Score], int]:
        """
        Get assessments with pagination and optional filters.
        """
        query = select(Score)
        
        # Apply filters
        if username:
            query = query.filter(Score.username == username)
        if age_group:
            query = query.filter(Score.detailed_age_group == age_group)
        
        # Get total count (using a separate query for count in async)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Apply pagination and ordering
        query = query.order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        assessments = result.scalars().all()
        
        return assessments, total
    
    @staticmethod
    async def get_assessment_by_id(db: AsyncSession, assessment_id: int) -> Optional[Score]:
        """Get a single assessment by ID."""
        result = await db.execute(select(Score).filter(Score.id == assessment_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_assessment_stats(db: AsyncSession, username: Optional[str] = None) -> dict:
        """
        Get statistical summary of assessments.
        """
        stats_query = select(
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.max(Score.total_score).label('max_score'),
            func.min(Score.total_score).label('min_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        )
        
        if username:
            stats_query = stats_query.filter(Score.username == username)
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        # Get age group distribution
        age_dist_query = select(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        )
        
        if username:
            age_dist_query = age_dist_query.filter(Score.username == username)
        
        age_dist_query = age_dist_query.group_by(Score.detailed_age_group)
        age_dist_result = await db.execute(age_dist_query)
        age_distribution = age_dist_result.all()
        
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
    async def get_assessment_responses(db: AsyncSession, assessment_id: int) -> List[Response]:
        """Get all responses for a specific assessment."""
        assessment_result = await db.execute(select(Score).filter(Score.id == assessment_id))
        assessment = assessment_result.scalar_one_or_none()
        if not assessment:
            return []
        
        responses_result = await db.execute(
            select(Response).filter(
                Response.username == assessment.username,
                Response.timestamp == assessment.timestamp
            )
        )
        return responses_result.scalars().all()


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
        query = select(Question)
        
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
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        
        # Apply pagination
        query = query.order_by(Question.id).offset(skip).limit(limit)
        result = await db.execute(query)
        questions = result.scalars().all()
        
        return questions, total
    
    @staticmethod
    async def get_question_by_id(db: AsyncSession, question_id: int) -> Optional[Question]:
        """Get a single question by ID."""
        result = await db.execute(select(Question).filter(Question.id == question_id))
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
        query = select(Question).filter(
            Question.is_active == 1,
            Question.min_age <= age,
            Question.max_age >= age
        ).order_by(Question.id)
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_categories(db: AsyncSession) -> List[QuestionCategory]:
        """Get all question categories."""
        result = await db.execute(select(QuestionCategory).order_by(QuestionCategory.id))
        return result.scalars().all()
    
    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[QuestionCategory]:
        """Get a category by ID."""
        result = await db.execute(select(QuestionCategory).filter(QuestionCategory.id == category_id))
        return result.scalar_one_or_none()
