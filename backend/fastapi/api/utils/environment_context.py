"""Environment context management for data hygiene and strict environment separation.

This module ensures that analytics data from different environments (development,
staging, production) is strictly separated to prevent data mixing issues.

Issue: #979 - Environment & Data Hygiene Issues
"""
import os
from contextvars import ContextVar
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    """Valid environment values."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# Context variable to store current environment in request context
_environment_context: ContextVar[Optional[str]] = ContextVar(
    "environment_context", default=None
)


class EnvironmentContext:
    """Context manager for environment isolation.
    
    Usage:
        with EnvironmentContext("staging"):
            # All analytics operations here will use staging environment
            analytics_service.log_event(...)
    """
    
    def __init__(self, environment: str):
        self.environment = self._validate_environment(environment)
        self.token = None
    
    def __enter__(self):
        self.token = _environment_context.set(self.environment)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            _environment_context.reset(self.token)
    
    @staticmethod
    def _validate_environment(env: str) -> str:
        """Validate and normalize environment string."""
        env = env.lower()
        valid_envs = {e.value for e in Environment}
        if env not in valid_envs:
            raise ValueError(f"Invalid environment: {env}. Must be one of: {valid_envs}")
        return env


def get_current_environment() -> str:
    """Get the current environment from context or environment variable.
    
    Priority:
        1. Context variable (set by middleware or context manager)
        2. APP_ENV environment variable
        3. SOULSENSE_ENV environment variable
        4. Default to 'development'
    
    Returns:
        Current environment string (development, staging, production, testing)
    """
    # Check context variable first (for request-scoped environment)
    ctx_env = _environment_context.get()
    if ctx_env:
        return ctx_env
    
    # Fall back to environment variables
    env = os.getenv("APP_ENV", "").lower()
    if env:
        return env
    
    env = os.getenv("SOULSENSE_ENV", "").lower()
    if env:
        return env
    
    return Environment.DEVELOPMENT.value


def set_environment_context(environment: str) -> None:
    """Set the environment context for the current scope.
    
    This is typically called by middleware at the start of each request.
    """
    valid_envs = {e.value for e in Environment}
    env = environment.lower()
    if env not in valid_envs:
        raise ValueError(f"Invalid environment: {env}. Must be one of: {valid_envs}")
    _environment_context.set(env)


def is_production() -> bool:
    """Check if current environment is production."""
    return get_current_environment() == Environment.PRODUCTION.value


def is_staging() -> bool:
    """Check if current environment is staging."""
    return get_current_environment() == Environment.STAGING.value


def is_development() -> bool:
    """Check if current environment is development."""
    return get_current_environment() == Environment.DEVELOPMENT.value


def validate_environment_strictness() -> dict:
    """Validate that environment separation is properly configured.
    
    Returns:
        Dictionary with validation results.
    """
    env = get_current_environment()
    
    results = {
        "environment": env,
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "separation_enabled": True
    }
    
    # Check for production database URL in non-production environments
    db_url = os.getenv("DATABASE_URL", "")
    if env != Environment.PRODUCTION.value:
        if "prod" in db_url.lower() or "production" in db_url.lower():
            results["errors"].append(
                f"CRITICAL: Non-production environment ({env}) using production database!"
            )
            results["is_valid"] = False
    
    # Check for analytics project separation
    analytics_project = os.getenv("ANALYTICS_PROJECT_ID", "")
    if analytics_project:
        env_prefix = env[:4].lower()  # First 4 chars of environment
        if env_prefix not in analytics_project.lower():
            results["warnings"].append(
                f"Analytics project '{analytics_project}' may not be environment-specific"
            )
    
    # Check Redis database separation
    redis_db = os.getenv("REDIS_DB", "0")
    if env == Environment.STAGING.value and redis_db == "0":
        results["warnings"].append(
            "Staging environment using default Redis DB (0). Consider using a separate DB."
        )
    
    return results


def get_environment_prefix() -> str:
    """Get a prefix for environment-specific resources.
    
    Returns:
        Environment prefix for resource naming (e.g., 'prod_', 'staging_', 'dev_')
    """
    env = get_current_environment()
    prefixes = {
        Environment.PRODUCTION.value: "prod",
        Environment.STAGING.value: "staging",
        Environment.DEVELOPMENT.value: "dev",
        Environment.TESTING.value: "test"
    }
    return prefixes.get(env, "dev")
