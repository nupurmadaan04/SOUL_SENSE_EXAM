"""
Query optimization middleware for FastAPI.

Implements:
- Query result caching with Redis
- N+1 query prevention
- Eager loading hints
- Query result pagination
"""

from functools import wraps
from typing import Optional, Callable, Any
import hashlib
import json
import logging
from fastapi import Request
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)


def cache_query(ttl: int = 300, key_prefix: str = "query"):
    """
    Cache query results in Redis.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Cache key prefix
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            key_parts = [key_prefix, func.__name__]
            
            # Add hashable args to key
            for arg in args:
                if hasattr(arg, 'id'):
                    key_parts.append(str(arg.id))
            
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, bool)):
                    key_parts.append(f"{k}:{v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            try:
                from backend.fastapi.api.services.cache_service import cache_service
                cached = await cache_service.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")
            
            # Execute query
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                from backend.fastapi.api.services.cache_service import cache_service
                await cache_service.set(cache_key, json.dumps(result), ttl)
                logger.debug(f"Cached result: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")
            
            return result
        
        return wrapper
    return decorator


def eager_load(*relationships):
    """
    Decorator to add eager loading to queries.
    
    Usage:
        @eager_load('user', 'comments')
        async def get_posts(db):
            return db.query(Post).all()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Add eager loading options if result is a query
            if hasattr(result, 'options'):
                for rel in relationships:
                    result = result.options(selectinload(rel))
            
            return result
        
        return wrapper
    return decorator


class QueryOptimizer:
    """Utility class for query optimization."""
    
    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 50):
        """
        Paginate query results.
        
        Args:
            query: SQLAlchemy query
            page: Page number (1-indexed)
            per_page: Items per page
        
        Returns:
            Paginated results with metadata
        """
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @staticmethod
    def add_eager_loading(query, *relationships):
        """Add eager loading to prevent N+1 queries."""
        for rel in relationships:
            query = query.options(selectinload(rel))
        return query
    
    @staticmethod
    def add_joined_loading(query, *relationships):
        """Add joined loading for one-to-one relationships."""
        for rel in relationships:
            query = query.options(joinedload(rel))
        return query
