from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

def get_user_id(request: Request):
    """
    Key function for slowapi to identify users.
    Prioritizes authenticated user ID/username, falls back to IP.
    """
    # 1. Check if user_id was already set in request.state (by some middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user_id:{user_id}"

    # 2. Extract from JWT manually if limiter runs before dependency injection
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from ..config import get_settings_instance
            settings = get_settings_instance()
            from jose import jwt
            
            # Use jwt_secret_key if available (dev), otherwise SECRET_KEY
            secret = getattr(settings, "jwt_secret_key", settings.SECRET_KEY)
            payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
            username = payload.get("sub")
            if username:
                return f"user:{username}"
        except Exception:
            # Token might be invalid, expired, or for a different scope
            pass
            
    # 3. Fallback to IP address
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_id)
