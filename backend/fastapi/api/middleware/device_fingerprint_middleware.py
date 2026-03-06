"""
Device Fingerprint Validation Middleware

This middleware validates device fingerprints on authenticated requests to detect
session hijacking attempts and enforce session binding with drift tolerance.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..utils.device_fingerprinting import DeviceFingerprinting, DeviceFingerprint
from ..models import UserSession
from ..services.db_router import get_db_session

logger = logging.getLogger(__name__)


class DeviceFingerprintValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate device fingerprints on authenticated requests.

    This middleware:
    1. Extracts current device fingerprint from request
    2. Compares with stored fingerprint for the session
    3. Allows controlled drift tolerance
    4. Logs and blocks suspicious activity
    """

    async def dispatch(self, request: Request, call_next):
        # Skip validation for non-authenticated endpoints
        if not self._requires_authentication(request):
            return await call_next(request)

        try:
            # Extract session ID from request (could be from JWT token or session cookie)
            session_id = self._extract_session_id(request)
            if not session_id:
                # No session to validate, continue
                return await call_next(request)

            # Get database session
            db = get_db_session()

            # Get stored session with device fingerprint
            stored_session = await self._get_session_with_fingerprint(db, session_id)
            if not stored_session:
                # Session not found, continue (let auth middleware handle this)
                return await call_next(request)

            # Extract current device fingerprint
            current_fingerprint = DeviceFingerprinting.extract_fingerprint_from_request(request)

            # Validate fingerprint
            is_valid, drift_score, reason = await self._validate_device_fingerprint(
                db, stored_session, current_fingerprint, request
            )

            if not is_valid:
                logger.warning(
                    f"Device fingerprint validation failed for session {session_id}: {reason} "
                    f"(drift_score: {drift_score:.3f})"
                )

                # Log security event
                await self._log_security_event(
                    db, session_id, stored_session.user_id, "device_fingerprint_mismatch",
                    {
                        "drift_score": drift_score,
                        "reason": reason,
                        "ip_address": current_fingerprint.ip_address,
                        "user_agent": current_fingerprint.user_agent
                    }
                )

                # Return 401 Unauthorized for fingerprint mismatch
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session validation failed. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Fingerprint valid, continue with request
            return await call_next(request)

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error in device fingerprint validation: {e}")
            # On error, allow request to continue (fail open for availability)
            return await call_next(request)

    def _requires_authentication(self, request: Request) -> bool:
        """Check if the request requires authentication."""
        # Skip authentication check for public endpoints
        public_paths = [
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/captcha",
            "/api/v1/server-id"
        ]

        return not any(request.url.path.startswith(path) for path in public_paths)

    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request (JWT token or session cookie)."""
        # Try to get from Authorization header (Bearer token)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Extract session ID from JWT token (jti claim)
            try:
                from jose import jwt
                from ..config import get_settings_instance
                settings = get_settings_instance()

                payload = jwt.get_unverified_claims(token)
                return payload.get("jti")  # JWT ID claim
            except Exception:
                pass

        # Try to get from session cookie
        session_cookie = request.cookies.get("session_id")
        if session_cookie:
            return session_cookie

        return None

    async def _get_session_with_fingerprint(self, db: AsyncSession, session_id: str) -> Optional[UserSession]:
        """Get user session with device fingerprint data."""
        stmt = select(UserSession).where(
            UserSession.session_id == session_id,
            UserSession.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_device_fingerprint(
        self,
        db: AsyncSession,
        stored_session: UserSession,
        current_fingerprint: DeviceFingerprint,
        request: Request
    ) -> tuple[bool, float, str]:
        """Validate current device fingerprint against stored fingerprint."""

        # Reconstruct stored fingerprint from database
        stored_fingerprint_data = {
            'fingerprint_hash': stored_session.device_fingerprint_hash,
            'user_agent': stored_session.device_user_agent or '',
            'ip_address': stored_session.ip_address or '',
            'accept_language': stored_session.device_accept_language or '',
            'accept_encoding': '',  # Not stored in current model
            'screen_resolution': stored_session.device_screen_resolution,
            'timezone_offset': stored_session.device_timezone_offset,
            'platform': stored_session.device_platform,
            'plugins': stored_session.device_plugins_hash,
            'canvas_fingerprint': stored_session.device_canvas_fingerprint,
            'webgl_fingerprint': stored_session.device_webgl_fingerprint,
            'created_at': stored_session.device_fingerprint_created_at
        }

        stored_fingerprint = DeviceFingerprinting.normalize_fingerprint_data(stored_fingerprint_data)

        # Check if fingerprints match exactly
        if current_fingerprint.fingerprint_hash == stored_fingerprint.fingerprint_hash:
            return True, 0.0, "Exact fingerprint match"

        # Check if drift is acceptable
        is_acceptable, drift_score, reason = DeviceFingerprinting.is_drift_acceptable(
            stored_fingerprint, current_fingerprint
        )

        if is_acceptable:
            # Update session with new fingerprint data (drift tolerance)
            await self._update_session_fingerprint(db, stored_session, current_fingerprint)

        return is_acceptable, drift_score, reason

    async def _update_session_fingerprint(
        self,
        db: AsyncSession,
        session: UserSession,
        fingerprint: DeviceFingerprint
    ):
        """Update session with new fingerprint data."""
        session.device_fingerprint_hash = fingerprint.fingerprint_hash
        session.device_user_agent = fingerprint.user_agent
        session.device_accept_language = fingerprint.accept_language
        session.device_screen_resolution = fingerprint.screen_resolution
        session.device_timezone_offset = fingerprint.timezone_offset
        session.device_platform = fingerprint.platform
        session.device_plugins_hash = fingerprint.plugins
        session.device_canvas_fingerprint = fingerprint.canvas_fingerprint
        session.device_webgl_fingerprint = fingerprint.webgl_fingerprint
        session.device_fingerprint_created_at = fingerprint.created_at
        session.last_activity = fingerprint.created_at

        await db.commit()

    async def _log_security_event(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: Optional[int],
        event_type: str,
        details: dict
    ):
        """Log security event for audit purposes."""
        try:
            from ..models import AuditLog
            from datetime import datetime, timezone
            UTC = timezone.utc

            audit_log = AuditLog(
                event_id=f"fp_{session_id}_{datetime.now(UTC).timestamp()}",
                user_id=user_id,
                event_type="security",
                severity="warning",
                resource_type="session",
                resource_id=session_id,
                action="fingerprint_validation",
                outcome="failure" if event_type == "device_fingerprint_mismatch" else "success",
                details=str(details),
                ip_address=details.get("ip_address", ""),
                user_agent=details.get("user_agent", "")
            )

            db.add(audit_log)
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")