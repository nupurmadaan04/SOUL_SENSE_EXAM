"""Database service for assessments and questions (Async Version)."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import func, select, update, delete, text
from typing import List, Optional, Tuple, AsyncGenerator
from datetime import datetime
from fastapi import HTTPException, Request, status
import logging
import traceback
import time
from functools import wraps

# Import model classes from models module
from ..models import Base, Score, Response, Question, QuestionCategory
from ..config import get_settings

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

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Async dependency to get a request-scoped database session.

    Guarantees:
    - single AsyncSession per request context (nested dependencies share same session)
    - rollback on exceptions/timeouts
    - timeout guard to prevent stalled sessions starving the pool
    """
    existing_session = getattr(request.state, "db_session", None)
    if existing_session is not None:
        yield existing_session
        return

    timeout_seconds = int(getattr(settings, "db_request_timeout_seconds", 30))

    async with AsyncSessionLocal() as db:
        request.state.db_session = db
        try:
            async with asyncio.timeout(timeout_seconds):
                yield db
        except TimeoutError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timed out",
            ) from exc
        except Exception:
            await db.rollback()
            raise
        finally:
            if getattr(request.state, "db_session", None) is db:
                delattr(request.state, "db_session")
            await db.close()

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

def get_pool_status():
    """
    Get metrics about the connection pool status to monitor for exhaustion.
    """
    from sqlalchemy.pool import QueuePool

    if isinstance(engine.pool, QueuePool):
        return {
            "pool_size": engine.pool.size(),
            "checkedin": engine.pool.checkedin(),
            "checkedout": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "pool_timeout": engine.pool.timeout(),
            "pool_recycle": engine.pool.recycle,
            "can_spawn_more": engine.pool.overflow() < engine.pool.max_overflow() if hasattr(engine.pool, 'max_overflow') else False
        }
    return {"pool_type": type(engine.pool).__name__, "message": "Metrics not supported for this pool type"}


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
        """
        Get assessments with pagination and optional filters (Async).
        When user_id is provided, results are scoped to that user only.
        """
        stmt = select(Score)

        # Apply filters
        if user_id is not None:
            stmt = stmt.filter(Score.user_id == user_id)
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
        stats = result.first()

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
        """Get a single question by ID (Async)."""
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


# Transaction management utilities for #1218: Unreleased Locks in Async Transaction Scope
import functools
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError


@asynccontextmanager
async def transaction_scope(db: AsyncSession):
    """
    Async context manager for database transactions with guaranteed rollback.

    Ensures:
    - Automatic rollback on exceptions
    - Lock release on any failure
    - Support for nested savepoints
    - Deterministic transaction boundaries
    """
    async with db.begin():
        try:
            yield
        except Exception:
            # Ensure rollback happens even if begin() context fails
            if db.in_transaction():
                await db.rollback()
            raise


def deadlock_retry(max_retries: int = 3, backoff_factor: float = 0.1):
    """
    Decorator to retry operations that fail due to database deadlocks.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier (seconds)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    # Check if it's a deadlock error (MySQL/PostgreSQL specific)
                    error_msg = str(e).lower()
                    if "deadlock" in error_msg or "lock wait timeout" in error_msg:
                        if attempt < max_retries:
                            # Exponential backoff
                            delay = backoff_factor * (2 ** attempt)
                            logging.getLogger("api.services.db_service").warning(
                                f"Deadlock detected, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})"
                            )
                            await asyncio.sleep(delay)
                            continue
                    # Not a deadlock or max retries reached
                    raise
            # Should not reach here, but just in case
            raise last_exception
        return wrapper
    return decorator


# Export all services
__all__ = [
    'AssessmentService',
    'QuestionService',
    'ResponseService',
    'get_db',
    'engine',
    'AsyncSessionLocal',
    'transaction_scope',
    'deadlock_retry'
]
