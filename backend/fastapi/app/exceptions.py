"""
Exception Hierarchy for SoulSense Application.

All application-specific exceptions inherit from SoulSenseError,
which provides consistent error handling and optional chaining.
"""

from typing import Optional


# Error code constants for categorization
class ErrorCodes:
    """Error code constants for programmatic error handling."""
    # Database errors (1000-1999)
    DB_CONNECTION_FAILED = 1001
    DB_QUERY_FAILED = 1002
    DB_INTEGRITY_ERROR = 1003
    
    # Configuration errors (2000-2999)
    CONFIG_MISSING = 2001
    CONFIG_INVALID = 2002
    CONFIG_PARSE_ERROR = 2003
    
    # Resource errors (3000-3999)
    RESOURCE_NOT_FOUND = 3001
    RESOURCE_LOAD_FAILED = 3002
    
    # Validation errors (4000-4999)
    VALIDATION_FAILED = 4001
    INVALID_INPUT = 4002
    
    # Authentication errors (5000-5999)
    AUTH_FAILED = 5001
    AUTH_EXPIRED = 5002
    AUTH_INVALID_CREDENTIALS = 5003
    
    # API errors (6000-6999)
    API_CONNECTION_FAILED = 6001
    API_TIMEOUT = 6002
    API_RESPONSE_ERROR = 6003
    
    # ML errors (7000-7999)
    ML_MODEL_LOAD_FAILED = 7001
    ML_PREDICTION_FAILED = 7002
    ML_TRAINING_FAILED = 7003
    
    # UI errors (8000-8999)
    UI_RENDER_FAILED = 8001
    UI_EVENT_ERROR = 8002
    
    # Export errors (9000-9999)
    EXPORT_FAILED = 9001
    EXPORT_FORMAT_ERROR = 9002


class SoulSenseError(Exception):
    """
    Base exception for SoulSense application.
    
    All custom exceptions should inherit from this class.
    Provides error code support and exception chaining.
    """
    
    default_code: int = 0
    
    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None,
        error_code: Optional[int] = None
    ) -> None:
        super().__init__(message)
        self.original_exception = original_exception
        self.error_code = error_code or self.default_code
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.error_code:
            return f"[E{self.error_code}] {base}"
        return base


class DatabaseError(SoulSenseError):
    """Raised when a database operation fails."""
    default_code = ErrorCodes.DB_QUERY_FAILED


class ConfigurationError(SoulSenseError):
    """Raised when configuration is missing or invalid."""
    default_code = ErrorCodes.CONFIG_INVALID


class ResourceError(SoulSenseError):
    """Raised when a required resource (file, asset, question) is missing."""
    default_code = ErrorCodes.RESOURCE_NOT_FOUND


class ValidationError(SoulSenseError):
    """Raised when user input is invalid."""
    default_code = ErrorCodes.VALIDATION_FAILED


class AuthenticationError(SoulSenseError):
    """Raised when authentication fails."""
    default_code = ErrorCodes.AUTH_FAILED


class APIConnectionError(SoulSenseError):
    """Raised when external API connection fails."""
    pass

class IntegrityError(SoulSenseError):
    """Raised when startup integrity checks fail."""
    pass

    default_code = ErrorCodes.API_CONNECTION_FAILED


class MLModelError(SoulSenseError):
    """Raised when ML model operations fail (loading, prediction, training)."""
    default_code = ErrorCodes.ML_MODEL_LOAD_FAILED


class UIError(SoulSenseError):
    """Raised when UI rendering or event handling fails."""
    default_code = ErrorCodes.UI_RENDER_FAILED


class ExportError(SoulSenseError):
    """Raised when export or report generation fails."""
    default_code = ErrorCodes.EXPORT_FAILED
