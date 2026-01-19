"""
Centralized Error Handling Module for SoulSense Application.

Provides consistent error logging, user-friendly messages, and graceful degradation
across all application modules.

GitHub Issue: #325
"""

import logging
import sys
import traceback
import functools
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast
from datetime import datetime
from contextlib import contextmanager

from app.exceptions import (
    SoulSenseError,
    DatabaseError,
    ConfigurationError,
    ResourceError,
    ValidationError,
    AuthenticationError,
    APIConnectionError,
)

# Type variable for generic return types
T = TypeVar('T')

# Error severity levels
class ErrorSeverity:
    """Error severity classification."""
    LOW = "LOW"           # Minor issues, operation can continue
    MEDIUM = "MEDIUM"     # Notable issues, degraded functionality
    HIGH = "HIGH"         # Critical issues, feature unavailable
    CRITICAL = "CRITICAL" # Application-breaking issues


# User-friendly message mapping
USER_MESSAGES: Dict[Type[Exception], str] = {
    DatabaseError: "A database error occurred. Please try again later.",
    ConfigurationError: "There's a configuration issue. Please contact support.",
    ResourceError: "A required resource could not be found.",
    ValidationError: "Please check your input and try again.",
    AuthenticationError: "Authentication failed. Please check your credentials.",
    APIConnectionError: "Unable to connect to the service. Check your internet connection.",
    FileNotFoundError: "The requested file could not be found.",
    PermissionError: "Permission denied. Please check file permissions.",
    ConnectionError: "Network connection error. Please check your internet.",
    TimeoutError: "The operation timed out. Please try again.",
}


class ErrorHandler:
    """
    Centralized error handler for the SoulSense application.
    
    Provides consistent error logging, user message mapping, and error tracking.
    """
    
    _instance: Optional['ErrorHandler'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'ErrorHandler':
        """Singleton pattern to ensure single error handler instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the error handler."""
        if self._initialized:
            return
            
        self._initialized = True
        self._logger = logging.getLogger("app.error_handler")
        self._error_count: Dict[str, int] = {}
        self._last_errors: list = []
        self._max_error_history = 100
    
    def log_error(
        self,
        exception: Exception,
        module: str = "unknown",
        operation: str = "unknown",
        severity: str = ErrorSeverity.MEDIUM,
        user_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with structured context.
        
        Args:
            exception: The exception that occurred
            module: Module name where error occurred
            operation: Operation being performed when error occurred
            severity: Error severity level
            user_id: Optional user ID for context
            additional_context: Additional context information
        """
        error_type = type(exception).__name__
        timestamp = datetime.now().isoformat()
        
        # Build structured log message
        log_data = {
            "timestamp": timestamp,
            "severity": severity,
            "module": module,
            "operation": operation,
            "error_type": error_type,
            "message": str(exception),
        }
        
        if user_id:
            log_data["user_id"] = str(user_id)
            
        if additional_context:
            log_data["context"] = str(additional_context)
        
        # Get traceback for non-trivial errors
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            log_data["traceback"] = traceback.format_exc()
        
        # Log based on severity
        log_message = (
            f"[{severity}] {module}.{operation}: {error_type} - {exception}"
        )
        
        if severity == ErrorSeverity.CRITICAL:
            self._logger.critical(log_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            self._logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            self._logger.warning(log_message)
        else:
            self._logger.info(log_message)
        
        # Track error statistics
        error_key = f"{module}.{error_type}"
        self._error_count[error_key] = self._error_count.get(error_key, 0) + 1
        
        # Keep recent error history
        self._last_errors.append(log_data)
        if len(self._last_errors) > self._max_error_history:
            self._last_errors.pop(0)
    
    def get_user_message(
        self,
        exception: Exception,
        default_message: str = "An unexpected error occurred. Please try again."
    ) -> str:
        """
        Get a user-friendly message for an exception.
        
        Args:
            exception: The exception to get message for
            default_message: Default message if no mapping found
            
        Returns:
            User-friendly error message
        """
        # Check for SoulSenseError with custom message
        if isinstance(exception, SoulSenseError):
            return str(exception)
        
        # Check type mapping
        for exc_type, message in USER_MESSAGES.items():
            if isinstance(exception, exc_type):
                return message
        
        return default_message
    
    def handle_exception(
        self,
        exception: Exception,
        module: str = "unknown",
        operation: str = "unknown",
        show_ui: bool = True,
        severity: Optional[str] = None
    ) -> None:
        """
        Handle an exception with logging and optional UI notification.
        
        Args:
            exception: The exception to handle
            module: Module name
            operation: Operation name
            show_ui: Whether to show error dialog to user
            severity: Override severity level
        """
        # Determine severity if not provided
        if severity is None:
            if isinstance(exception, (DatabaseError, ConfigurationError)):
                severity = ErrorSeverity.HIGH
            elif isinstance(exception, (ValidationError, ResourceError)):
                severity = ErrorSeverity.MEDIUM
            else:
                severity = ErrorSeverity.MEDIUM
        
        # Log the error
        self.log_error(exception, module, operation, severity)
        
        # Show UI error if requested
        if show_ui:
            try:
                from app.main import show_error
                user_message = self.get_user_message(exception)
                show_error("Error", user_message, exception)
            except ImportError:
                # Fallback if main not available
                print(f"ERROR: {self.get_user_message(exception)}")
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error count statistics."""
        return dict(self._error_count)
    
    def get_recent_errors(self, count: int = 10) -> list:
        """Get recent error entries."""
        return self._last_errors[-count:]


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def safe_operation(
    fallback: Optional[T] = None,
    log: bool = True,
    user_message: Optional[str] = None,
    severity: str = ErrorSeverity.MEDIUM,
    show_ui: bool = False,
    reraise: bool = False
) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    Decorator to wrap functions with automatic error handling.
    
    Args:
        fallback: Value to return if exception occurs
        log: Whether to log the exception
        user_message: Custom user-facing message
        severity: Error severity level
        show_ui: Whether to show error dialog
        reraise: Whether to re-raise the exception after handling
        
    Returns:
        Decorated function
        
    Example:
        @safe_operation(fallback=[], user_message="Failed to load data")
        def load_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                module = func.__module__ or "unknown"
                operation = func.__name__
                
                if log:
                    handler = get_error_handler()
                    handler.log_error(e, module, operation, severity)
                    
                    if show_ui:
                        msg = user_message or handler.get_user_message(e)
                        try:
                            from app.main import show_error
                            show_error("Error", msg, e)
                        except ImportError:
                            pass
                
                if reraise:
                    raise
                    
                return fallback
        return wrapper
    return decorator


@contextmanager
def safe_execute(
    operation_name: str,
    module: str = "unknown",
    fallback_action: Optional[Callable[[], None]] = None,
    log: bool = True,
    severity: str = ErrorSeverity.MEDIUM,
    show_ui: bool = False,
    reraise: bool = False
):
    """
    Context manager for safe execution of code blocks.
    
    Args:
        operation_name: Name of the operation for logging
        module: Module name for logging
        fallback_action: Optional function to call on error
        log: Whether to log exceptions
        severity: Error severity level
        show_ui: Whether to show error dialog
        reraise: Whether to re-raise exceptions
        
    Example:
        with safe_execute("Loading dashboard", module="dashboard"):
            load_dashboard_data()
    """
    try:
        yield
    except Exception as e:
        if log:
            handler = get_error_handler()
            handler.log_error(e, module, operation_name, severity)
            
            if show_ui:
                msg = handler.get_user_message(e)
                try:
                    from app.main import show_error
                    show_error("Error", msg, e)
                except ImportError:
                    pass
        
        if fallback_action:
            try:
                fallback_action()
            except Exception as fallback_error:
                logging.error(f"Fallback action failed: {fallback_error}")
        
        if reraise:
            raise


def setup_global_exception_handlers() -> None:
    """
    Set up global exception handlers for the application.
    
    This wires up:
    - sys.excepthook for uncaught exceptions
    - tkinter's report_callback_exception for GUI errors
    """
    handler = get_error_handler()
    
    def global_excepthook(exc_type: Type[BaseException], exc_value: BaseException, exc_tb) -> None:
        """Handle uncaught exceptions globally."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        
        handler.log_error(
            cast(Exception, exc_value),
            module="global",
            operation="uncaught_exception",
            severity=ErrorSeverity.CRITICAL
        )
        
        # Try to show error to user
        try:
            from app.main import show_error
            user_msg = handler.get_user_message(cast(Exception, exc_value))
            show_error("Unexpected Error", user_msg, exc_value)
        except Exception:
            # Fallback to stderr
            traceback.print_exception(exc_type, exc_value, exc_tb)
    
    # Install global exception hook
    sys.excepthook = global_excepthook
    
    # Try to set up tkinter error handler
    try:
        import tkinter as tk
        
        def tk_exception_handler(exc_type: Type[BaseException], exc_value: BaseException, exc_tb) -> None:
            """Handle tkinter callback exceptions."""
            handler.log_error(
                cast(Exception, exc_value),
                module="tkinter",
                operation="callback_exception",
                severity=ErrorSeverity.HIGH
            )
            
            try:
                from app.main import show_error
                user_msg = handler.get_user_message(cast(Exception, exc_value))
                show_error("Interface Error", user_msg, exc_value)
            except Exception:
                traceback.print_exception(exc_type, exc_value, exc_tb)
        
        # This will be called when Tk is initialized
        tk.Tk.report_callback_exception = tk_exception_handler
        
    except ImportError:
        pass  # tkinter not available


# Convenience function for quick error logging
def log_error(
    exception: Exception,
    module: str = "unknown",
    operation: str = "unknown",
    severity: str = ErrorSeverity.MEDIUM
) -> None:
    """
    Quick helper to log an error.
    
    Args:
        exception: The exception to log
        module: Module name
        operation: Operation name
        severity: Error severity
    """
    get_error_handler().log_error(exception, module, operation, severity)
