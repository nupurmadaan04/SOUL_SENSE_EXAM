import time
from typing import Dict, Optional, Tuple
from cachetools import TTLCache
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

import threading

class RateLimiter:
    """
    In-memory rate limiter using sliding window logic.
    Supports both IP-based and Identifier-based (email/username) limiting.
    Thread-safe.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # key -> list of timestamps
        self.cache: TTLCache = TTLCache(maxsize=10000, ttl=window_seconds)
        self.lock = threading.Lock()

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if the key is rate limited.
        Returns (is_limited, remaining_seconds)
        """
        with self.lock:
            now = time.time()
            timestamps = self.cache.get(key, [])
            
            # Filter timestamps within the window
            valid_timestamps = [ts for ts in timestamps if now - ts < self.window_seconds]
            
            if len(valid_timestamps) >= self.max_requests:
                oldest_ts = valid_timestamps[0]
                wait_time = int(self.window_seconds - (now - oldest_ts))
                return True, max(0, wait_time)
            
            # Add current timestamp
            valid_timestamps.append(now)
            self.cache[key] = valid_timestamps
            return False, 0

# Global limiters
login_limiter = RateLimiter(max_requests=10, window_seconds=60)
registration_limiter = RateLimiter(max_requests=10, window_seconds=60)
password_reset_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Analytics limiter: 30 requests per minute
analytics_limiter = RateLimiter(max_requests=30, window_seconds=60)

async def rate_limit_analytics(request: Request):
    is_limited, wait_time = analytics_limiter.is_rate_limited(request.client.host)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many analytics requests. Please wait {wait_time}s."
        )
