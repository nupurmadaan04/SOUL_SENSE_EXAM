"""
Race Condition Mitigation - Issue #1067

Implements comprehensive protection against race conditions in critical endpoints:
- Idempotency keys for duplicate request prevention
- Row-level locking for atomic operations
- Enhanced transaction handling
- Concurrent request protection
"""

import hashlib
import logging
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, text
from sqlalchemy.exc import IntegrityError
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class IdempotencyService:
    """
    Service for managing idempotency keys to prevent duplicate operations.

    Stores idempotency keys in Redis with TTL to prevent replay attacks
    and ensure operations are only executed once.
    """

    def __init__(self):
        self.settings = get_settings_instance()
        self.redis = None

    async def _get_redis(self):
        if self.redis is None:
            try:
                from ..main import app
                self.redis = getattr(app.state, 'redis_client', None)
            except:
                pass
        return self.redis

    async def check_and_set_idempotency(
        self,
        key: str,
        operation: str,
        ttl_seconds: int = 300
    ) -> tuple[bool, Optional[str]]:
        """
        Check if operation with idempotency key was already performed.

        Returns:
            (is_duplicate, response_data)
            - is_duplicate: True if operation already performed
            - response_data: Cached response if duplicate, None otherwise
        """
        redis = await self._get_redis()
        if not redis:
            # Fallback: allow operation if Redis unavailable
            logger.warning("Redis unavailable for idempotency check")
            return False, None

        cache_key = f"idempotency:{operation}:{key}"

        # Check if operation already completed
        cached_result = await redis.get(cache_key)
        if cached_result:
            logger.info(f"Duplicate {operation} request detected: {key}")
            return True, cached_result.decode('utf-8')

        # Mark operation as in-progress
        await redis.setex(f"in_progress:{cache_key}", 30, "1")  # 30s timeout

        return False, None

    async def complete_idempotency(
        self,
        key: str,
        operation: str,
        response_data: str,
        ttl_seconds: int = 300
    ):
        """Mark idempotency operation as completed with response data."""
        redis = await self._get_redis()
        if not redis:
            return

        cache_key = f"idempotency:{operation}:{key}"
        in_progress_key = f"in_progress:{cache_key}"

        # Store result and remove in-progress flag
        await redis.setex(cache_key, ttl_seconds, response_data)
        await redis.delete(in_progress_key)

        logger.debug(f"Idempotency operation completed: {operation}:{key}")

    async def cleanup_expired_operations(self):
        """Clean up expired in-progress operations (should be called periodically)."""
        redis = await self._get_redis()
        if not redis:
            return

        # This would need a more sophisticated cleanup mechanism
        # For now, rely on Redis TTL
        pass

# Global idempotency service instance
idempotency_service = IdempotencyService()

async def check_idempotency(
    request: Request,
    operation: str,
    ttl_seconds: int = 300
) -> Optional[str]:
    """
    Middleware function to check idempotency for critical operations.

    Args:
        request: FastAPI request object
        operation: Operation type (e.g., 'exam_submit', 'token_refresh')
        ttl_seconds: How long to cache the result

    Returns:
        Cached response data if duplicate, None if new operation

    Raises:
        HTTPException: If operation is currently in progress
    """
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        # Allow operation without idempotency key (not enforced)
        return None

    # Create compound key with user context if available
    user_id = getattr(request.state, 'user_id', None)
    compound_key = f"{user_id or 'anon'}:{idempotency_key}"

    is_duplicate, cached_response = await idempotency_service.check_and_set_idempotency(
        compound_key, operation, ttl_seconds
    )

    if is_duplicate:
        return cached_response

    # Check if operation is currently in progress
    redis = await idempotency_service._get_redis()
    if redis:
        in_progress_key = f"in_progress:idempotency:{operation}:{compound_key}"
        if await redis.exists(in_progress_key):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operation already in progress. Please wait and try again."
            )

    # Store the idempotency key in request state for later completion
    request.state.idempotency_key = compound_key
    request.state.idempotency_operation = operation
    request.state.idempotency_ttl = ttl_seconds

    return None

async def complete_idempotency(request: Request, response_data: str):
    """Complete an idempotency operation with response data."""
    if hasattr(request.state, 'idempotency_key'):
        await idempotency_service.complete_idempotency(
            request.state.idempotency_key,
            request.state.idempotency_operation,
            response_data,
            getattr(request.state, 'idempotency_ttl', 300)
        )

# Database locking utilities
async def with_row_lock(db: AsyncSession, table_name: str, condition: str, condition_params: Dict[str, Any]):
    """
    Execute a query with row-level locking to prevent concurrent modifications.

    Args:
        db: Database session
        table_name: Table to lock
        condition: WHERE clause condition
        condition_params: Parameters for the condition

    Example:
        await with_row_lock(db, "users", "id = :user_id", {"user_id": 123})
    """
    lock_query = f"SELECT 1 FROM {table_name} WHERE {condition} FOR UPDATE"
    await db.execute(text(lock_query), condition_params)

def generate_idempotency_key(request: Request, operation: str) -> str:
    """
    Generate a deterministic idempotency key from request characteristics.

    This is useful when clients don't provide explicit idempotency keys.
    """
    # Use combination of user ID, operation, and request timestamp
    user_id = getattr(request.state, 'user_id', 'anon')
    timestamp = str(int(time.time()))

    # Create hash of request characteristics
    key_components = f"{user_id}:{operation}:{timestamp}"
    return hashlib.sha256(key_components.encode()).hexdigest()[:16]