from pathlib import Path
import os
import sys
import secrets
from typing import Optional, Any

from dotenv import load_dotenv
from pydantic import Field, field_validator, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FASTAPI_DIR = BACKEND_DIR / "fastapi"
ENV_FILE = ROOT_DIR / ".env"

# Only add backend-specific paths to avoid module name conflicts with main app
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))


try:
    from core.validators import validate_environment_on_startup, log_environment_summary
except ImportError:
    # Fallback for different execution contexts
    try:
        from backend.core.validators import validate_environment_on_startup, log_environment_summary
    except ImportError:
        def validate_environment_on_startup(env: str = "development"):
            return {"validation_summary": {"valid": True, "errors": [], "warnings": []}, "validated_variables": {}}
        def log_environment_summary(vars, summary, env):
            pass

load_dotenv(ENV_FILE)


class BaseAppSettings(BaseSettings):
    """Base settings with common configuration."""

    # Application settings
    app_env: str = Field(default="development", description="Application environment")
    ENVIRONMENT: str = Field(default="development", description="Environment alias")
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=True, description="Debug mode")
    welcome_message: str = Field(default="Welcome to Soul Sense!", description="Welcome message")
    
    # Mock Authentication Mode (for testing/development)
    mock_auth_mode: bool = Field(default=False, description="Enable mock authentication for testing")

    # Database configuration
    database_type: str = Field(default="sqlite", description="Database type")
    database_url: str = Field(
        default=f"sqlite:///{ROOT_DIR}/data/soulsense.db",
        description="Database URL"
    )
    replica_database_url: Optional[str] = Field(
        default=None, 
        description="Read-replica database URL"
    )    # Connection pooling configuration
    use_pgbouncer: bool = Field(default=False, description="Use PgBouncer for connection pooling")
    pgbouncer_host: str = Field(default="localhost", description="PgBouncer host")
    pgbouncer_port: int = Field(default=6432, description="PgBouncer port")
    @property
    def async_database_url(self) -> str:
        """Construct asynchronous database URL."""
        url = self.database_url

        # Use PgBouncer for PostgreSQL in production
        if self.use_pgbouncer and url.startswith("postgresql://"):
            # Replace host and port with PgBouncer settings
            import re
            # Extract current host and port
            match = re.match(r'postgresql://([^:/@]+)(?::(\d+))?', url)
            if match:
                current_host = match.group(1)
                current_port = match.group(2) or "5432"
                # Replace with PgBouncer host and port
                url = url.replace(f"{current_host}:{current_port}", f"{self.pgbouncer_host}:{self.pgbouncer_port}")
                url = url.replace(f"{current_host}", f"{self.pgbouncer_host}:{self.pgbouncer_port}")

        # Convert to async driver
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url

    @property
    def async_replica_database_url(self) -> Optional[str]:
        """Construct asynchronous replica database URL."""
        url = self.replica_database_url
        if not url:
            return None
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url

    # Redis configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database index")
    redis_url: Optional[str] = Field(default=None, description="Redis URL (if set, overrides individual host/port)")
    redis_ttl_seconds: int = Field(default=60, description="Default lock TTL in seconds")

    # Deletion Grace Period
    deletion_grace_period_days: int = Field(default=30, ge=0, description="Grace period for account deletion in days")

    # JWT configuration
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, ge=1, description="JWT expiration hours")

    # GitHub Configuration
    github_token: Optional[str] = Field(default=None, description="GitHub Personal Access Token")
    github_repo_owner: str = Field(default="nupurmadaan04", description="GitHub Repository Owner")
    github_repo_name: str = Field(default="SOUL_SENSE_EXAM", description="GitHub Repository Name")

    # OAuth Configuration
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth Client ID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth Client Secret")
    github_client_id: Optional[str] = Field(default=None, description="GitHub OAuth Client ID")
    github_client_secret: Optional[str] = Field(default=None, description="GitHub OAuth Client Secret")

    # CORS Configuration
    # Cookie Security Settings
    cookie_secure: bool = Field(default=False, description="Use Secure flag for cookies (Requires HTTPS)")
    cookie_samesite: str = Field(default="lax", description="SameSite attribute for cookies (lax, strict, none)")
    cookie_domain: Optional[str] = Field(default=None, description="Domain attribute for cookies")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Any = Field(
        default=[
            "http://localhost:3000", 
            "http://localhost:3005", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3005",
            "tauri://localhost"
        ],
        description="Allowed origins for CORS"
    )

    # CORS Security Settings
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS requests")
    cors_max_age: int = Field(default=3600, description="Max age for preflight cache (seconds)")
    cors_expose_headers: list[str] = Field(
        default=["X-API-Version", "X-Request-ID", "X-Process-Time"],
        description="Headers to expose via CORS"
    )
    # Redis Configuration (for rate limiting and caching)
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # Storage Configuration (S3 / Blob) (#1125)
    storage_type: str = Field(default="s3", description="Cloud storage provider (s3, azure, local)")
    s3_bucket_name: str = Field(default="soulsense-archival", description="S3 bucket for cold storage")
    s3_region: str = Field(default="us-east-1", description="S3 bucket region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")
    archival_threshold_years: int = Field(default=2, description="Age threshold for archival in years")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from configuration."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            if isinstance(v, str):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    return [v]
            return v
        raise ValueError(v)

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def validate_cors_origins_security(cls, v: list[str], info) -> list[str]:
        """Validate CORS origins for security issues."""
        values = info.data

        # Validate origin formats
        for origin in v:
            if not origin:
                raise ValueError(
                    f"Invalid CORS origin format: {origin}. "
                    "Origins cannot be empty."
                )
            if not origin.startswith(("http://", "https://", "tauri://")) and origin != "*":
                raise ValueError(
                    f"Invalid CORS origin format: {origin}. "
                    "Origins must use http://, https://, or tauri:// protocols."
                )
            # Check for incomplete URLs (protocol only)
            if origin in ["http://", "https://", "tauri://"]:
                raise ValueError(
                    f"Invalid CORS origin format: {origin}. "
                    "Origins must include a valid host."
                )

        # Warn about localhost in production (but don't block)
        if values.get("app_env") == "production":
            localhost_origins = [o for o in v if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                import warnings
                warnings.warn(
                    f"Production environment contains localhost origins: {localhost_origins}. "
                    "Consider removing these for security."
                )

        return v

        # Validate origin formats
        for origin in v:
            if not origin.startswith(("http://", "https://", "tauri://")) and origin != "*":
                raise ValueError(
                    f"Invalid CORS origin format: {origin}. "
                    "Origins must use http://, https://, or tauri:// protocols."
                )

        # Warn about localhost in production (but don't block)
        if values.get("app_env") == "production":
            localhost_origins = [o for o in v if "localhost" in o or "127.0.0.1" in o]
            if localhost_origins:
                import warnings
                warnings.warn(
                    f"Production environment contains localhost origins: {localhost_origins}. "
                    "Consider removing these for security."
                )

        return v

    @model_validator(mode="after")
    def validate_cors_security(self) -> "BaseAppSettings":
        """Validate CORS security after all fields are set."""
        if self.cors_allow_credentials and "*" in self.BACKEND_CORS_ORIGINS:
            raise ValueError(
                "CORS security violation: Cannot use wildcard origin (*) when allow_credentials=True. "
                "This would allow any website to make authenticated requests to your API, "
                "potentially leading to CSRF attacks and token theft."
            )
        return self

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        """Alias for checking if environment is production."""
        return self.app_env == "production"

    @property
    def ENVIRONMENT(self) -> str:
        """Alias for app_env to match issue requirements."""
        return self.app_env

    @property
    def is_production(self) -> bool:
        """Check if the current environment is production."""
        return self.app_env == "production"

    @field_validator('app_env')
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed_envs = {'development', 'staging', 'production', 'testing'}
        if v.lower() not in allowed_envs:
            raise ValueError(f'app_env must be one of {allowed_envs}, got {v}')
        return v.lower()

    @field_validator('mock_auth_mode')
    @classmethod
    def validate_mock_auth_mode(cls, v: bool, info) -> bool:
        # Forcibly ignore mock auth in production
        if info.data.get('app_env') == 'production':
            return False
        return v

    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError('database_url cannot be empty')
        
        # Normalize to forward slashes for SQLite on Windows
        if v.startswith('sqlite:///'):
            v = v.replace('\\', '/')
            
        # Basic URL validation for database URLs
        if not (v.startswith('sqlite:///') or '://' in v):
            raise ValueError('database_url must be a valid database URL')
        return v

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key_entropy(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY is cryptographically weak. It must be at least 32 characters long.")
        return v


class DevelopmentSettings(BaseAppSettings):
    """Settings for development environment."""

    ENVIRONMENT: str = "development"
    debug: bool = True
    SECRET_KEY: str = Field(default="dev_jwt_secret_key_for_development_only_not_secure", description="Development JWT key")
    mock_auth_mode: bool = True
    jwt_secret_key: str = Field(default="dev_jwt_secret_key_for_development_only_not_secure", description="Development JWT key")


class StagingSettings(BaseAppSettings):
    """Settings for staging environment."""

    app_env: str = "staging"
    ENVIRONMENT: str = "staging"
    debug: bool = False

    # Required staging database settings
    database_host: str = Field(..., description="Database host")
    database_port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database_name: str = Field(..., description="Database name")
    database_user: str = Field(..., description="Database user")
    database_password: str = Field(..., description="Database password")

    # Redis staging settings
    redis_host: str = Field(..., description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: str = Field(..., description="Redis password")

    @field_validator('database_host')
    @classmethod
    def validate_database_host(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('database_host cannot be empty in staging')
        return v.strip()


class ProductionSettings(BaseAppSettings):
    """Settings for production environment."""

    app_env: str = "production"
    ENVIRONMENT: str = "production"
    debug: bool = False

    # Enforce secure cookies in production
    cookie_secure: bool = True
    cookie_samesite: str = "lax"  # Or 'strict' if API and FE are on same domain

    # Required production database settings
    database_host: str = Field(..., description="Database host")
    database_port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    database_name: str = Field(..., description="Database name")
    database_user: str = Field(..., description="Database user")
    database_password: str = Field(..., description="Database password")

    # Redis production settings
    redis_host: str = Field(..., description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: str = Field(..., description="Redis password")

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
            print(f"[ERROR] Environment validation failed for '{env}'!")
            log_environment_summary(validation_result['validated_variables'], summary, env)
            # Only exit in production/staging if there are errors
            if env in ['production', 'staging']:
                raise SystemExit(1)

        # Log validation summary
        log_environment_summary(validation_result['validated_variables'], summary, env)

    except Exception as e:
        if isinstance(e, SystemExit):
            raise e
        print(f"[ERROR] Environment validation error: {e}")
        # Don't crash in dev if validation itself fails
        if env in ['production', 'staging']:
            raise SystemExit(1)

    # Create appropriate settings class based on environment
    if env == "production":
        return ProductionSettings() # type: ignore
    elif env == "staging":
        return StagingSettings() # type: ignore
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
