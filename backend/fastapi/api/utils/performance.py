"""
Performance optimization utilities for the SoulSense API.
Includes caching, database query optimization, and response helpers.
"""

from functools import lru_cache
from typing import Optional, TypeVar, Callable, Any
import hashlib
import json
import logging
import time
from datetime import timedelta

logger = logging.getLogger("api.performance")

T = TypeVar('T')


class SimpleCache:
    """
    Simple in-memory cache for expensive operations.
    Implements TTL (Time To Live) cache eviction.
    """

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl: int = 300  # 5 minutes default TTL

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        import time

        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        import time

        cache_ttl = ttl if ttl is not None else self._ttl
        expiry = time.time() + cache_ttl
        self._cache[key] = (value, expiry)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def delete(self, key: str) -> bool:
        """Delete specific cache entry."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False


# Global cache instance
_cache = SimpleCache()


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results with TTL.
    Use for expensive database queries or external API calls.

    Args:
        ttl: Time to live in seconds (default: 300 = 5 minutes)
        key_prefix: Prefix for cache key to avoid collisions
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = _cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl=ttl)
            logger.debug(f"Cached result for {func.__name__}")

            return result

        return wrapper

    return decorator


def clear_cache(pattern: Optional[str] = None) -> None:
    """
    Clear cache entries optionally matching a pattern.

    Args:
        pattern: Optional pattern to match. If None, clears all cache.
    """
    if pattern is None:
        _cache.clear()
        logger.info("Cleared all cache")
    else:
        # Pattern-based clearing would require more complex implementation
        # For now, just clear all
        _cache.clear()
        logger.info(f"Cleared cache (pattern: {pattern})")


@lru_cache(maxsize=128)
def get_cached_question_categories(age: Optional[int] = None) -> list[dict]:
    """
    Get question categories with caching.
    Categories rarely change, so we cache them aggressively.

    Args:
        age: Optional age filter for age-appropriate questions

    Returns:
        List of question categories
    """
    from sqlalchemy import create_engine, text
    from .config import get_settings_instance

    settings = get_settings_instance()

    # This would normally query the database
    # For now, return a placeholder
    return [
        {"id": 1, "name": "Self-Awareness", "description": "Understanding emotions"},
        {"id": 2, "name": "Self-Management", "description": "Managing emotions"},
        {"id": 3, "name": "Social Awareness", "description": "Understanding others"},
        {"id": 4, "name": "Relationship Management", "description": "Managing relationships"},
    ]


class QueryOptimizer:
    """
    Database query optimization utilities.
    """

    @staticmethod
    def paginate(query, page: int = 1, page_size: int = 20):
        """
        Add pagination to a SQLAlchemy query.

        Args:
            query: SQLAlchemy query object
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (items, total_count, page_info)
        """
        # Get total count
        total_count = query.count()

        # Calculate offset
        offset = (page - 1) * page_size

        # Apply pagination
        items = query.offset(offset).limit(page_size).all()

        # Calculate page info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        page_info = {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        }

        return items, total_count, page_info

    @staticmethod
    def optimize_select_fields(query, model, fields: list[str]):
        """
        Optimize query to select only specific fields.

        Args:
            query: SQLAlchemy query object
            model: SQLAlchemy model
            fields: List of field names to select

        Returns:
            Optimized query
        """
        columns = [getattr(model, field) for field in fields if hasattr(model, field)]
        return query.with_entities(*columns)


def get_db_session_stats(db) -> dict:
    """
    Get database session performance statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with session stats
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    stats = {
        "query_count": 0,
        "total_time": 0.0,
        "slow_queries": [],
    }

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
        stats["query_count"] += 1

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, "_query_start_time"):
            total = time.time() - context._query_start_time
            stats["total_time"] += total

            # Track slow queries (> 100ms)
            if total > 0.1:
                stats["slow_queries"].append({
                    "statement": statement[:500],  # Truncate long queries
                    "time": total,
                })

    return stats


def log_query_performance(db, operation: str = "query") -> Callable[[], None]:
    """
    Enable query performance logging for a database session.

    Args:
        db: Database session
        operation: Operation name for logging
    """
    stats = get_db_session_stats(db)

    def log_stats():
        if stats["query_count"] > 0:
            avg_time = stats["total_time"] / stats["query_count"]
            logger.info(
                f"DB Operation '{operation}': "
                f"{stats['query_count']} queries, "
                f"avg {avg_time*1000:.2f}ms, "
                f"total {stats['total_time']*1000:.2f}ms"
            )

            if stats["slow_queries"]:
                logger.warning(
                    f"Found {len(stats['slow_queries'])} slow queries in '{operation}'"
                )
                for slow in stats["slow_queries"][:3]:  # Log first 3
                    logger.warning(f"  - {slow['time']*1000:.2f}ms: {slow['statement']}")

    return log_stats
