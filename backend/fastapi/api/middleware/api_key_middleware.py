# api_key_middleware.py
"""
API Key Middleware for Fine-Grained Access Control (#1264)

FastAPI middleware that:
- Extracts API keys from request headers
- Validates keys against the database
- Enforces scope-based access control
- Provides request.state.api_key for downstream handlers
"""

import logging
from typing import Callable, Optional, List
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.api_key_service import ApiKeyService
from ..services.db_service import AsyncSessionLocal

logger = logging.getLogger(__name__)

# API key header name
API_KEY_HEADER = "X-API-Key"

# Exempt paths that don't require API key authentication
_EXEMPT_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/captcha",
    "/api/v1/auth/server-id",
    "/api/v1/analytics/events",  # Public analytics endpoint
}

# Scope requirements for different endpoints
# Maps path patterns to required scopes
SCOPE_REQUIREMENTS = {
    # User management
    "/api/v1/users": {
        "GET": ["users:read"],
        "POST": ["users:write"],
        "PUT": ["users:write"],
        "DELETE": ["admin"],
    },
    "/api/v1/users/": {  # User-specific endpoints
        "GET": ["users:read"],
        "PUT": ["users:write"],
        "DELETE": ["admin"],
    },

    # Payments
    "/api/v1/payments": {
        "GET": ["payments:read"],
        "POST": ["payments:write"],
    },

    # Analytics
    "/api/v1/analytics": {
        "GET": ["analytics:read"],
        "POST": ["analytics:write"],
    },

    # Exams
    "/api/v1/exams": {
        "GET": ["exams:read"],
        "POST": ["exams:write"],
        "PUT": ["exams:write"],
        "DELETE": ["admin"],
    },

    # Journal entries
    "/api/v1/journal": {
        "GET": ["journal:read"],
        "POST": ["journal:write"],
        "PUT": ["journal:write"],
        "DELETE": ["journal:write"],
    },

    # Surveys
    "/api/v1/surveys": {
        "GET": ["surveys:read"],
        "POST": ["surveys:write"],
        "PUT": ["surveys:write"],
    },

    # Notifications
    "/api/v1/notifications": {
        "GET": ["notifications:read"],
        "POST": ["notifications:write"],
    },

    # Settings
    "/api/v1/settings": {
        "GET": ["settings:read"],
        "PUT": ["settings:write"],
    },

    # Admin endpoints
    "/api/v1/admin": {
        "GET": ["admin"],
        "POST": ["admin"],
        "PUT": ["admin"],
        "DELETE": ["admin"],
    },
}


def _is_exempt_path(path: str) -> bool:
    """Check if a path is exempt from API key authentication."""
    if path in _EXEMPT_PATHS:
        return True

    # Check for prefix matches
    for exempt_path in _EXEMPT_PATHS:
        if path.startswith(exempt_path):
            return True

    return False


def _get_required_scopes(path: str, method: str) -> List[str]:
    """
    Get the required scopes for a given path and HTTP method.

    Args:
        path: Request path
        method: HTTP method (GET, POST, etc.)

    Returns:
        List of required scope strings
    """
    # Check for exact path matches first
    if path in SCOPE_REQUIREMENTS:
        method_scopes = SCOPE_REQUIREMENTS[path].get(method, [])
        if method_scopes:
            return method_scopes

    # Check for prefix matches
    for scope_path, method_scopes in SCOPE_REQUIREMENTS.items():
        if path.startswith(scope_path):
            required_scopes = method_scopes.get(method, [])
            if required_scopes:
                return required_scopes

    # Default to read scope for GET requests, write for others
    if method == "GET":
        return ["read"]
    else:
        return ["write"]


async def api_key_middleware(request: Request, call_next: Callable):
    """
    FastAPI middleware for API key authentication and scope validation.

    This middleware:
    1. Checks if the path requires API key authentication
    2. Extracts and validates the API key
    3. Enforces scope requirements
    4. Sets request.state.api_key for downstream use
    """
    path = request.url.path
    method = request.method

    # Skip authentication for exempt paths
    if _is_exempt_path(path):
        return await call_next(request)

    # Get required scopes for this endpoint
    required_scopes = _get_required_scopes(path, method)

    # Extract API key from header
    api_key_header = request.headers.get(API_KEY_HEADER)
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": f"APIKey realm=\"{path}\""},
        )

    # Validate API key
    async with AsyncSessionLocal() as db_session:
        api_key_service = ApiKeyService(db_session)
        api_key_record = await api_key_service.verify_api_key(api_key_header)

        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )

        # Validate scopes
        has_required_scopes = await api_key_service.validate_scopes(
            api_key_record, required_scopes
        )

        if not has_required_scopes:
            logger.warning(
                f"API key {api_key_record.id} lacks required scopes {required_scopes} for {method} {path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {', '.join(required_scopes)}",
            )

        # Store API key info in request state for downstream handlers
        request.state.api_key = api_key_record
        request.state.user_id = api_key_record.user_id

        logger.debug(
            f"API key {api_key_record.id} authenticated for {method} {path} "
            f"with scopes: {api_key_record.scopes}"
        )

    # Continue with the request
    return await call_next(request)


# Dependency for route handlers that need API key info
async def get_api_key(request: Request) -> Optional[object]:
    """
    Dependency to get the current API key from request state.

    Returns:
        ApiKey instance if authenticated with API key, None otherwise
    """
    return getattr(request.state, 'api_key', None)


# Helper function to check scopes in route handlers
def require_scopes(required_scopes: List[str]):
    """
    Dependency factory for requiring specific scopes in route handlers.

    Usage:
        @app.get("/protected")
        async def protected_endpoint(api_key: ApiKey = Depends(require_scopes(["read"]))):
            # Only accessible with 'read' scope
            pass

    Args:
        required_scopes: List of scope strings that are required

    Returns:
        Dependency function that validates scopes
    """
    async def scope_dependency(request: Request) -> object:
        api_key = getattr(request.state, 'api_key', None)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key authentication required",
            )

        # Validate scopes
        async with AsyncSessionLocal() as db_session:
            api_key_service = ApiKeyService(db_session)
            has_scopes = await api_key_service.validate_scopes(api_key, required_scopes)

            if not has_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scopes: {', '.join(required_scopes)}",
                )

            return api_key

    return scope_dependency