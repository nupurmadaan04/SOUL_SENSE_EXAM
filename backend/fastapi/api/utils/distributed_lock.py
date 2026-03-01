import time
import logging
import uuid
import threading
import asyncio
from typing import Optional, Any, List
import redis
from redlock import Redlock
from backend.fastapi.api.config import get_settings_instance

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

class DistributedLock:
    """
    Distributed lock implementation using Redlock algorithm with fencing tokens.
    Handles automatic lock renewal and connection failures.
    """
    
    def __init__(self, resource: str):
        self.resource = f"lock:{resource}"
        self.settings = get_settings_instance()
        self.client = self._get_redis_client()
        # Redlock needs a list of redis clients/connection strings
        self.redlock_manager = Redlock([self.client])
        self._lock: Optional[Any] = None
        self._fencing_token: Optional[int] = None
        self._stop_renewal = threading.Event()
        self._renewal_thread: Optional[threading.Thread] = None

    def _get_redis_client(self):
        """Get or create connection to Redis."""
        try:
            if self.settings.redis_url:
                return redis.from_url(self.settings.redis_url)
            
            return redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                password=self.settings.redis_password,
                db=self.settings.redis_db,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True # Important for getting tokens as integers/strings
            )
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failure for distributed lock: {e}")
            raise DistributedLockError(f"Cannot connect to Redis: {e}")

    def acquire(self, ttl_ms: int = 30000, retry_count: int = 3, retry_delay_ms: int = 200) -> bool:
        """
        Acquire the distributed lock.
        
        Args:
            ttl_ms: Time-to-live in milliseconds. Default 30s.
            retry_count: Number of times to retry acquisition.
            retry_delay_ms: Time between retries in milliseconds.
            
        Returns:
            bool: True if lock acquired, False otherwise.
        """
        try:
            # Try to acquire lock using Redlock algorithm
            self._lock = self.redlock_manager.lock(
                self.resource, 
                ttl_ms
            )
            
            if self._lock:
                # Generate fencing token (monotonically increasing value)
                self._fencing_token = self._generate_fencing_token()
                logger.info(f"Successfully acquired lock on {self.resource} with fencing token {self._fencing_token}")
                
                # Start renewal thread if operation is expected to be long
                self._start_renewal_thread(ttl_ms)
                return True
            
            logger.warning(f"Failed to acquire lock on {self.resource} after retries.")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during lock acquisition for {self.resource}: {e}")
            return False

    def release(self) -> bool:
        """
        Release the lock and stop renewal.
        """
        # Stop renewal first
        self._stop_renewal.set()
        if self._renewal_thread and self._renewal_thread.is_alive():
            self._renewal_thread.join(timeout=1.0)
            
        if not self._lock:
            return True
            
        try:
            self.redlock_manager.unlock(self._lock)
            logger.info(f"Successfully released lock on {self.resource}")
            self._lock = None
            self._fencing_token = None
            return True
        except Exception as e:
            logger.error(f"Error while releasing lock on {self.resource}: {e}")
            return False

    def _generate_fencing_token(self) -> int:
        """
        Generates a fencing token using INCR on a specific key in Redis.
        Ensures atomicity and monotonicity.
        """
        fencing_key = f"fencing:{self.resource}"
        try:
            # We use the raw client to ensure we get an incrementing number
            return self.client.incr(fencing_key)
        except redis.RedisError as e:
            logger.error(f"Failed to generate fencing token for {self.resource}: {e}")
            # If Redis fails, we can't safely provide a fencing token.
            # Depending on policy, we might still proceed or fail the whole operation.
            # Here we raise to ensure atomicity.
            raise DistributedLockError(f"Fencing token generation failed: {e}")

    def get_fencing_token(self) -> Optional[int]:
        """Returns the current fencing token if the lock is held."""
        return self._fencing_token

    def _start_renewal_thread(self, ttl_ms: int):
        """
        Starts a background thread to renew the lock before it expires.
        This provides a basic heartbeat mechanism.
        """
        self._stop_renewal.clear()
        
        # Renew at 1/3 of TTL to be safe
        renewal_interval_sec = (ttl_ms / 3) / 1000.0
        
        def renew_loop():
            while not self._stop_renewal.is_set():
                time.sleep(renewal_interval_sec)
                if self._stop_renewal.is_set():
                    break
                
                if self._lock:
                    try:
                        # Re-acquiring with same value and resource acts as extension in Redlock
                        # actually it sets a new lock. A better extension would use a Lua script.
                        # redlock-py's extension support is limited, so we attempt to re-lock
                        # if we still own it.
                        self._extend_lock(ttl_ms)
                    except Exception as e:
                        logger.warning(f"Failed to renew lock on {self.resource}: {e}")
        
        self._renewal_thread = threading.Thread(target=renew_loop, daemon=True)
        self._renewal_thread.start()

    def _extend_lock(self, ttl_ms: int):
        """
        Extends the lock TTL if possible. 
        Note: Redlock-py doesn't have an 'extend', so we use a custom Lua script
        to ensure atomicity (only extend if the value matches).
        """
        extension_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("pexpire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        try:
            # self._lock is a dict containing 'resource' and 'key' (the random value) in redlock-py
            success = self.client.eval(extension_script, 1, self.resource, self._lock['key'], ttl_ms)
            if success:
                logger.debug(f"Extended lock on {self.resource} for {ttl_ms}ms")
            else:
                logger.warning(f"Lock on {self.resource} could not be extended (already expired or lost)")
                self._stop_renewal.set() # Stop trying if we lost it
        except Exception as e:
             logger.error(f"Error during lock extension: {e}")

    def __enter__(self):
        """Context manager support."""
        if self.acquire():
            return self
        raise DistributedLockError(f"Could not acquire lock on {self.resource}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.release()
import uuid
import logging
from functools import wraps
from typing import Optional, Callable, Any

import redis.asyncio as redis
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

# Lua script to safely release a lock
RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

_redis_pool = None

async def get_redis():
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings_instance()
        _redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool

class DistributedLock:
    """
    Context manager for a distributed lock using Redis SET NX PX.
    Implements a variation of the Redlock algorithm for single-node Redis.
    """
    def __init__(self, name: str, timeout: int = 60, redis_client: Optional[redis.Redis] = None):
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.lock_value = str(uuid.uuid4())
        self.redis = redis_client
        self._acquired = False

    async def __aenter__(self):
        if self.redis is None:
            self.redis = await get_redis()
            
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
    `name` can be a format string using kwargs from the decorated function.
    """
    import inspect
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Attempt to interpolate the name with kwargs
            try:
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                lock_name = name.format(**bound_args.arguments)
            except (KeyError, IndexError, AttributeError):
                lock_name = name
                
            try:
                async with DistributedLock(name=lock_name, timeout=timeout):
                    return await func(*args, **kwargs)
            except RuntimeError as e:
                logger.warning(f"Task skipped due to active lock: {e}")
                raise
        return wrapper
    return decorator
