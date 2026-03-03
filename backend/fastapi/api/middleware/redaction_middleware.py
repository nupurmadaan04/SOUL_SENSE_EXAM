import json
import logging
from typing import List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.redaction import redact_data
from ..config import get_settings_instance
from starlette.concurrency import iterate_in_threadpool

logger = logging.getLogger(__name__)

# New redaction_middleware implementation
async def redaction_middleware(request: Request, call_next):
    """
    Middleware to redact PII from JSON responses based on user roles and internal bypass.
    """
    response: Response = await call_next(request)

    # 1. Bypass if not JSON or if it's an internal system call (e.g., from another service)
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return response

    # Check for internal bypass header (e.g., set by internal services)
    settings = get_settings_instance()
    internal_bypass_header = getattr(settings, "internal_bypass_header_name", "X-Internal-Bypass")
    if request.headers.get(internal_bypass_header) == "true":
        logger.debug("Redaction middleware bypassed due to internal bypass header.")
        return response

    # 2. Get user roles from request state
    user = getattr(request.state, "user", None)
    roles = []
    if user:
        if getattr(user, "is_admin", False):
            roles.append("admin")
        if hasattr(user, "roles") and isinstance(user.roles, list):
            roles.extend(user.roles)
    
    # 3. Intercept and redact
    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        data = json.loads(body)
        redacted_data = redact_data(data, roles)
        
        new_content = json.dumps(redacted_data).encode("utf-8")
        
        from fastapi.responses import Response as FAResponse
        return FAResponse(
            content=new_content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type="application/json"
        )
    except json.JSONDecodeError as e:
        logger.debug(f"Redaction middleware skipped non-JSON or malformed content: {e}")
        response.body_iterator = iterate_in_threadpool(iter([body]))
        return response
    except Exception as e:
        logger.error(f"An unexpected error occurred in redaction middleware: {e}", exc_info=True)
        response.body_iterator = iterate_in_threadpool(iter([body]))
        return response
