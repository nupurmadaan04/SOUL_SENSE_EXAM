"""
Request-Level Logging Middleware

Provides comprehensive request/response logging with:
- Unique request ID generation (UUID4) for correlation
- Processing time tracking
- JSON-formatted structured logs
- X-Request-ID response header for frontend tracing
- PII protection (no body logging for sensitive endpoints)
- Context variable propagation for nested logging
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable, Optional

from ..utils.deep_redactor import DeepRedactorFormatter
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable to store request_id for the current request
# This allows nested functions/services to access request_id without passing it explicitly
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True

logger = logging.getLogger("api.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging with correlation IDs.
    
    Features:
    - Generates unique UUID4 request ID for each request
    - Tracks request processing time (latency)
    - Emits structured JSON logs for easy parsing by log aggregators
    - Adds X-Request-ID header to responses for frontend tracing
    - Protects PII by avoiding body logging on sensitive endpoints
    - Uses contextvars for request ID propagation throughout request lifecycle
    """
    
    # Sensitive endpoints where we should NOT log request/response bodies
    SENSITIVE_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/password-reset",
        "/api/v1/auth/2fa",
        "/api/v1/profiles/medical",
        "/api/v1/users/me",
    }
    
    def __init__(self, app: Callable):
        super().__init__(app)
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure JSON-formatted logging for structured output."""
        # Ensure logger is configured for JSON output
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            # Use DeepRedactorFormatter for structured logs with PII protection
            formatter = DeepRedactorFormatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "request_id": "%(request_id)s", "message": %(message)s}'
            )
            handler.setFormatter(formatter)
            handler.addFilter(RequestIdFilter())
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        # Ensure request_id is available to all loggers via the root handlers
        root_logger = logging.getLogger()
        for root_handler in root_logger.handlers:
            root_handler.addFilter(RequestIdFilter())
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract real client IP address, handling proxy scenarios.
        
        Priority:
        1. X-Forwarded-For (first IP in chain - actual client)
        2. X-Real-IP (Nginx standard)
        3. request.client.host (direct connection)
        """
        # Check X-Forwarded-For header (standard for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For contains comma-separated IPs: client, proxy1, proxy2
            # The first IP is the actual client
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
        
        # Check X-Real-IP header (Nginx standard)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client host
        return request.client.host if request.client else "unknown"
    
    def _is_sensitive_path(self, path: str) -> bool:
        """Check if the request path is sensitive (contains PII)."""
        # Check exact match
        if path in self.SENSITIVE_PATHS:
            return True
        
        # Check if path starts with sensitive prefix
        for sensitive_path in self.SENSITIVE_PATHS:
            if path.startswith(sensitive_path):
                return True
        
        return False
    
    def _sanitize_query_params(self, request: Request) -> dict:
        """
        Sanitize query parameters by masking sensitive values.
        
        Masks: password, token, secret, key, otp, code
        """
        sensitive_keys = {"password", "token", "secret", "key", "otp", "code", "captcha"}
        sanitized = {}
        
        for key, value in request.query_params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with comprehensive logging.
        
        1. Generate unique request ID
        2. Set request ID in context variable
        3. Record start time
        4. Process request
        5. Calculate processing time
        6. Log structured request/response data
        7. Add X-Request-ID header to response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Set request ID in context variable for propagation
        token = request_id_ctx.set(request_id)
        
        # Store request_id in request state for access in route handlers
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Extract request metadata
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        is_sensitive = self._is_sensitive_path(path)
        
        # Log incoming request
        request_log = {
            "event": "request_started",
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        
        # Add query params if not sensitive
        if not is_sensitive and request.query_params:
            request_log["query_params"] = self._sanitize_query_params(request)
        
        # Log request initiation
        logger.info(json.dumps(request_log))
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Add X-Request-ID header to response for frontend correlation
            response.headers["X-Request-ID"] = request_id
            
            # Extract user ID from request state if available (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            
            # Log request completion
            response_log = {
                "event": "request_completed",
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
            }
            
            # Add user ID if authenticated
            if user_id:
                response_log["user_id"] = user_id
            
            # Add response size if available
            if "content-length" in response.headers:
                response_log["response_size_bytes"] = int(response.headers["content-length"])
            
            # Log level based on status code
            if response.status_code >= 500:
                logger.error(json.dumps(response_log))
            elif response.status_code >= 400:
                logger.warning(json.dumps(response_log))
            else:
                logger.info(json.dumps(response_log))
            
            # Log slow requests separately
            if process_time > 500:
                slow_log = {
                    "event": "slow_request",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "process_time_ms": round(process_time, 2),
                    "threshold_ms": 500,
                }
                logger.warning(json.dumps(slow_log))
            
            return response
        except Exception as e:
            # Log exception
            process_time = (time.time() - start_time) * 1000
            error_log = {
                "event": "request_error",
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time_ms": round(process_time, 2),
            }
            logger.error(json.dumps(error_log), exc_info=True)
            raise
        finally:
            request_id_ctx.reset(token)


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.
    
    This function can be called from anywhere in the request lifecycle
    (services, utilities, etc.) to get the current request ID for logging.
    
    Returns:
        str: Current request ID or None if not in request context
        
    Example:
        from api.middleware.logging_middleware import get_request_id
        
        def some_service_function():
            request_id = get_request_id()
            logger.info(f"Processing data for request {request_id}")
    """
    return request_id_ctx.get()


class ContextualLogger:
    """
    Logger wrapper that automatically includes request_id in all log messages.
    
    Usage:
        from api.middleware.logging_middleware import ContextualLogger
        
        logger = ContextualLogger("my_service")
        logger.info("User logged in", user_id=123)
        # Output: {"request_id": "abc-123", "user_id": 123, "message": "User logged in"}
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _add_context(self, msg: str, **kwargs) -> str:
        from ..utils.deep_redactor import DeepRedactor
        request_id = get_request_id()
        # Redact the message itself
        redacted_msg = DeepRedactor.redact(msg)
        log_data = {"message": redacted_msg}
        
        if request_id:
            log_data["request_id"] = request_id
        
        # Add and redact any extra context
        if kwargs:
            for k, v in kwargs.items():
                log_data[k] = DeepRedactor.redact(v)
        
        return json.dumps(log_data)
    
    def info(self, msg: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._add_context(msg, **kwargs))
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._add_context(msg, **kwargs))
    
    def error(self, msg: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._add_context(msg, **kwargs))
    
    def debug(self, msg: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._add_context(msg, **kwargs))
