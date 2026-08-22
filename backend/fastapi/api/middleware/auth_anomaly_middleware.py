"""
Auth Anomaly Detection Middleware #1263
========================================

Middleware for real-time authentication anomaly detection and enforcement.
Integrates with the authentication pipeline to detect suspicious behavior
and apply appropriate security measures.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.auth_anomaly_service import AuthAnomalyService, RiskLevel, EnforcementAction
from ..services.db_router import get_db
from ..utils.network import get_real_ip
from ..config import get_settings_instance

logger = logging.getLogger(__name__)
settings = get_settings_instance()


from starlette.middleware.base import BaseHTTPMiddleware

class AuthAnomalyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detecting authentication anomalies and enforcing security measures.
    Integrates with FastAPI authentication pipeline.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Only process authentication-related endpoints
        if not self._is_auth_endpoint(request.url.path):
            return await call_next(request)

        # Extract request data for anomaly detection
        ip_address = get_real_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")

        try:
            from ..services.db_service import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                anomaly_service = AuthAnomalyService(db)
                if request.url.path == "/api/v1/auth/login" and request.method == "POST":
                    await self._handle_login_attempt(request, ip_address, user_agent, anomaly_service, db)
        except Exception as e:
            logger.debug(f"Error in anomaly middleware: {e}")

        return await call_next(request)

    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if the request path is authentication-related"""
        auth_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/verify-2fa"
        ]
        return any(path.startswith(auth_path) for auth_path in auth_paths)

    async def _handle_login_attempt(
        self,
        request: Request,
        ip_address: str,
        user_agent: str,
        anomaly_service: AuthAnomalyService,
        db: AsyncSession
    ) -> None:
        """Handle anomaly detection for login attempts"""
        try:
            # Parse request body to get identifier
            body = await request.json()
            identifier = body.get("identifier", "")

            # Calculate risk score for this login attempt
            risk_score = await anomaly_service.calculate_risk_score(
                user_id=None,  # We don't know the user yet
                identifier=identifier,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=""  # Could be extracted from request if available
            )

            # Log anomaly if risk score is above threshold
            if risk_score.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await anomaly_service.log_anomaly_event(
                    user_id=None,
                    anomaly_type=risk_score.triggered_rules[0] if risk_score.triggered_rules else "unknown",
                    risk_score=risk_score,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"endpoint": "login", "pre_auth_check": True}
                )

            # Apply enforcement actions for high-risk attempts
            if risk_score.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._apply_enforcement_action(risk_score.recommended_action, request)

        except Exception as e:
            logger.error(f"Error in login attempt anomaly detection: {e}")
            # Don't block login if anomaly detection fails

    async def _apply_enforcement_action(self, action: EnforcementAction, request: Request) -> None:
        """Apply the recommended enforcement action"""
        if action == EnforcementAction.RATE_LIMIT:
            # Add rate limiting headers or delay
            request.state.anomaly_enforcement = "rate_limited"
            logger.warning(f"Applied rate limiting for high-risk login attempt from {get_real_ip(request)}")

        elif action == EnforcementAction.TEMPORARY_LOCK:
            # This would be handled by the auth service after user identification
            request.state.anomaly_enforcement = "temporary_lock_recommended"
            logger.warning(f"Temporary lock recommended for high-risk login attempt from {get_real_ip(request)}")

        elif action == EnforcementAction.MFA_CHALLENGE:
            # Force MFA challenge
            request.state.anomaly_enforcement = "mfa_required"
            logger.warning(f"MFA challenge required for high-risk login attempt from {get_real_ip(request)}")

        elif action == EnforcementAction.ACCOUNT_LOCK:
            # Critical risk - block the attempt
            request.state.anomaly_enforcement = "blocked"
            logger.error(f"Blocked critical-risk login attempt from {get_real_ip(request)}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily suspended due to suspicious activity. Please contact support."
            )


# Factory function for dependency injection
async def get_anomaly_service(db: AsyncSession = Depends(get_db)) -> AuthAnomalyService:
    return AuthAnomalyService(db)