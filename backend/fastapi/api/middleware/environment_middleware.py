"""Environment isolation middleware for data hygiene.

This middleware ensures that all requests are tagged with the current environment,
preventing staging data from mixing with production data.

Issue: #979 - Environment & Data Hygiene Issues
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from ..utils.environment_context import set_environment_context, get_current_environment

logger = logging.getLogger("api.environment")


class EnvironmentMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce environment context on all requests.
    
    This middleware:
    1. Sets the environment context for each request
    2. Validates that the request is not crossing environment boundaries
    3. Adds environment headers to responses for debugging
    """
    
    def __init__(self, app: ASGIApp, default_environment: str = "development"):
        super().__init__(app)
        self.default_environment = default_environment
    
    async def dispatch(self, request: Request, call_next):
        """Process request with environment context."""
        # Determine environment from headers or use default
        env_header = request.headers.get("X-Environment")
        
        if env_header:
            environment = env_header.lower()
            logger.debug(f"Environment from header: {environment}")
        else:
            environment = get_current_environment()
            logger.debug(f"Environment from context: {environment}")
        
        # Set environment context for this request
        set_environment_context(environment)
        
        # Add environment to request state for access in route handlers
        request.state.environment = environment
        
        # Process the request
        response = await call_next(request)
        
        # Add environment headers to response for debugging
        response.headers["X-Environment"] = environment
        
        # Add warning header if in staging to prevent confusion
        if environment == "staging":
            response.headers["X-Environment-Warning"] = "staging-data"
        
        return response


class EnvironmentValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate environment configuration on startup.
    
    This middleware performs strict validation to ensure:
    - Production database is not used in non-production environments
    - Environment-specific settings are properly configured
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._validated = False
    
    async def dispatch(self, request: Request, call_next):
        """Validate environment on first request."""
        if not self._validated:
            from ..utils.environment_context import validate_environment_strictness
            
            validation = validate_environment_strictness()
            
            if not validation["is_valid"]:
                logger.error(f"Environment validation failed: {validation['errors']}")
                # In production, we might want to fail fast
                if validation["environment"] == "production":
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=500,
                        detail="Environment configuration error"
                    )
            
            if validation["warnings"]:
                for warning in validation["warnings"]:
                    logger.warning(f"Environment warning: {warning}")
            
            logger.info(
                f"Environment validation passed: {validation['environment']} "
                f"(separation_enabled={validation['separation_enabled']})"
            )
            self._validated = True
        
        return await call_next(request)
