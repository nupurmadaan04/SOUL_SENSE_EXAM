
import json
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from ..services.cache_service import cache_service
from ..config import get_settings_instance

logger = logging.getLogger(__name__)
settings = get_settings_instance()

MAINTENANCE_KEY = "soulsense:maintenance_state"

class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip for internal health checks and docs
        if request.url.path in ("/health", "/ready", "/api/v1/health", "/api/v1/ready", "/docs", "/openapi.json"):
            return await call_next(request)

        # 2. Check Redis for maintenance state
        state = await cache_service.get(MAINTENANCE_KEY)
        if not state or not isinstance(state, dict):
            return await call_next(request)

        mode = state.get("mode", "NORMAL")
        if mode == "NORMAL":
            return await call_next(request)

        # 3. Check if user is an Admin (can bypass)
        is_admin = False
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                from jose import jwt, JWTError
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
                # Check for is_admin claim or equivalent
                is_admin = payload.get("is_admin", False)
            except (JWTError, Exception):
                pass

        # 4. Handle READ_ONLY mode
        if mode == "READ_ONLY":
            # Only Allow GET, HEAD, OPTIONS
            if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
                response = await call_next(request)
                response.headers["X-Maintenance-Mode"] = "READ_ONLY"
                return response
            
            # If it's a write (POST/PUT/PATCH/DELETE) and NOT an admin, block it
            if not is_admin:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "READ_ONLY_MODE",
                        "message": state.get("reason", "System is currently in read-only mode for maintenance."),
                        "retry_after": state.get("retry_after", 60)
                    },
                    headers={"Retry-After": str(state.get("retry_after", 60))}
                )

        # 5. Handle MAINTENANCE mode
        if mode == "MAINTENANCE":
            # Block ALL requests for non-admins
            if not is_admin:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "MAINTENANCE_MODE",
                        "message": state.get("reason", "System is down for scheduled maintenance."),
                        "retry_after": state.get("retry_after", 60)
                    },
                    headers={"Retry-After": str(state.get("retry_after", 60))}
                )

        # Allowed (either admin or normal)
        return await call_next(request)
