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

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))

try:
    from core.validators import validate_environment_on_startup, log_environment_summary
except ImportError:
    try:
        from backend.core.validators import validate_environment_on_startup, log_environment_summary
    except ImportError:
        def validate_environment_on_startup(env: str = "development"):
            return {"validation_summary": {"valid": True, "errors": [], "warnings": []}, "validated_variables": {}}
        def log_environment_summary(vars, summary, env):
            pass

load_dotenv(ENV_FILE)

class BaseAppSettings(BaseSettings):
    app_env: str = Field(default="development", description="Application environment")
    ENVIRONMENT: str = Field(default="development", description="Environment alias")
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=True, description="Debug mode")
    welcome_message: str = Field(default="Welcome to Soul Sense!", description="Welcome message")
    mock_auth_mode: bool = Field(default=False, description="Enable mock authentication for testing")

    database_type: str = Field(default="sqlite", description="Database type")
    database_url: str = Field(default=f"sqlite:///{ROOT_DIR}/data/soulsense.db", description="Database URL")
    replica_database_url: Optional[str] = Field(default=None, description="Read-replica database URL")
    use_pgbouncer: bool = Field(default=False, description="Use PgBouncer for connection pooling")
    pgbouncer_host: str = Field(default="localhost", description="PgBouncer host")
    pgbouncer_port: int = Field(default=6432, description="PgBouncer port")

    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database index")
    redis_ttl_seconds: int = Field(default=60, description="Default lock TTL in seconds")

    deletion_grace_period_days: int = Field(default=30, ge=0, description="Grace period for account deletion in days")

    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, ge=1, description="JWT expiration hours")

    github_token: Optional[str] = Field(default=None, description="GitHub Personal Access Token")
    github_repo_owner: str = Field(default="nupurmadaan04", description="GitHub Repository Owner")
    github_repo_name: str = Field(default="SOUL_SENSE_EXAM", description="GitHub Repository Name")

    google_client_id: Optional[str] = Field(default=None, description="Google OAuth Client ID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth Client Secret")
    github_client_id: Optional[str] = Field(default=None, description="GitHub OAuth Client ID")
    github_client_secret: Optional[str] = Field(default=None, description="GitHub OAuth Client Secret")

    cookie_secure: bool = Field(default=False, description="Use Secure flag for cookies")
    cookie_samesite: str = Field(default="lax", description="SameSite attribute for cookies")
    cookie_domain: Optional[str] = Field(default=None, description="Domain attribute for cookies")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")

    BACKEND_CORS_ORIGINS: Any = Field(default=["http://localhost:3000", "http://localhost:3005", "tauri://localhost"], description="Allowed origins for CORS")
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS requests")
    cors_max_age: int = Field(default=3600, description="Max age for preflight cache")
    cors_expose_headers: list[str] = Field(default=["X-API-Version", "X-Request-ID", "X-Process-Time"], description="Headers to expose via CORS")

    storage_type: str = Field(default="s3", description="Cloud storage provider")
    s3_bucket_name: str = Field(default="soulsense-archival", description="S3 bucket")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")
    archival_threshold_years: int = Field(default=2, description="Age threshold for archival")

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url

    @property
    def async_replica_database_url(self) -> Optional[str]:
        url = self.replica_database_url
        if not url:
            return None
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return url

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class DevelopmentSettings(BaseAppSettings):
    ENVIRONMENT: str = "development"
    debug: bool = True
    SECRET_KEY: str = "dev_jwt_secret_key_for_development_only_not_secure"
    mock_auth_mode: bool = True

class StagingSettings(BaseAppSettings):
    app_env: str = "staging"
    ENVIRONMENT: str = "staging"
    debug: bool = False
    database_host: str = Field(default="localhost")
    database_name: str = Field(default="soulsense_staging")
    database_user: str = Field(default="postgres")
    database_password: str = Field(default="password")
    redis_host: str = Field(default="localhost")
    redis_password: str = Field(default="password")

class ProductionSettings(BaseAppSettings):
    app_env: str = "production"
    ENVIRONMENT: str = "production"
    debug: bool = False
    cookie_secure: bool = True
    database_host: str = Field(...)
    database_name: str = Field(...)
    database_user: str = Field(...)
    database_password: str = Field(...)
    redis_host: str = Field(...)
    redis_password: str = Field(...)

def get_settings() -> BaseAppSettings:
    env = os.getenv('APP_ENV', 'development').lower()
    if env == "production":
        return ProductionSettings()
    elif env == "staging":
        return StagingSettings()
    else:
        return DevelopmentSettings()

_settings: Optional[BaseAppSettings] = None

def get_settings_instance() -> BaseAppSettings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings
