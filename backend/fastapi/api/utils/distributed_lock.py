import time
import logging
import uuid
import threading
from typing import Optional, Any, List
import redis
from redlock import Redlock
from backend.fastapi.api.config import get_settings_instance

logger = logging.getLogger(__name__)

class DistributedLockError(Exception):
    """Base exception for distributed lock errors."""
    pass

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
