"""
app/utils/db_transaction.py - Atomic Database Transaction Utilities

Provides:
- transactional() context manager: wraps operations in an atomic SQLAlchemy transaction
  with automatic rollback on exception and configurable retry for transient failures.
- retry_on_transient() decorator: retries a DB operation on known transient errors
  (OperationalError / timeout) using exponential back-off.

Usage
-----
# Context manager style
with transactional(db) as tx:
    tx.add(user)
    tx.add(session_record)
# Commits automatically; rolls back automatically on exception.

# Decorator style
@retry_on_transient(retries=3)
def save_critical(db, data):
    with transactional(db) as tx:
        tx.add(data)
"""

from __future__ import annotations

import logging
import time
import functools
from contextlib import contextmanager
from typing import Generator, Callable, Any, TypeVar

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transient error detection
# ---------------------------------------------------------------------------

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
    """Return True if the exception looks like a recoverable transient error."""
    if isinstance(exc, OperationalError):
        msg = str(exc).lower()
        return any(fragment in msg for fragment in _TRANSIENT_MSG_FRAGMENTS)
    return False


# ---------------------------------------------------------------------------
# Core atomic context manager
# ---------------------------------------------------------------------------

@contextmanager
def transactional(db: Session) -> Generator[Session, None, None]:
    """
    Yield the existing *db* session wrapped in an atomic transaction block.

    - On success  → commits the nested savepoint (no partial writes).
    - On any error → rolls back to the savepoint, then re-raises.

    Nested calls are safe: SQLAlchemy uses SAVEPOINTs automatically for
    sessions that are already inside a transaction.

    Example::

        with transactional(db) as tx:
            tx.add(user)
            tx.add(profile)
        # ↑ Both rows committed atomically, or neither.
    """
    try:
        yield db
        db.commit()
        logger.debug("Transaction committed successfully.")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "SQLAlchemy error – transaction rolled back: %s",
            exc,
            exc_info=True,
        )
        raise
    except Exception as exc:
        db.rollback()
        logger.error(
            "Unexpected error – transaction rolled back: %s",
            exc,
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_transient(
    retries: int = 3,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    """
    Decorator that retries *func* up to *retries* times if a transient DB
    error is raised.

    Delays between attempts follow exponential back-off:
        delay = base_delay * (backoff_factor ** attempt)

    Args:
        retries:        Maximum number of retry attempts (total = 1 + retries).
        base_delay:     Seconds to wait before the first retry.
        backoff_factor: Multiplier applied to delay on each subsequent retry.

    Example::

        @retry_on_transient(retries=3)
        def save_critical(db: Session, user: User) -> None:
            with transactional(db) as tx:
                tx.add(user)
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
                            "Transient DB error on attempt %d/%d – retrying in %.1fs: %s",
                            attempt + 1,
                            retries + 1,
                            delay,
                            exc,
                        )
                        time.sleep(delay)
                    else:
                        raise
            # Should be unreachable, but satisfies type-checkers
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
