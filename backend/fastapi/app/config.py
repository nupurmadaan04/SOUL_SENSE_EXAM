from pathlib import Path
import os
import sys
import secrets
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FASTAPI_DIR = BACKEND_DIR / "fastapi"
ENV_FILE = ROOT_DIR / ".env"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))

from backend.core.validators import validate_environment_on_startup, log_environment_summary

load_dotenv(ENV_FILE)


class BaseAppSettings(BaseSettings):
    """Base settings with common configuration."""

    # Application settings
    app_env: str = Field(default="development", description="Application environment")
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=True, description="Debug mode")
    welcome_message: str = Field(default="Welcome to Soul Sense!", description="Welcome message")

    # Database configuration
    database_type: str = Field(default="sqlite", description="Database type")
    database_url: str = Field(default="sqlite:///../../data/soulsense.db", description="Database URL")

    # JWT configuration
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, ge=1, description="JWT expiration hours")

    # GitHub Configuration
    github_token: Optional[str] = Field(default=None, description="GitHub Personal Access Token")
    github_repo_owner: str = Field(default="nupurmadaan04", description="GitHub Repository Owner")
    github_repo_name: str = Field(default="SOUL_SENSE_EXAM", description="GitHub Repository Name")

    # CORS Configuration
    allowed_origins: str = Field(
        default='["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3005"]',
        description="Allowed origins for CORS"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse allowed_origins JSON string."""
        import json
        import logging
        
        logger = logging.getLogger("app.config")
        
        try:
            return json.loads(self.allowed_origins)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse allowed_origins JSON: '{self.allowed_origins}'. Error: {e}"
            )
            return []

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator('app_env')
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed_envs = {'development', 'staging', 'production'}
        if v.lower() not in allowed_envs:
            raise ValueError(f'app_env must be one of {allowed_envs}, got {v}')
        return v.lower()

    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError('database_url cannot be empty')
        # Basic URL validation for database URLs
        if not (v.startswith('sqlite:///') or '://' in v):
            raise ValueError('database_url must be a valid database URL')
        return v

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError('jwt_secret_key must be at least 32 characters long')
        return v


class DevelopmentSettings(BaseAppSettings):
    """Settings for development environment."""

    debug: bool = True
    jwt_secret_key: str = Field(default="dev_jwt_secret_key_for_development_only_not_secure", description="Development JWT key")


class StagingSettings(BaseAppSettings):
    """Settings for staging environment."""

    app_env: str = "staging"
    debug: bool = False

    # Required staging database settings
    database_host: str = Field(..., description="Database host")
    database_port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database_name: str = Field(..., description="Database name")
    database_user: str = Field(..., description="Database user")
    database_password: str = Field(..., description="Database password")

    @field_validator('database_host')
    @classmethod
    def validate_database_host(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('database_host cannot be empty in staging')
        return v.strip()


class ProductionSettings(BaseAppSettings):
    """Settings for production environment."""

    app_env: str = "production"
    debug: bool = False

    # Required production database settings
    database_host: str = Field(..., description="Database host")
    database_port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database_name: str = Field(..., description="Database name")
    database_user: str = Field(..., description="Database user")
    database_password: str = Field(..., description="Database password")

    @field_validator('database_host')
    @classmethod
    def validate_database_host(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('database_host cannot be empty in production')
        return v.strip()


def get_settings() -> BaseAppSettings:
    """Get settings based on environment."""
    # Validate environment on startup
    env = os.getenv('APP_ENV', 'development').lower()

    try:
        validation_result = validate_environment_on_startup(env)
        summary = validation_result['validation_summary']

        if not summary['valid']:
            print("[ERROR] Environment validation failed!")
            log_environment_summary(validation_result['validated_variables'], summary)
            raise SystemExit(1)

        # Log validation summary
        log_environment_summary(validation_result['validated_variables'], summary)

    except Exception as e:
        print(f"[ERROR] Environment validation error: {e}")
        raise SystemExit(1)

    # Create appropriate settings class based on environment
    if env == "production":
        return ProductionSettings()
    elif env == "staging":
        return StagingSettings()
    else:  # development
        return DevelopmentSettings()


# Global settings instance
_settings: Optional[BaseAppSettings] = None


def get_settings_instance() -> BaseAppSettings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings
