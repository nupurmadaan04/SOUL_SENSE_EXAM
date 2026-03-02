"""
Database Error Handling Utilities with Transient Failure Retry Logic

Provides common error handling patterns for database operations across all services.
Supports automatic retry with exponential backoff and jitter for transient database errors.

Transient Errors (Retriable):
- SQLState 40001: Serialization failure / Deadlock detected
- SQLState 40P01: Deadlock detected (PostgreSQL)
- SQLState 55P03: Lock not available
- SQLState 57014: Query cancelled
- Other connection-level errors (08xxx)

Permanent Errors (Non-Retriable):
- Constraint violations (23xxx)
- Permission errors (42xxx)
- Syntax errors (42601)
"""

import logging
import asyncio
import time
import random
from typing import Callable, TypeVar, Any, Optional
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from sqlalchemy.exc import OperationalError, DatabaseError, DisconnectionError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_MS = 100
DEFAULT_JITTER_FACTOR = 0.1

# Transient SQL error codes (retriable)
TRANSIENT_SQLSTATES = {
    '40001',  # Serialization failure / Deadlock detected
    '40P01',  # Deadlock detected (PostgreSQL specific)
    '55P03',  # Lock not available
    '57014',  # Query cancelled
    '08000',  # Connection exception
    '08003',  # Connection does not exist
    '08006',  # Connection failure
    '60000',  # System error
}


class DatabaseConnectionError(Exception):
    """Raised when database connection fails (after retries exhausted)."""
    pass


class TransientDatabaseError(DatabaseConnectionError):
    """Internal exception for transient database errors that should be retried."""
    pass


class PermanentDatabaseError(DatabaseConnectionError):
    """Exception for permanent database errors that should not be retried."""
    pass


def _is_transient_error(exception: Exception) -> bool:
    """
    Determine if a database exception is transient (retriable) or permanent.
    
    Transient errors: deadlocks, lock timeouts, connection issues
    Permanent errors: constraint violations, permission errors, syntax errors
    
    Args:
        exception: SQLAlchemy exception
        
    Returns:
        True if error is transient and retriable, False if permanent
    """
    if not isinstance(exception, (OperationalError, DatabaseError, DisconnectionError)):
        return False
    
    try:
        # Extract SQLState code from the original database exception
        if hasattr(exception, 'orig') and exception.orig is not None:
            orig_exc = exception.orig
            
            # PostgreSQL and other databases provide sqlstate attribute
            if hasattr(orig_exc, 'sqlstate'):
                sqlstate = orig_exc.sqlstate
                if sqlstate in TRANSIENT_SQLSTATES:
                    return True
                # If no sqlstate, treat connection errors as transient
                return False
        
        # For DisconnectionError, always treat as transient
        if isinstance(exception, DisconnectionError):
            return True
            
        # Conservative: treat unknown OperationalError as transient
        if isinstance(exception, OperationalError):
            return True
            
    except Exception:
        # On any error in detection logic, default to transient
        pass
    
    return False


def _calculate_backoff_delay(attempt: int, base_delay_ms: float = DEFAULT_BASE_DELAY_MS, 
                             jitter_factor: float = DEFAULT_JITTER_FACTOR) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Uses exponential backoff: base_delay * (4 ** attempt)
    With jitter: delay * (1 + random(-jitter_factor, +jitter_factor))
    
    Prevents "thundering herd" behavior where multiple requests retry at same time.
    
    Args:
        attempt: Retry attempt number (0-based)
        base_delay_ms: Base delay in milliseconds
        jitter_factor: Jitter factor (0.0-1.0, typically 0.1 for 10%)
        
    Returns:
        Delay in seconds (milliseconds converted to seconds)
    """
    # Exponential backoff: 100ms, 400ms, 1600ms for attempts 0, 1, 2
    exponential_delay = base_delay_ms * (4 ** attempt)
    
    # Add jitter: random factor between (1 - jitter_factor) and (1 + jitter_factor)
    jitter_multiplier = 1.0 + random.uniform(-jitter_factor, jitter_factor)
    delay_ms = exponential_delay * jitter_multiplier
    
    # Convert to seconds
    return delay_ms / 1000.0


async def _retry_async_operation(
    coro_func: Callable[..., Any],
    operation_name: str = "database operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> Any:
    """
    Execute an async operation with automatic retry on transient database errors.
    
    Args:
        coro_func: Async callable that returns a coroutine
        operation_name: Human-readable operation name for logging
        max_retries: Maximum number of retry attempts
        base_delay_ms: Base delay in milliseconds for exponential backoff
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseConnectionError: If operation fails after all retries
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await coro_func()
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            last_exception = e
            
            if not _is_transient_error(e):
                logger.error(
                    f"Permanent database error during {operation_name}: {str(e)}",
                    exc_info=True
                )
                raise PermanentDatabaseError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
            
            # Transient error - retry if attempts remaining
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                logger.warning(
                    f"Transient database error during {operation_name} "
                    f"(SQLState: {getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Database operation {operation_name} failed after {max_retries} retries. "
                    f"Last error: {str(e)}",
                    exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during {operation_name}: {str(e)}", exc_info=True)
            raise
    
    # Should not reach here, but just in case
    raise DatabaseConnectionError(
        f"Service temporarily unavailable. Please try again later."
    ) from last_exception


def _retry_sync_operation(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: dict = None,
    operation_name: str = "database operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> T:
    """
    Execute a sync operation with automatic retry on transient database errors.
    
    Args:
        func: Callable to execute
        args: Positional arguments for the callable
        kwargs: Keyword arguments for the callable
        operation_name: Human-readable operation name for logging
        max_retries: Maximum number of retry attempts
        base_delay_ms: Base delay in milliseconds for exponential backoff
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseConnectionError: If operation fails after all retries
    """
    if kwargs is None:
        kwargs = {}
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            last_exception = e
            
            if not _is_transient_error(e):
                logger.error(
                    f"Permanent database error during {operation_name}: {str(e)}",
                    exc_info=True
                )
                raise PermanentDatabaseError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
            
            # Transient error - retry if attempts remaining
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                logger.warning(
                    f"Transient database error during {operation_name} "
                    f"(SQLState: {getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Database operation {operation_name} failed after {max_retries} retries. "
                    f"Last error: {str(e)}",
                    exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during {operation_name}: {str(e)}", exc_info=True)
            raise
    
    raise DatabaseConnectionError(
        f"Service temporarily unavailable. Please try again later."
    ) from last_exception


def handle_db_operation(
    operation_name: str = "database operation",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
):
    """
    Decorator for handling database connection errors in service methods with retry logic.
    
    Automatically retries operations on transient database errors (deadlocks, lock timeouts)
    using exponential backoff with jitter to prevent thundering herd.
    
    Supports both sync and async functions.
    
    Args:
        operation_name: Human-readable operation name for logging
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds for exponential backoff (default: 100ms)
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd (default: 0.1)

    Usage (Sync):
        @handle_db_operation("user registration", max_retries=3)
        def register_user(self, user_data):
            # database operations here
            pass

    Usage (Async):
        @handle_db_operation("user registration", max_retries=3)
        async def register_user(self, user_data):
            # async database operations here
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Check if function is async
        import asyncio
        import inspect
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                async def coro_func():
                    return await func(*args, **kwargs)
                
                return await _retry_async_operation(
                    coro_func,
                    operation_name=operation_name,
                    max_retries=max_retries,
                    base_delay_ms=base_delay_ms,
                    jitter_factor=jitter_factor,
                )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                return _retry_sync_operation(
                    func,
                    args=args,
                    kwargs=kwargs,
                    operation_name=operation_name,
                    max_retries=max_retries,
                    base_delay_ms=base_delay_ms,
                    jitter_factor=jitter_factor,
                )
            return sync_wrapper
    
    return decorator


@contextmanager
def db_error_handler(
    operation_name: str = "database operation",
    rollback_on_error: bool = True,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
):
    """
    Context manager for handling database operations with error handling and retry logic.
    
    Automatically retries operations on transient database errors.
    Handles rollback on errors.
    
    Args:
        operation_name: Human-readable operation name for logging
        rollback_on_error: Whether to rollback on error (default: True)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds for exponential backoff (default: 100ms)
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd (default: 0.1)

    Usage:
        with db_error_handler("user query", rollback_on_error=True, max_retries=3):
            user = self.db.query(User).filter(...).first()
            return user
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            yield
            return  # Success - exit context
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            last_exception = e
            
            # Try to rollback if we have a session
            if rollback_on_error:
                try:
                    for arg in locals().get('self', {}).values() if isinstance(locals().get('self'), dict) else []:
                        if hasattr(arg, 'rollback'):
                            try:
                                arg.rollback()
                            except:
                                pass
                except:
                    pass
            
            if not _is_transient_error(e):
                logger.error(
                    f"Permanent database error during {operation_name}: {str(e)}",
                    exc_info=True
                )
                raise PermanentDatabaseError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
            
            # Transient error - retry if attempts remaining
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                logger.warning(
                    f"Transient database error during {operation_name} "
                    f"(SQLState: {getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Database operation {operation_name} failed after {max_retries} retries. "
                    f"Last error: {str(e)}",
                    exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during {operation_name}: {str(e)}", exc_info=True)
            raise
    
    # Should not reach here, but just in case
    if last_exception:
        raise DatabaseConnectionError(
            f"Service temporarily unavailable. Please try again later."
        ) from last_exception


@asynccontextmanager
async def db_error_handler_async(
    operation_name: str = "database operation",
    rollback_on_error: bool = True,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
):
    """
    Async context manager for handling async database operations with error handling and retry logic.
    
    Automatically retries operations on transient database errors.
    Handles rollback on errors.
    
    Args:
        operation_name: Human-readable operation name for logging
        rollback_on_error: Whether to rollback on error (default: True)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds for exponential backoff (default: 100ms)
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd (default: 0.1)

    Usage:
        async with db_error_handler_async("user query", rollback_on_error=True, max_retries=3) as session:
            user = await session.query(User).filter(...).first()
            return user
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            yield
            return  # Success - exit context
        except (OperationalError, DatabaseError, DisconnectionError) as e:
            last_exception = e
            
            # Try to rollback if we have a session
            if rollback_on_error:
                try:
                    for arg in locals().get('self', {}).values() if isinstance(locals().get('self'), dict) else []:
                        if hasattr(arg, 'rollback'):
                            try:
                                await arg.rollback() if asyncio.iscoroutinefunction(arg.rollback) else arg.rollback()
                            except:
                                pass
                except:
                    pass
            
            if not _is_transient_error(e):
                logger.error(
                    f"Permanent database error during {operation_name}: {str(e)}",
                    exc_info=True
                )
                raise PermanentDatabaseError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
            
            # Transient error - retry if attempts remaining
            if attempt < max_retries:
                delay = _calculate_backoff_delay(attempt, base_delay_ms, jitter_factor)
                logger.warning(
                    f"Transient database error during {operation_name} "
                    f"(SQLState: {getattr(e.orig, 'sqlstate', 'unknown') if hasattr(e, 'orig') else 'unknown'}). "
                    f"Retrying in {delay*1000:.0f}ms (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Database operation {operation_name} failed after {max_retries} retries. "
                    f"Last error: {str(e)}",
                    exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Service temporarily unavailable. Please try again later."
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during {operation_name}: {str(e)}", exc_info=True)
            raise
    
    # Should not reach here, but just in case
    if last_exception:
        raise DatabaseConnectionError(
            f"Service temporarily unavailable. Please try again later."
        ) from last_exception


def safe_db_query(
    db: Session,
    query_func: Callable[[], Any],
    operation_name: str = "query",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> Any:
    """
    Safely execute a database query with error handling and automatic retry on transient errors.
    
    Retries the query up to max_retries times with exponential backoff and jitter
    on transient database errors (deadlocks, lock timeouts, etc.).
    
    Args:
        db: SQLAlchemy Session
        query_func: Callable that performs the database query
        operation_name: Human-readable operation name for logging
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds for exponential backoff (default: 100ms)
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd (default: 0.1)

    Returns:
        Result of the query

    Raises:
        DatabaseConnectionError: If query fails after all retries

    Usage:
        user = safe_db_query(
            self.db,
            lambda: self.db.query(User).filter(User.id == user_id).first(),
            "get user by ID",
            max_retries=3
        )
    """
    return _retry_sync_operation(
        query_func,
        operation_name=operation_name,
        max_retries=max_retries,
        base_delay_ms=base_delay_ms,
        jitter_factor=jitter_factor,
    )


async def safe_db_query_async(
    db: Any,  # AsyncSession
    query_func: Callable[..., Any],
    operation_name: str = "query",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay_ms: float = DEFAULT_BASE_DELAY_MS,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> Any:
    """
    Safely execute an async database query with error handling and automatic retry.
    
    Retries the query up to max_retries times with exponential backoff and jitter
    on transient database errors (deadlocks, lock timeouts, etc.).
    
    Args:
        db: SQLAlchemy AsyncSession
        query_func: Async callable that performs the database query
        operation_name: Human-readable operation name for logging
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay_ms: Base delay in milliseconds for exponential backoff (default: 100ms)
        jitter_factor: Jitter factor (0.0-1.0) to prevent thundering herd (default: 0.1)

    Returns:
        Result of the query

    Raises:
        DatabaseConnectionError: If query fails after all retries

    Usage:
        user = await safe_db_query_async(
            self.db,
            lambda: self.db.query(User).filter(User.id == user_id).first(),
            "get user by ID",
            max_retries=3
        )
    """
    async def coro_wrapper():
        return await query_func()
    
    return await _retry_async_operation(
        coro_wrapper,
        operation_name=operation_name,
        max_retries=max_retries,
        base_delay_ms=base_delay_ms,
        jitter_factor=jitter_factor,
    )