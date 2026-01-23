"""Centralized error handling utility"""
import logging
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)

def safe_execute(operation_name: str, default_return=None):
    """Decorator for consistent error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                return default_return
        return wrapper
    return decorator

def handle_db_error(func):
    """Decorator for database operation error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            return None
    return wrapper

def validate_input(validation_func):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not validation_func(*args, **kwargs):
                logger.warning(f"Invalid input for {func.__name__}")
                return False
            return func(*args, **kwargs)
        return wrapper
    return decorator