import time
import logging
import uuid
import asyncio
from functools import wraps
from typing import Optional, Any, List, Callable
import redis.asyncio as redis

from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class DistributedLockError(Exception):
    """Base exception for distributed lock errors."""
    pass

class AsyncLock:
    """
    Async lock that ensures release in finally block, even during exceptions.
    Wraps asyncio.Lock with proper exception handling.
    """
    def __init__(self, lock: asyncio.Lock = None, timeout: float = None):
        self._lock = lock or asyncio.Lock()
        self._timeout = timeout
        self._acquired = False

    async def __aenter__(self):
        if self._timeout:
            try:
                await asyncio.wait_for(self._lock.acquire(), timeout=self._timeout)
            except asyncio.TimeoutError:
                raise RuntimeError(f"Lock acquisition timed out after {self._timeout}s")
        else:
            await self._lock.acquire()
        self._acquired = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            self._lock.release()
            self._acquired = False

# Lua script to safely release a lock
RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

class DistributedLock:
    """
    Context manager for a distributed lock using Redis SET NX PX.
    """
    def __init__(self, name: str, timeout: int = 60):
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.lock_value = str(uuid.uuid4())
        self.settings = get_settings_instance()
        self.redis = None
        self._acquired = False

    async def __aenter__(self):
        if self.redis is None:
            self.redis = redis.from_url(self.settings.redis_url, decode_responses=True)
            
        acquired = await self.redis.set(
            self.name,
            self.lock_value,
            nx=True,
            px=self.timeout * 1000
        )
        
        if not acquired:
            raise RuntimeError(f"Could not acquire lock for {self.name}")
            
        self._acquired = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._acquired and self.redis:
            try:
                await self.redis.eval(RELEASE_LOCK_SCRIPT, 1, self.name, self.lock_value)
            except Exception as e:
                logger.error(f"Failed to release lock {self.name}: {e}")
            finally:
                self._acquired = False

def require_lock(name: str, timeout: int = 60):
    """
    Decorator to prevent concurrent execution of the same job across worker nodes.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            lock_name = name
            try:
                async with DistributedLock(name=lock_name, timeout=timeout):
                    return await func(*args, **kwargs)
            except RuntimeError as e:
                logger.warning(f"Task skipped due to active lock: {e}")
                raise
        return wrapper
    return decorator
