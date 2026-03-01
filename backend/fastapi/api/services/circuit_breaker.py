import asyncio
import time
import logging
import functools
from enum import Enum
from typing import Callable, Any, Optional, Type
from fastapi import HTTPException, status
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, blocking calls
    HALF_OPEN = "HALF_OPEN" # Testing for recovery

class CircuitBreaker:
    def __init__(
        self, 
        service_name: str, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 30,
        latency_threshold: float = 0.2, # trips if > 200ms consistently
        expected_exception: Type[Exception] = Exception
    ):
        self.service_name = f"circuit_breaker:{service_name}"
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.latency_threshold = latency_threshold
        self.expected_exception = expected_exception
        self.settings = get_settings_instance()
        
        # We'll use the app's global redis client if available, else local mock
        self.redis = None 

    def _get_redis(self):
        """Lazy access to redis client."""
        if self.redis:
             return self.redis
        
        try:
            from ..main import app
            self.redis = getattr(app.state, 'redis_client', None)
        except ImportError:
            pass
        return self.redis

    async def get_state(self) -> CircuitState:
        redis = self._get_redis()
        if not redis:
            return CircuitState.CLOSED # Default to safe if Redis is down

        state = await redis.get(f"{self.service_name}:state")
        if not state:
            return CircuitState.CLOSED
        
        state = CircuitState(state)
        
        if state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            opened_at = float(await redis.get(f"{self.service_name}:opened_at") or 0)
            if time.time() - opened_at >= self.recovery_timeout:
                await self.set_state(CircuitState.HALF_OPEN)
                return CircuitState.HALF_OPEN
        
        return state

    async def set_state(self, state: CircuitState):
        redis = self._get_redis()
        if not redis: return
        
        await redis.set(f"{self.service_name}:state", state.value)
        if state == CircuitState.OPEN:
            await redis.set(f"{self.service_name}:opened_at", str(time.time()))
        elif state == CircuitState.CLOSED:
            await redis.delete(f"{self.service_name}:failures")
        
        logger.warning(f"Circuit Breaker [{self.service_name}] transitioned to {state.value}")

    async def increment_failures(self):
        redis = self._get_redis()
        if not redis: return
        
        failures = await redis.incr(f"{self.service_name}:failures")
        if failures >= self.failure_threshold:
            await self.set_state(CircuitState.OPEN)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        state = await self.get_state()
        
        if state == CircuitState.OPEN:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE__UNAVAILABLE,
                detail=f"Circuit Breaker for {self.service_name} is OPEN. Service temporarily unavailable."
            )

        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # LATENCY CHECK (#1135)
            duration = time.time() - start_time
            if duration > self.latency_threshold:
                logger.warning(f"Circuit Breaker [{self.service_name}] slow response: {duration:.2f}s > {self.latency_threshold}s")
                await self.increment_failures() # High latency counts as a failure
            
            # If successful and was HALF_OPEN, close the circuit
            if state == CircuitState.HALF_OPEN:
                await self.set_state(CircuitState.CLOSED)
            
            return result
        
        except self.expected_exception as e:
            logger.error(f"Circuit Breaker [{self.service_name}] caught failure: {e}")
            await self.increment_failures()
            raise e

def circuit_breaker(
    service_name: str, 
    failure_threshold: int = 5, 
    recovery_timeout: int = 30
):
    """Decorator to protect external calls."""
    breaker = CircuitBreaker(service_name, failure_threshold, recovery_timeout)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
