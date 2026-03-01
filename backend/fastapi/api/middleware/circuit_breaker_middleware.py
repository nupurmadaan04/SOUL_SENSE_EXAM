import time
import logging
import asyncio
from typing import Callable, Dict, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from ..services.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger(__name__)

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks the health and latency of heavy service endpoints (#1135).
    Automatically throttles requests if the underlying service (like NLP) is slow or failing.
    """
    def __init__(self, app, latency_threshold: float = 0.5):
        super().__init__(app)
        self.latency_threshold = latency_threshold
        # Mapping of path patterns to circuit breakers
        self.breakers: Dict[str, CircuitBreaker] = {}

    def _get_breaker(self, path: str) -> Optional[CircuitBreaker]:
        """Identifies if a path belongs to a 'heavy' service and returns its breaker."""
        # Define paths considered 'heavy' and prone to degradation
        HEAVY_PATHS = {
            "/api/v1/journal/create": "journal_nlp_service",
            "/api/v1/ml/inference": "ml_service",
            "/api/v1/assessment/score": "scoring_service"
        }
        
        for p, name in HEAVY_PATHS.items():
            if path.startswith(p):
                if name not in self.breakers:
                    self.breakers[name] = CircuitBreaker(name, latency_threshold=self.latency_threshold)
                return self.breakers[name]
        return None

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        breaker = self._get_breaker(path)
        
        if not breaker:
            return await call_next(request)

        # Check breaker state
        state = await breaker.get_state()
        if state == CircuitState.OPEN:
             logger.warning(f"Circuit Breaker [{breaker.service_name}] blocking request to {path}")
             raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Heavy service temporarily unavailable due to performance degradation (Circuit Breaker OPEN)."
             )

        start_time = time.time()
        try:
            response: Response = await call_next(request)
            
            # LATENCY TRACKING
            duration = time.time() - start_time
            if duration > self.latency_threshold:
                logger.warning(f"Heavy Request [{path}] exceeded latency threshold: {duration:.2f}s")
                await breaker.increment_failures()
            
            # Successful request in HALF_OPEN resets the breaker
            if state == CircuitState.HALF_OPEN:
                 await breaker.set_state(CircuitState.CLOSED)
                 
            return response

        except Exception as e:
            logger.error(f"Heavy Request [{path}] failed with error: {e}")
            await breaker.increment_failures()
            raise e
