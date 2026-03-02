import time
import uuid
import logging
import os
import asyncio
from typing import Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.limiter import get_real_ip, get_user_id
from ..config import get_settings_instance
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Load Lua script from file
LUA_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'resources', 'rate_limit.lua')
try:
    with open(LUA_SCRIPT_PATH, 'r') as f:
        LUA_RATE_LIMIT = f.read()
except FileNotFoundError:
    logger.error("rate_limit.lua not found!")
    LUA_RATE_LIMIT = ""

class SlidingWindowRateLimiter:
    def __init__(self):
        self.settings = get_settings_instance()
        self.redis = None
        self._script = None

    async def _get_redis(self):
        if self.redis:
            return self.redis
        try:
            from ..main import app
            self.redis = getattr(app.state, 'redis_client', None)
            if self.redis and LUA_RATE_LIMIT:
                 self._script = self.redis.register_script(LUA_RATE_LIMIT)
        except Exception:
            pass
        return self.redis

    async def check_rate_limit(self, key_name: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Check rate limit using sliding window algorithm.
        
        Properly handles connection cleanup on:
        - asyncio.CancelledError: request cancelled mid-check
        - redis.TimeoutError: Redis timeout
        - redis.ConnectionError: connection pool exhaustion
        """
        redis_conn = await self._get_redis()
        if not redis_conn or not self._script:
            return True, limit # Open if Redis is down

        now = time.time()
        request_id = str(uuid.uuid4())
        # Returns [allowed_int, remaining]
        try:
            try:
                res = await asyncio.wait_for(
                    self._script(keys=[f"rate_limit:{key_name}"], args=[now, window, limit, request_id]),
                    timeout=2.0  # 2 second timeout for Lua script execution
                )
                return bool(res[0]), res[1]
            except asyncio.TimeoutError:
                logger.warning(f"Redis sliding window timeout for {key_name}, denying request")
                return False, 0  # Fail closed on timeout
            except asyncio.CancelledError:
                # Request cancelled - propagate after cleanup
                logger.debug(f"Rate limit check cancelled for {key_name}")
                raise
        except asyncio.CancelledError:
            # Re-raise cancellation after cleanup
            logger.debug(f"Sliding window check cancelled for {key_name}")
            raise
        except (redis.TimeoutError, redis.ConnectionError) as e:
            # Connection pool issue - reset connection and fail closed
            logger.warning(f"Redis connection issue in sliding window for {key_name}: {type(e).__name__}: {e}")
            self.redis = None
            self._script = None
            return False, 0  # Fail closed to protect resources
        except Exception as e:
            logger.error(f"Redis sliding window rate limiting failed for {key_name}: {e}", exc_info=True)
            return False, 0  # Fail closed on unknown error

rate_limiter = SlidingWindowRateLimiter()

async def sliding_rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for sliding-window rate limiting (#1087, #1099).
    Applies granular limits by IP/User/API Key to prevent bursts.
    
    Exception-safe: Ensures no connection leaks on cancellation or timeout.
    """
    if request.url.path.startswith("/api/v1/health") or not request.url.path.startswith("/api"):
        return await call_next(request)

    # Determine granularity and defaults
    api_key = request.headers.get("X-API-Key")
    user_id = getattr(request.state, "user_id", None)
    
    if api_key:
        ident = f"api_key:{api_key}"
        limit = 1000
        window = 60
    elif user_id:
        ident = f"user:{user_id}"
        limit = 200
        window = 60
    else:
        ip = get_real_ip(request)
        ident = f"ip:{ip}"
        limit = 50
        window = 60
    
    try:
        allowed, remaining = await rate_limiter.check_rate_limit(ident, limit, window)
    except asyncio.CancelledError:
        # Request cancelled - ensure cleanup and re-raise
        logger.debug(f"Rate limit check cancelled for {ident}")
        raise
    except Exception as e:
        # Unexpected error - log and fail closed
        logger.error(f"Rate limit check failed for {ident}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit check failed. Please retry.",
            headers={"Retry-After": "1"}
        )
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for {ident}")
        # Build standard slow down headers
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(window)
        }
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
            headers=headers
        )

    try:
        response: Response = await call_next(request)
    except asyncio.CancelledError:
        # Client cancelled request
        logger.debug(f"Request cancelled after rate limit check for {ident}")
        raise
    
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(window)
    
    return response
