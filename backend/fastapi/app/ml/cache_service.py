"""
Caching Service for Analytics Performance Optimization.

Provides Redis-based caching for expensive ML computations and API responses.
"""

import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import redis
import pickle

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for analytics."""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except redis.ConnectionError:
            logger.warning("Redis not available, caching disabled")
            self.enabled = False
        except Exception as e:
            logger.warning(f"Cache initialization failed: {e}")
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                # Try to parse as JSON first, then pickle
                try:
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return pickle.loads(data.encode('latin1'))
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled:
            return False

        try:
            # Try to serialize as JSON first, then pickle
            try:
                data = json.dumps(value, default=str)
            except (TypeError, ValueError):
                data = pickle.dumps(value).decode('latin1')

            return self.redis_client.setex(key, ttl_seconds, data)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled:
            return False

        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enabled:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False

    def clear_user_cache(self, username: str) -> int:
        """Clear all cache entries for a specific user."""
        if not self.enabled:
            return 0

        try:
            pattern = f"user:{username}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear failed for user {username}: {e}")
            return 0

    # Analytics-specific cache methods
    def get_patterns_cache(self, username: str, time_range: str) -> Optional[Dict]:
        """Get cached pattern analysis results."""
        key = f"user:{username}:patterns:{time_range}"
        return self.get(key)

    def set_patterns_cache(self, username: str, time_range: str, data: Dict, ttl: int = 1800):
        """Cache pattern analysis results (30 min TTL)."""
        key = f"user:{username}:patterns:{time_range}"
        self.set(key, data, ttl)

    def get_correlations_cache(self, username: str, metrics_hash: str) -> Optional[Dict]:
        """Get cached correlation analysis results."""
        key = f"user:{username}:correlations:{metrics_hash}"
        return self.get(key)

    def set_correlations_cache(self, username: str, metrics_hash: str, data: Dict, ttl: int = 3600):
        """Cache correlation analysis results (1 hour TTL)."""
        key = f"user:{username}:correlations:{metrics_hash}"
        self.set(key, data, ttl)

    def get_forecast_cache(self, username: str, days: int) -> Optional[Dict]:
        """Get cached forecast results."""
        key = f"user:{username}:forecast:{days}"
        return self.get(key)

    def set_forecast_cache(self, username: str, days: int, data: Dict, ttl: int = 1800):
        """Cache forecast results (30 min TTL)."""
        key = f"user:{username}:forecast:{days}"
        self.set(key, data, ttl)

    def get_insights_cache(self, username: str) -> Optional[Dict]:
        """Get cached personalized insights."""
        key = f"user:{username}:insights"
        return self.get(key)

    def set_insights_cache(self, username: str, data: Dict, ttl: int = 900):
        """Cache personalized insights (15 min TTL)."""
        key = f"user:{username}:insights"
        self.set(key, data, ttl)


# Global cache instance
_cache_service = None

def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
