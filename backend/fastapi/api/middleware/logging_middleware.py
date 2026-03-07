"""
Request-Level Logging Middleware

Provides comprehensive request/response logging with:
- Unique request ID generation (UUID4) for correlation
- Processing time tracking
- JSON-formatted structured logs
- X-Request-ID response header for frontend tracing
- PII protection (no body logging for sensitive endpoints)
- Context variable propagation for nested logging and async tasks
- Integration with context propagation system for traceability across async boundaries
"""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable, Optional, Dict, Any

from ..utils.deep_redactor import DeepRedactorFormatter
from ..utils.context_propagation import (
    request_id_ctx,
    user_id_ctx,
    correlation_id_ctx,
    request_path_ctx,
    client_ip_ctx,
    trace_parent_ctx,
    RequestContext,
    capture_request_context,
    set_context_vars,
    reset_context_vars,
    TracingContextFilter,
)
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Re-export for backward compatibility
from ..utils.context_propagation import (
    get_request_id,
    get_user_id,
    get_correlation_id,
    get_trace_parent,
    get_full_context,
    propagate_context,
    propagate_context_sync,
    create_task_with_context,
    ContextPropagator,
)


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
    - Sets up context for propagation into async tasks (Issue #1363)
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
            # Also add TracingContextFilter for enhanced tracing (Issue #1363)
            root_handler.addFilter(TracingContextFilter())
    
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
    
    def _capture_full_context(self, request: Request) -> RequestContext:
        """
        Capture full request context including distributed tracing info.
        
        Issue #1363: Request Context Propagation into Async Tasks
        Captures all relevant context for propagation to async boundaries.
        """
        request_id = str(uuid.uuid4())
        
        # Get user_id if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        # Get correlation ID from headers (for distributed tracing)
        correlation_id = request.headers.get("X-Correlation-ID")
        
        # Get W3C trace context
        trace_parent = request.headers.get("traceparent")
        
        return RequestContext(
            request_id=request_id,
            user_id=user_id,
            correlation_id=correlation_id,
            request_path=str(request.url.path),
            client_ip=self._get_client_ip(request),
            trace_parent=trace_parent,
            metadata={
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "method": request.method,
            }
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with comprehensive logging and context setup.
        
        1. Generate unique request ID
        2. Set request context in context variables for propagation
        3. Record start time
        4. Process request
        5. Calculate processing time
        6. Log structured request/response data
        7. Add X-Request-ID header to response
        
        Issue #1363: Sets up context that can be captured and propagated to async tasks
        """
        # Capture full request context
        context = self._capture_full_context(request)
        
        # Set all context variables for propagation
        tokens = set_context_vars(context)
        
        # Store request_id in request state for access in route handlers
        request.state.request_id = context.request_id
        request.state.request_context = context  # Store full context for easy access
        
        # Record start time
        start_time = time.time()
        
        # Extract request metadata
        method = request.method
        path = request.url.path
        client_ip = context.client_ip
        user_agent = request.headers.get("User-Agent", "unknown")
        is_sensitive = self._is_sensitive_path(path)
        
        # Log incoming request
        request_log = {
            "event": "request_started",
            "request_id": context.request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        
        # Add correlation ID if present
        if context.correlation_id:
            request_log["correlation_id"] = context.correlation_id
        
        # Add trace parent if present
        if context.trace_parent:
            request_log["trace_parent"] = context.trace_parent
        
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
            response.headers["X-Request-ID"] = context.request_id
            
            # Add correlation ID header if it was provided
            if context.correlation_id:
                response.headers["X-Correlation-ID"] = context.correlation_id
            
            # Extract user ID from request state if available (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            if user_id and not context.user_id:
                context.user_id = user_id
            
            # Log request completion
            response_log = {
                "event": "request_completed",
                "request_id": context.request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
            }
            
            # Add user ID if authenticated
            if context.user_id:
                response_log["user_id"] = context.user_id
            
            # Add correlation ID if present
            if context.correlation_id:
                response_log["correlation_id"] = context.correlation_id
            
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
                    "request_id": context.request_id,
                    "method": method,
                    "path": path,
                    "process_time_ms": round(process_time, 2),
                    "threshold_ms": 500,
                }
                if context.user_id:
                    slow_log["user_id"] = context.user_id
                logger.warning(json.dumps(slow_log))
            
            return response
        except Exception as e:
            # Log exception
            process_time = (time.time() - start_time) * 1000
            error_log = {
                "event": "request_error",
                "request_id": context.request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time_ms": round(process_time, 2),
            }
            if context.user_id:
                error_log["user_id"] = context.user_id
            logger.error(json.dumps(error_log), exc_info=True)
            raise
        finally:
            # Always reset context to prevent leakage
            reset_context_vars(tokens)


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
        correlation_id = get_correlation_id()
        user_id = get_user_id()
        
        # Redact the message itself
        redacted_msg = DeepRedactor.redact(msg)
        log_data = {"message": redacted_msg}
        
        if request_id:
            log_data["request_id"] = request_id
        
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        if user_id:
            log_data["user_id"] = user_id
        
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


def create_request_context_from_state(request: Request) -> Optional[RequestContext]:
    """
    Helper function to get request context from request state.
    
    Useful when scheduling background tasks from route handlers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        RequestContext if available, None otherwise
        
    Example:
        @app.post("/export")
        async def export_data(request: Request):
            context = create_request_context_from_state(request)
            # Pass context to background task
            asyncio.create_task(
                propagate_context(context, process_export, data)
            )
    """
    return getattr(request.state, "request_context", None)
