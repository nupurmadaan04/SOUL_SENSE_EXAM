"""Database Error Handling with Transient Failure Retry Logic (Issue #1229)"""

import logging
import asyncio
import time
import random
from typing import Callable, Any, TypeVar
from sqlalchemy.exc import OperationalError, DatabaseError, DisconnectionError

logger = logging.getLogger(__name__)
T = TypeVar('T')

# Transient SQL error codes
TRANSIENT_SQLSTATES = {'40001', '40P01', '55P03', '57014', '08000', '08003', '08006'}


class DatabaseConnectionError(Exception):
    """Database connection error."""
    pass


def _is_transient_error(exception: Exception) -> bool:
    """Check if error is transient (retriable)."""
    if not isinstance(exception, (OperationalError, DatabaseError, DisconnectionError)):
        return False
    
    if isinstance(exception, DisconnectionError):
        return True
    
    if isinstance(exception, OperationalError):
        try:
            if hasattr(exception, 'orig') and hasattr(exception.orig, 'sqlstate'):
                return exception.orig.sqlstate in TRANSIENT_SQLSTATES
        except Exception:
            pass
        return True
    
    return False


def _calculate_backoff_delay(attempt: int, base_delay_ms: float = 100.0, 
                             jitter_factor: float = 0.1) -> float:
    """Calculate exponential backoff delay with jitter."""
    exponential_delay = base_delay_ms * (4 ** attempt)
    jitter_multiplier = 1.0 + random.uniform(-jitter_factor, jitter_factor)
    return (exponential_delay * jitter_multiplier) / 1000.0


async def _retry_async_operation(
    coro_func: Callable[..., Any],
    operation_name: str = "database operation",
    max_retries: int = 3,
    base_delay_ms: float = 100.0,
    jitter_factor: float = 0.1,
) -> Any:
    """Execute async operation with automatic retry on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return await coro_func()
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            if not _is_transient_error(e):
                logger.error(f"Permanent database error during {operation_name}: {e}")
                raise DatabaseConnectionError(f"Database error: {str(e)}") from e
            
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                sqlstate = getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'
                logger.warning(
                    f"Transient database error during {operation_name} (SQLState: {sqlstate}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Database operation {operation_name} failed after {max_retries} retries.")
                raise DatabaseConnectionError(f"Database operation failed: {str(e)}") from e


def _retry_sync_operation(
    func: Callable[..., T],
    operation_name: str = "database operation",
    max_retries: int = 3,
    base_delay_ms: float = 100.0,
    jitter_factor: float = 0.1,
) -> T:
    """Execute sync operation with automatic retry on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            if not _is_transient_error(e):
                logger.error(f"Permanent database error during {operation_name}: {e}")
                raise DatabaseConnectionError(f"Database error: {str(e)}") from e
            
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                sqlstate = getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'
                logger.warning(
                    f"Transient database error during {operation_name} (SQLState: {sqlstate}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                logger.error(f"Database operation {operation_name} failed after {max_retries} retries.")
                raise DatabaseConnectionError(f"Database operation failed: {str(e)}") from e
