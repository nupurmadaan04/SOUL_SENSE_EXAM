import json
import logging
import hashlib
from functools import wraps
from typing import Any, Callable, Optional
import redis
from ..config import get_settings_instance

logger = logging.getLogger("api.cache")

class RedisCache:
    """
    Utility class for Redis-based caching.
    """
    def __init__(self):
        settings = get_settings_instance()
        self.enabled = False
        try:
            if settings.redis_url:
                self.client = redis.from_url(settings.redis_url)
            else:
                self.client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password,
                    db=settings.redis_db,
                    decode_responses=True
                )
            # Short timeout for ping to avoid hanging startup
            self.client.execute_command('CLIENT', 'SETNAME', 'soulsense_cache')
            self.client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis cache disabled: Could not connect to Redis: {e}")

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict, prefix: str) -> str:
        """Generate a stable cache key."""
        # Clean args to ignore db sessions or self
        clean_args = []
        for arg in args:
            # Skip common non-serializable objects
            if hasattr(arg, 'execute') or hasattr(arg, 'commit'): # Likely a DB session
                continue
            if hasattr(arg, '__class__') and arg.__class__.__name__ in ['AssessmentService', 'QuestionService', 'ExamService', 'JournalService']:
                continue
            clean_args.append(str(arg))
            
        # Clean kwargs
        clean_kwargs = {k: v for k, v in kwargs.items() if k not in ['db', 'session']}
        
        arg_str = f"{func_name}:{json.dumps(clean_args)}:{json.dumps(clean_kwargs, sort_keys=True)}"
        arg_hash = hashlib.md5(arg_str.encode()).hexdigest()
        return f"{prefix}:{func_name}:{arg_hash}"

    def cache(self, ttl: int = 300, prefix: str = "ssc"):
        """
        Decorator to cache async function results in Redis.
        Result must be JSON serializable.
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)

                cache_key = self._generate_key(func.__name__, args, kwargs, prefix)

                try:
                    cached_val = self.client.get(cache_key)
                    if cached_val:
                        logger.debug(f"Cache hit: {cache_key}")
                        return json.loads(cached_val)
                except Exception as e:
                    logger.error(f"Cache retrieval error for {cache_key}: {e}")

                # Call the actual function
                result = await func(*args, **kwargs)

                try:
                    # Only cache if result is not None
                    if result is not None:
                        self.client.setex(cache_key, ttl, json.dumps(result))
                        logger.debug(f"Cache miss, saved: {cache_key}")
                except Exception as e:
                    logger.error(f"Cache storage error for {cache_key}: {e}")

                return result
            return wrapper
        return decorator

    def invalidate(self, pattern: str):
        """Invalidate cache keys matching a pattern."""
        if not self.enabled:
            return
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
        except Exception as e:
            logger.error(f"Cache invalidation error for {pattern}: {e}")

# Global cache instance
cache_manager = RedisCache()
