"""
Consent validation middleware for privacy compliance.

This middleware checks user consent before allowing analytics data collection.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Optional
import json

from ..services.analytics_service import AnalyticsService
from ..services.db_service import AsyncSessionLocal


from starlette.middleware.base import BaseHTTPMiddleware

class ConsentValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate user consent before analytics operations.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Check if this is an analytics endpoint
        if self._is_analytics_endpoint(request.url.path):
            # Extract anonymous_id from request
            anonymous_id = self._extract_anonymous_id(request)

            if anonymous_id:
                try:
                    async with AsyncSessionLocal() as db:
                        consent_status = await AnalyticsService.check_analytics_consent_async(db, anonymous_id)

                        if not consent_status.get('analytics_consent_given', False):
                            # Consent not given, block analytics
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "error": "Analytics consent required",
                                    "message": "User has not provided consent for analytics data collection",
                                    "consent_required": True
                                }
                            )
                except Exception as e:
                    # Log error but don't block - fail open for now
                    print(f"Consent validation error: {e}")

        return await call_next(request)

    def _is_analytics_endpoint(self, path: str) -> bool:
        """
        Check if the request path is an analytics endpoint.
        """
        analytics_paths = [
            "/api/v1/analytics/",
            "/api/v1/analytics/events",
            "/api/v1/analytics/track",
            "/api/v1/analytics/log"
        ]
        return any(path.startswith(analytics_path) for analytics_path in analytics_paths)

    def _extract_anonymous_id(self, request: Request) -> Optional[str]:
        """
        Extract anonymous_id from request headers or query params.
        """
        # Check headers first
        anonymous_id = request.headers.get("X-Anonymous-ID")
        if anonymous_id:
            return anonymous_id

        # Check query parameters
        return request.query_params.get("anonymous_id")