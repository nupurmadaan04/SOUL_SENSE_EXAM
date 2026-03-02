import time
import logging
import asyncio
from typing import Tuple, Dict, Any, Optional
from fastapi import Request, HTTPException, status, Response
import redis.asyncio as redis
from ..config import get_settings_instance
from ..utils.network import get_real_ip

logger = logging.getLogger(__name__)
# Enable debug log for rate limiting
logger.setLevel(logging.DEBUG)

# Token Bucket Lua Script for Atomic Operation
# KEYS[1]: unique rate limit key
# ARGV[1]: capacity (max tokens)
# ARGV[2]: refill_rate (tokens per second)
# ARGV[3]: now (timestamp)
# ARGV[4]: amount (tokens requested, usually 1)
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local amount = tonumber(ARGV[4] or 1)

local bucket = redis.call('HMGET', key, 'last_refill_time', 'current_tokens')
local last_refill_time = tonumber(bucket[1]) or now
local current_tokens = tonumber(bucket[2]) or capacity

-- Refill tokens based on time passed
local delta = math.max(0, now - last_refill_time)
current_tokens = math.min(capacity, current_tokens + (delta * refill_rate))

local allowed = false
if current_tokens >= amount then
    current_tokens = current_tokens - amount
    allowed = true
end

-- Save state and set TTL (slightly more than it takes to fully refill)
redis.call('HMSET', key, 'last_refill_time', now, 'current_tokens', current_tokens)
redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 60)

return {allowed and 1 or 0, math.floor(current_tokens)}
"""

class TokenBucketLimiter:
    def __init__(self, key_prefix: str, default_capacity: int = 10, default_refill_rate: float = 1.0):
        self.key_prefix = key_prefix
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self.settings = get_settings_instance()
        self._redis = None
        self._lua_sha = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                # Fast timeout for Redis if it's down
                self._redis = redis.from_url(
                    self.settings.redis_url, 
                    decode_responses=True,
                    socket_timeout=1.0, 
                    socket_connect_timeout=1.0,
                    retry_on_timeout=False
                )
                # Pre-load the script
                self._lua_sha = await self._redis.script_load(TOKEN_BUCKET_SCRIPT)
                logger.debug(f"Token Bucket Lua loaded for {self.key_prefix}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis for rate limiting ({self.key_prefix}): {e}")
                self._redis = None
        return self._redis

    async def is_rate_limited(self, identifier: str, capacity: int = None, refill_rate: float = None) -> Tuple[bool, int]:
        """
        Returns (is_allowed, remaining_tokens)
        
        Ensures Redis connection cleanup on ALL exception paths including:
        - asyncio.CancelledError (request cancellation)
        - redis.TimeoutError (Redis timeout)
        - socket timeouts (network issues)
        - Script execution errors
        """
        cap = capacity or self.default_capacity
        refill = refill_rate or self.default_refill_rate
        
        red = await self._get_redis()
        if not red:
            logger.debug(f"Redis not available for {identifier}, using fallback.")
            return self._in_memory_fallback(identifier, cap)

        key = f"rl:tb:{self.key_prefix}:{identifier}"
        try:
            now = time.time()
            # Use evalsha for performance
            # This operation may raise:
            # - asyncio.CancelledError: request cancelled while executing
            # - redis.TimeoutError: Redis connection timeout
            # - redis.ConnectionError: connection pool exhausted
            try:
                result = await asyncio.wait_for(
                    red.evalsha(self._lua_sha, 1, key, cap, refill, now, 1),
                    timeout=2.0  # 2 second timeout for Lua script execution
                )
            except asyncio.TimeoutError:
                logger.warning(f"Redis Lua script timeout for {identifier}, using fallback")
                return self._in_memory_fallback(identifier, cap)
            except asyncio.CancelledError:
                # Client cancelled request - ensure cleanup before re-raising
                logger.debug(f"Rate limit check cancelled for {identifier}")
                raise
            
            allowed = result[0] == 1
            remaining = result[1]
            logger.debug(f"Rate Limit Check: {identifier} | Result: {allowed} | Remaining: {remaining}")
            return allowed, remaining
        except asyncio.CancelledError:
            # Re-raise cancellation after ensuring cleanup
            logger.debug(f"Request cancelled at rate limit check for {identifier}")
            raise
        except (redis.TimeoutError, redis.ConnectionError) as e:
            # Connection pool issues - use fallback and reset Redis connection
            logger.warning(f"Redis connection issue for {identifier}: {type(e).__name__}: {e}")
            # Reset the connection so future attempts will reconnect
            self._redis = None
            self._lua_sha = None
            return self._in_memory_fallback(identifier, cap)
        except Exception as e:
            logger.error(f"Token bucket LUA error: {e}", exc_info=True)
            return self._in_memory_fallback(identifier, cap)

    def _in_memory_fallback(self, identifier: str, capacity: int) -> Tuple[bool, int]:
        """Simple fixed-window fallback if Redis is down."""
        if not hasattr(self, "_fallback_store"):
            self._fallback_store = {} # key -> [count, window_start]
        
        now = time.time()
        window = 60 # 1 minute fixed window
        
        state = self._fallback_store.get(identifier)
        if not state or (now - state[1]) > window:
            self._fallback_store[identifier] = [1, now]
            return True, capacity - 1
        
        if state[0] < capacity:
            state[0] += 1
            return True, capacity - state[0]
        
        return False, 0

# Default Limiters
analytics_limiter = TokenBucketLimiter("analytics", default_capacity=30, default_refill_rate=0.5) # 30 burst, 0.5/sec refill
auth_limiter = TokenBucketLimiter("auth", default_capacity=5, default_refill_rate=0.1) # 5 burst, 1 every 10 sec

async def rate_limit_analytics(request: Request, response: Response):
    """Dependency for analytics endpoints."""
    try:
        client_ip = get_real_ip(request)
        
        # Dynamic Limit Logic
        capacity = 30
        refill_rate = 0.5 # 1 token every 2 seconds
        
        user = getattr(request.state, "user", None)
        if user and getattr(user, "is_premium", False):
            capacity = 100
            refill_rate = 5.0
        elif user and getattr(user, "is_admin", False):
            return

        allowed, remaining = await analytics_limiter.is_rate_limited(client_ip, capacity, refill_rate)
        
        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Token bucket empty.",
                headers={"Retry-After": "10"}
            )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"FATAL ERROR in rate_limit_analytics: {e}")
        logger.error(traceback.format_exc())
        return # Allow request on unknown error

async def rate_limit_auth(request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining = await auth_limiter.is_rate_limited(client_ip)
    
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail="Too many auth attempts."
        )
