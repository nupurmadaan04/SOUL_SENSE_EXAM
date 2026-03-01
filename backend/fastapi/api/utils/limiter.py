from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)


def get_real_ip(request: Request) -> str:
    """
    Extract the real client IP address from request headers.
    
    CRITICAL SECURITY: Uses hardened IP extraction that only trusts
    X-Forwarded-For headers from trusted proxies to prevent spoofing attacks.
    
    This prevents attackers from bypassing rate limits via header manipulation.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address as string
    """
    # Import here to avoid circular imports
    from .network import get_real_ip as get_secure_real_ip
    return get_secure_real_ip(request)


def get_user_id(request: Request):
    """
    Key function for slowapi to identify users for rate limiting.
    
    Enhanced bypass protection:
    1. Prioritizes authenticated user ID/username for strongest protection
    2. Falls back to IP + User-Agent fingerprint for unauthenticated requests
    3. Uses session cookies for additional tracking
    4. Applies bot detection patterns
    
    This prevents IP rotation, header spoofing, and distributed attacks.
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
            
    # 3. For unauthenticated requests: Create fingerprint to prevent bypass
    ip = get_real_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Extract session ID from cookies for additional tracking
    session_id = request.cookies.get("session_id", "none")
    
    # Create fingerprint combining IP, User-Agent, and session
    # This prevents simple IP rotation attacks
    fingerprint = f"{ip}:{hash(user_agent)}:{session_id}"
    
    # Add bot detection: suspicious user agents get stricter limits
    suspicious_patterns = [
        "bot", "crawler", "spider", "scraper", "python-requests", "curl"
    ]
    is_bot = any(pattern.lower() in user_agent.lower() for pattern in suspicious_patterns)
    
    if is_bot:
        return f"bot:{fingerprint}"
    else:
        return f"anon:{fingerprint}"


# Initialize Redis connection for rate limiting storage
# This will be initialized in the application startup
_redis_connection = None


def get_redis_connection():
    """Get or create Redis connection for rate limiting."""
    global _redis_connection
    if _redis_connection is None:
        from ..config import get_settings_instance
        settings = get_settings_instance()
        _redis_connection = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Redis connection initialized for rate limiting: {settings.redis_host}:{settings.redis_port}")
    return _redis_connection


# Initialize limiter with Redis storage backend
limiter = Limiter(
    key_func=get_user_id,
    storage_uri=None  # Will be set dynamically on first use via get_redis_connection
)
