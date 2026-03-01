"""
Database Error Handling Utilities

Provides common error handling patterns for database operations across all services.
"""

import logging
from typing import Callable, TypeVar, Any
from contextlib import contextmanager
from sqlalchemy.exc import OperationalError, DatabaseError, DisconnectionError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar('T')

class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass

def handle_db_operation(operation_name: str = "database operation"):
    """
    Decorator for handling database connection errors in service methods.

    Usage:
        @handle_db_operation("user registration")
        def register_user(self, user_data):
            # database operations here
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except (OperationalError, DatabaseError, DisconnectionError) as e:
                logger.error(f"Database connection error during {operation_name}: {str(e)}")
                raise DatabaseConnectionError(f"Service temporarily unavailable. Please try again later.")
            except Exception as e:
                logger.error(f"Unexpected error during {operation_name}: {str(e)}")
                raise
        return wrapper
    return decorator

@contextmanager
def db_error_handler(operation_name: str = "database operation", rollback_on_error: bool = True):
    """
    Context manager for handling database operations with error handling.

    Usage:
        with db_error_handler("user query", rollback_on_error=True):
            user = self.db.query(User).filter(...).first()
            return user
    """
    try:
        yield
    except (OperationalError, DatabaseError, DisconnectionError) as e:
        if rollback_on_error and hasattr(Session, 'rollback'):
            # Try to rollback if we have a session
            for arg in locals().get('args', []):
                if hasattr(arg, 'rollback'):
                    try:
                        arg.rollback()
                    except:
                        pass
        logger.error(f"Database connection error during {operation_name}: {str(e)}")
        raise DatabaseConnectionError(f"Service temporarily unavailable. Please try again later.")
    except Exception as e:
        if rollback_on_error:
            # Try to rollback on any error
            for arg in locals().get('args', []):
                if hasattr(arg, 'rollback'):
                    try:
                        arg.rollback()
                    except:
                        pass
        logger.error(f"Unexpected error during {operation_name}: {str(e)}")
        raise

def safe_db_query(db: Session, query_func: Callable[[], Any], operation_name: str = "query") -> Any:
    """
    Safely execute a database query with error handling.

    Usage:
        user = safe_db_query(self.db, lambda: self.db.query(User).filter(User.id == user_id).first(), "get user")
    """
    try:
        return query_func()
    except (OperationalError, DatabaseError, DisconnectionError) as e:
        logger.error(f"Database connection error during {operation_name}: {str(e)}")
        raise DatabaseConnectionError(f"Service temporarily unavailable. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name}: {str(e)}")
        raise