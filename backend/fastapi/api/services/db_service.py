"""Database service for assessments and questions (Async Version)."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import func, select, update, delete, text
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Any
from datetime import datetime
import logging
import traceback
import time
from functools import wraps

# Import model classes from models module
from ..models import Base, Score, Response, Question, QuestionCategory
from ..config import get_settings
from ..utils.cache import cache_manager

settings = get_settings()
logger = logging.getLogger("api.db")

# Convert standard sqlite:// to sqlite+aiosqlite:// if needed
database_url = settings.database_url
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

# Configure connect_args based on DB type
connect_args = {}
if settings.database_type == "sqlite":
    # SQLite async driver specific settings
    connect_args["timeout"] = settings.database_pool_timeout
elif "postgresql" in database_url:
    # Postgres-specific statement timeout (milliseconds)
    connect_args["command_timeout"] = settings.database_statement_timeout / 1000.0

# Create async engine with production-ready pooling
engine_args = {
    "connect_args": connect_args,
    "echo": settings.debug
}

if settings.database_type == "sqlite":
    from sqlalchemy.pool import StaticPool
    engine_args["poolclass"] = StaticPool
else:
    engine_args.update({
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_recycle": settings.database_pool_recycle,
        "pool_pre_ping": settings.database_pool_pre_ping,
    })

# Initialize Async Engine
engine = create_async_engine(database_url, **engine_args)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False, 
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Dependency to get asynchronous database session."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            # Automatic commit if no exception
            # We don't auto-commit here to give service layer control, 
            # but we ensure the session is closed by the context manager.
        except Exception as e:
            await db.rollback()
            logger.error(f"Async Database session error: {e}", extra={
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
            raise
        finally:
            await db.close()

def db_timeout(seconds: float = 5.0):
    """Timeout wrapper for database operations to prevent thread hangs."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Database operation timed out after {seconds}s: {func.__name__}")
                raise Exception(f"Database operation timed out: {func.__name__}")
        return wrapper
    return decorator

class AssessmentService:
    """Service for managing assessments (scores) using AsyncSession."""
    
    @staticmethod
    @db_timeout(10.0)
    async def get_assessments(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> Tuple[List[Score], int]:
        """Get assessments with pagination and optional filters (Async)."""
        stmt = select(Score)
        
        # Apply filters
        if user_id is not None:
            stmt = stmt.filter(Score.user_id == user_id)
        elif username:
            stmt = stmt.filter(Score.username == username)
        if age_group:
            stmt = stmt.filter(Score.detailed_age_group == age_group)
        
        # Get total count (using a separate statement for clarity and speed in async)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Score.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        assessments = result.scalars().all()
        
        return list(assessments), total
    
    @staticmethod
    async def get_assessment_by_id(
        db: AsyncSession, assessment_id: int, user_id: Optional[int] = None
    ) -> Optional[Score]:
        """Get a single assessment by ID (Async)."""
        stmt = select(Score).filter(Score.id == assessment_id)
        if user_id is not None:
            stmt = stmt.filter(Score.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    @cache_manager.cache(ttl=600, prefix="stats")
    async def get_assessment_stats(
        db: AsyncSession,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ) -> dict:
        """Get statistical summary of assessments (Async)."""
        stmt = select(
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.max(Score.total_score).label('max_score'),
            func.min(Score.total_score).label('min_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        )
        
        if user_id is not None:
            stmt = stmt.filter(Score.user_id == user_id)
        elif username:
            stmt = stmt.filter(Score.username == username)
        
        result = await db.execute(stmt)
        stats = result.mappings().first()
        
        # Get age group distribution
        age_stmt = select(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        ).group_by(Score.detailed_age_group)
        
        if user_id is not None:
            age_stmt = age_stmt.filter(Score.user_id == user_id)
        elif username:
            age_stmt = age_stmt.filter(Score.username == username)
        
        age_result = await db.execute(age_stmt)
        age_distribution = age_result.all()
        
        return {
            'total_assessments': stats['total'] or 0,
            'average_score': round(float(stats['avg_score'] or 0), 2),
            'highest_score': stats['max_score'] or 0,
            'lowest_score': stats['min_score'] or 0,
            'average_sentiment': round(float(stats['avg_sentiment'] or 0), 2),
            'age_group_distribution': {
                age_group: count for age_group, count in age_distribution if age_group
            }
        }

class QuestionService:
    """Service for managing questions (Async)."""
    
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
        """Get questions with pagination and filters (Async)."""
        stmt = select(Question)
        
        if active_only:
            stmt = stmt.filter(Question.is_active == 1)
        if category_id is not None:
            stmt = stmt.filter(Question.category_id == category_id)
        if min_age is not None:
            stmt = stmt.filter(Question.min_age <= min_age)
        if max_age is not None:
            stmt = stmt.filter(Question.max_age >= max_age)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        stmt = stmt.order_by(Question.id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        questions = result.scalars().all()
        
        return list(questions), total
    
    @staticmethod
    async def get_question_by_id(db: AsyncSession, question_id: int) -> Optional[Question]:
        """Get a single question by ID (Async)."""
        stmt = select(Question).filter(Question.id == question_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
