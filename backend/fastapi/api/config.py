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
<<<<<<< HEAD

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

=======
    db_request_timeout_seconds: int = Field(default=30, ge=5, le=300, description="Request-scoped DB timeout in seconds")
    thread_pool_max_workers: int = Field(default=64, ge=8, le=512, description="Default executor max workers for blocking fallbacks")
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
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

<<<<<<< HEAD
    @property
    def redis_url(self) -> str:
=======
    # Redis configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database index")
    redis_connection_url: Optional[str] = Field(default=None, description="Redis URL (if set, overrides individual host/port)")
    redis_ttl_seconds: int = Field(default=60, description="Default lock TTL in seconds")
    
    # Celery configuration
    celery_broker_url: Optional[str] = Field(default=None, description="Celery broker URL")
    celery_result_backend: Optional[str] = Field(default=None, description="Celery result backend")
    celery_worker_max_tasks_per_child: int = Field(default=100, ge=1, description="Restart worker children after serving 100 tasks to prevent memory leaks")

    # Database connection pool configuration
    database_pool_size: int = Field(default=20, ge=1, description="The number of connections to keep open inside the connection pool")
    database_max_overflow: int = Field(default=10, ge=0, description="The number of connections to allow in connection pool ‘overflow’")
    database_pool_timeout: int = Field(default=30, ge=0, description="The number of seconds to wait before giving up on getting a connection from the pool")
    database_pool_recycle: int = Field(default=1800, ge=-1, description="Number of seconds after which a connection is automatically recycled")
    database_pool_pre_ping: bool = Field(default=True, description="Enable pool pre-ping to handle DB node failures")
    database_statement_timeout: int = Field(default=30000, ge=0, description="Database statement timeout in milliseconds")

    # Database connection pool configuration
    database_pool_size: int = Field(default=20, ge=1, description="The number of connections to keep open inside the connection pool")
    database_max_overflow: int = Field(default=10, ge=0, description="The number of connections to allow in connection pool ‘overflow’")
    database_pool_timeout: int = Field(default=30, ge=0, description="The number of seconds to wait before giving up on getting a connection from the pool")
    database_pool_recycle: int = Field(default=1800, ge=-1, description="Number of seconds after which a connection is automatically recycled")
    database_pool_pre_ping: bool = Field(default=True, description="Enable pool pre-ping to handle DB node failures")
    database_statement_timeout: int = Field(default=30000, ge=0, description="Database statement timeout in milliseconds")

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
        if self.redis_connection_url:
            return self.redis_connection_url
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
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

<<<<<<< HEAD
=======
    @property
    def is_production(self) -> bool:
        """Alias for checking if environment is production."""
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


>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af
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
