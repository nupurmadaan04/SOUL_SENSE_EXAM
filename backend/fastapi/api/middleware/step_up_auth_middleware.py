"""
Step-Up Authentication Middleware (#1245)

This middleware enforces step-up authentication for privileged/sensitive operations.
Routes marked as requiring step-up auth will be blocked unless the user has
recently completed step-up verification.
"""

import logging
from typing import Optional, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.auth_service import AuthService
from ..services.db_router import get_db_session
from ..models import User

logger = logging.getLogger(__name__)


class StepUpAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce step-up authentication for privileged operations.

    This middleware:
    1. Checks if the current route requires step-up authentication
    2. Validates that the user has recent step-up verification for the required purpose
    3. Blocks access if step-up auth is missing or expired
    """

    def __init__(self, app, privileged_routes: Optional[List[dict]] = None):
        """
        Initialize middleware with privileged route configuration.

        Args:
            privileged_routes: List of route configs, each with:
                - path: URL path pattern (e.g., "/users/me")
                - methods: List of HTTP methods (e.g., ["DELETE"])
                - purpose: Step-up purpose identifier (e.g., "delete_account")
        """
        super().__init__(app)
        self.privileged_routes = privileged_routes or [
            {
                "path": "/users/me",
                "methods": ["DELETE"],
                "purpose": "delete_account"
            },
            {
                "path": "/auth/2fa/disable",
                "methods": ["POST"],
                "purpose": "disable_2fa"
            }
        ]

    async def dispatch(self, request: Request, call_next):
        # Check if this route requires step-up authentication
        route_config = self._get_route_config(request)
        if not route_config:
            # Route doesn't require step-up auth
            return await call_next(request)

        try:
            # Extract user and session info
            user = getattr(request.state, "user", None)
            session_id = getattr(request.state, "session_id", None)

            if not user or not session_id:
                # No authenticated user, let auth middleware handle it
                return await call_next(request)

            # Get database session
            db = get_db_session()
            auth_service = AuthService(db)

            # Check if user has valid step-up auth for this purpose
            has_valid_auth = await auth_service.check_step_up_auth_valid(
                user_id=user.id,
                session_id=session_id,
                purpose=route_config["purpose"],
                max_age_minutes=30  # Valid for 30 minutes after verification
            )

            if not has_valid_auth:
                logger.warning(
                    f"Blocked privileged operation without step-up auth: "
                    f"user={user.username}, path={request.url.path}, method={request.method}, "
                    f"purpose={route_config['purpose']}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Step-up authentication required for this operation. "
                           f"Please complete step-up verification first."
                )

            # Step-up auth is valid, allow the request
            logger.info(
                f"Allowed privileged operation with valid step-up auth: "
                f"user={user.username}, path={request.url.path}, purpose={route_config['purpose']}"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Step-up auth middleware error: {e}")
            # On middleware error, allow request to continue (fail open for security)
            logger.warning("Step-up auth middleware failed, allowing request to proceed")

        return await call_next(request)

    def _get_route_config(self, request: Request) -> Optional[dict]:
        """
        Check if the current request matches a privileged route configuration.

        Returns route config dict if matched, None otherwise.
        """
        request_path = request.url.path
        request_method = request.method

        for route in self.privileged_routes:
            # Simple path matching (could be enhanced with regex/wildcards)
            if route["path"] in request_path and request_method in route["methods"]:
                return route

        return None