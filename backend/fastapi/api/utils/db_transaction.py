"""
backend/fastapi/api/utils/db_transaction.py - Atomic DB Transaction Utilities (FastAPI layer)

Mirrors app/utils/db_transaction.py for the FastAPI backend services.

Provides:
- transactional(db)  - atomic context manager around a SQLAlchemy Session
- retry_on_transient - retry decorator for transient OperationalErrors
"""

from __future__ import annotations

import logging
import time
import functools
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

_TRANSIENT_MSG_FRAGMENTS = (
    "database is locked",
    "deadlock",
    "connection reset",
    "connection timed out",
    "unable to open database",
    "disk i/o error",
    "operational error",
)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, OperationalError):
        msg = str(exc).lower()
        return any(fragment in msg for fragment in _TRANSIENT_MSG_FRAGMENTS)
    return False


@asynccontextmanager
async def transactional(db: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous context manager for atomic database transactions.
    
    Usage:
        async with transactional(db) as session:
            # perform operations
            await session.flush()
    """
    if not isinstance(db, AsyncSession):
        raise TypeError(f"Expected AsyncSession, got {type(db).__name__}")
        
    try:
        # Start a nested transaction or just use the current one
        # AsyncSession handles transaction state automatically
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction failed, rolling back: {e}")
        raise


F = TypeVar("F", bound=Callable[..., Any])


def retry_on_transient(
    retries: int = 3,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    """
    Decorator: retry *func* on transient DB errors with exponential back-off.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < retries and _is_transient(exc):
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            "Transient DB error attempt %d/%d – retrying in %.1fs: %s",
                            attempt + 1, retries + 1, delay, exc,
                        )
                        time.sleep(delay)
                    else:
                        raise
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
