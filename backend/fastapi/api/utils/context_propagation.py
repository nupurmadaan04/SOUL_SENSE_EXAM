"""
Request Context Propagation into Async Tasks

This module provides utilities for capturing and propagating request context
across async boundaries. It ensures that correlation IDs, user IDs, and other
request metadata are preserved when tasks are executed asynchronously.

Key Features:
- Context capture from request lifecycle
- Context propagation to async tasks via contextvars
- Thread pool context propagation for sync tasks
- Automatic cleanup to prevent context leakage
- Tracing instrumentation for validation

Usage:
    # In middleware - capture context
    context = capture_request_context(request)
    
    # In background task - propagate context
    asyncio.create_task(propagate_context(context, execute_task, *args, **kwargs))
"""

import asyncio
import logging
import uuid
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import Request

logger = logging.getLogger(__name__)

# Context variables for request metadata
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_path_ctx: ContextVar[Optional[str]] = ContextVar("request_path", default=None)
client_ip_ctx: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
trace_parent_ctx: ContextVar[Optional[str]] = ContextVar("trace_parent", default=None)

T = TypeVar("T")


@dataclass
class RequestContext:
    """
    Immutable data class representing request context.
    
    Attributes:
        request_id: Unique identifier for the request
        user_id: Authenticated user ID (if available)
        correlation_id: External correlation ID for distributed tracing
        request_path: API endpoint path
        client_ip: Client IP address
        trace_parent: W3C trace context parent ID
        metadata: Additional context metadata
    """
    request_id: str
    user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    request_path: Optional[str] = None
    client_ip: Optional[str] = None
    trace_parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "request_path": self.request_path,
            "client_ip": self.client_ip,
            "trace_parent": self.trace_parent,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestContext":
        """Create context from dictionary."""
        return cls(
            request_id=data["request_id"],
            user_id=data.get("user_id"),
            correlation_id=data.get("correlation_id"),
            request_path=data.get("request_path"),
            client_ip=data.get("client_ip"),
            trace_parent=data.get("trace_parent"),
            metadata=data.get("metadata", {}),
        )


def capture_request_context(request: Optional[Request] = None, **kwargs) -> RequestContext:
    """
    Capture request context from a FastAPI request object or current context.
    
    Args:
        request: FastAPI request object
        **kwargs: Additional context metadata
        
    Returns:
        RequestContext: Captured context
        
    Example:
        @app.get("/items")
        async def get_items(request: Request):
            context = capture_request_context(request)
            # Schedule background task with context
            asyncio.create_task(process_items(context, item_ids))
    """
    # First try to get from current context vars
    request_id = request_id_ctx.get()
    user_id = user_id_ctx.get()
    correlation_id = correlation_id_ctx.get()
    request_path = request_path_ctx.get()
    client_ip = client_ip_ctx.get()
    trace_parent = trace_parent_ctx.get()
    
    # Override with request object if provided
    if request is not None:
        # Get request_id from state or headers
        if hasattr(request.state, "request_id"):
            request_id = request.state.request_id
        elif "X-Request-ID" in request.headers:
            request_id = request.headers["X-Request-ID"]
        
        # Get user_id from state
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        
        # Get correlation_id from headers (for distributed tracing)
        correlation_id = request.headers.get("X-Correlation-ID", correlation_id)
        
        # Get trace parent from headers (W3C trace context)
        trace_parent = request.headers.get("traceparent", trace_parent)
        
        # Get path
        request_path = str(request.url.path)
        
        # Get client IP
        client_ip = _extract_client_ip(request)
    
    # Generate request_id if not present
    if not request_id:
        request_id = str(uuid.uuid4())
    
    return RequestContext(
        request_id=request_id,
        user_id=user_id,
        correlation_id=correlation_id,
        request_path=request_path,
        client_ip=client_ip,
        trace_parent=trace_parent,
        metadata=kwargs,
    )


def _extract_client_ip(request: Request) -> str:
    """Extract real client IP handling proxy scenarios."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def set_context_vars(context: RequestContext) -> list:
    """
    Set context variables from a RequestContext.
    
    Args:
        context: RequestContext to set
        
    Returns:
        List of tokens for resetting context
        
    Note:
        Always use reset_context_vars() to clean up after task completion
        to prevent context leakage between tasks.
    """
    tokens = []
    
    tokens.append(request_id_ctx.set(context.request_id))
    
    if context.user_id is not None:
        tokens.append(user_id_ctx.set(context.user_id))
    
    if context.correlation_id is not None:
        tokens.append(correlation_id_ctx.set(context.correlation_id))
    
    if context.request_path is not None:
        tokens.append(request_path_ctx.set(context.request_path))
    
    if context.client_ip is not None:
        tokens.append(client_ip_ctx.set(context.client_ip))
    
    if context.trace_parent is not None:
        tokens.append(trace_parent_ctx.set(context.trace_parent))
    
    return tokens


def reset_context_vars(tokens: list) -> None:
    """
    Reset context variables using tokens.
    
    Args:
        tokens: List of tokens returned by set_context_vars()
    """
    for token in tokens:
        try:
            request_id_ctx.reset(token)
        except ValueError:
            pass  # Token may not match current context


async def propagate_context(
    context: RequestContext,
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    Execute a function with propagated request context.
    
    This ensures that context variables are set before execution and
    properly cleaned up afterward to prevent context leakage.
    
    Args:
        context: RequestContext to propagate
        func: Async or sync function to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from func execution
        
    Example:
        async def background_task(data):
            request_id = get_request_id()
            logger.info(f"Processing with request_id: {request_id}")
            
        # Schedule with context propagation
        context = capture_request_context(request)
        asyncio.create_task(
            propagate_context(context, background_task, data)
        )
    """
    tokens = []
    try:
        # Set context variables
        tokens = set_context_vars(context)
        
        # Log context propagation for tracing
        logger.debug(
            f"Context propagated: request_id={context.request_id}, "
            f"user_id={context.user_id}, correlation_id={context.correlation_id}"
        )
        
        # Execute the function
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
            
    finally:
        # Always reset context to prevent leakage
        reset_context_vars(tokens)


def propagate_context_sync(
    context: RequestContext,
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    Synchronous version of propagate_context for thread pools.
    
    Args:
        context: RequestContext to propagate
        func: Sync function to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from func execution
    """
    tokens = []
    try:
        tokens = set_context_vars(context)
        return func(*args, **kwargs)
    finally:
        reset_context_vars(tokens)


def create_task_with_context(
    context: RequestContext,
    coro,
    **kwargs
) -> asyncio.Task:
    """
    Create an asyncio.Task with context propagation.
    
    Args:
        context: RequestContext to propagate
        coro: Coroutine to execute
        **kwargs: Additional arguments for asyncio.create_task
        
    Returns:
        asyncio.Task: Created task with propagated context
        
    Example:
        context = capture_request_context(request)
        task = create_task_with_context(
            context,
            process_data(data)
        )
    """
    async def wrapped():
        return await propagate_context(context, lambda: coro)
    
    return asyncio.create_task(wrapped(), **kwargs)


def with_request_context(func: Callable) -> Callable:
    """
    Decorator to automatically propagate request context.
    
    The decorated function must receive 'context' as first argument.
    
    Example:
        @with_request_context
        async def process_data(context: RequestContext, data: dict):
            # context is automatically set in contextvars
            request_id = get_request_id()
            ...
    """
    @wraps(func)
    async def wrapper(context: RequestContext, *args, **kwargs):
        return await propagate_context(context, func, context, *args, **kwargs)
    
    return wrapper


# Getter functions for accessing context variables

def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_ctx.get()


def get_user_id() -> Optional[int]:
    """Get current user ID from context."""
    return user_id_ctx.get()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_ctx.get()


def get_trace_parent() -> Optional[str]:
    """Get current W3C trace parent from context."""
    return trace_parent_ctx.get()


def get_full_context() -> Dict[str, Any]:
    """Get full context as dictionary for logging/debugging."""
    return {
        "request_id": request_id_ctx.get(),
        "user_id": user_id_ctx.get(),
        "correlation_id": correlation_id_ctx.get(),
        "request_path": request_path_ctx.get(),
        "client_ip": client_ip_ctx.get(),
        "trace_parent": trace_parent_ctx.get(),
    }


class ContextPropagator:
    """
    Context manager for temporarily setting request context.
    
    Usage:
        context = capture_request_context(request)
        with ContextPropagator(context):
            # Context is available here
            logger.info(f"Processing {get_request_id()}")
        # Context is automatically cleaned up
    """
    
    def __init__(self, context: RequestContext):
        self.context = context
        self.tokens: list = []
    
    def __enter__(self):
        self.tokens = set_context_vars(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        reset_context_vars(self.tokens)
        return False
    
    async def __aenter__(self):
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


class TracingContextFilter(logging.Filter):
    """
    Logging filter that injects tracing context into log records.
    
    Adds request_id, user_id, correlation_id, and trace_parent to log records
    for structured logging and distributed tracing.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        record.user_id = user_id_ctx.get() or "-"
        record.correlation_id = correlation_id_ctx.get() or "-"
        record.trace_parent = trace_parent_ctx.get() or "-"
        return True
