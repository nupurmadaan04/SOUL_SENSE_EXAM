import os
import json
import logging
import copy
from typing import Dict, Any, Union, Optional, TypeVar, Type, cast, overload
from dotenv import load_dotenv

from app.exceptions import ConfigurationError

# Load environment variables from .env file
load_dotenv()

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH: str = os.path.join(BASE_DIR, "config.json")

T = TypeVar("T")

@overload
def get_env_var(name: str, default: str, var_type: Type[str] = str) -> str: ...

@overload
def get_env_var(name: str, default: bool, var_type: Type[bool]) -> bool: ...

@overload
def get_env_var(name: str, default: int, var_type: Type[int]) -> int: ...

@overload
def get_env_var(name: str, default: float, var_type: Type[float]) -> float: ...

@overload
def get_env_var(name: str, default: None = None, var_type: Type[str] = str) -> Optional[str]: ...

def get_env_var(name: str, default: Any = None, 
                var_type: Type[Any] = str) -> Any:
    """
    Get an environment variable with SOULSENSE_ prefix.
    
    Args:
        name: Variable name without prefix (e.g., 'DEBUG' for SOULSENSE_DEBUG)
        default: Default value if not set
        var_type: Type to convert to (str, bool, int, float)
    
    Returns:
        The environment variable value converted to the specified type
    """
    full_name = f"SOULSENSE_{name}"
    value = os.environ.get(full_name)
    
    if value is None:
        return default
    
    # Type conversion
    if var_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    elif var_type == int:
        try:
            return int(value)
        except ValueError:
            return default
    elif var_type == float:
        try:
            return float(value)
        except ValueError:
            return default
    
    return value


# Environment settings
ENV: str = get_env_var("ENV", "development")
DEBUG: bool = get_env_var("DEBUG", False, bool)
LOG_LEVEL: str = get_env_var("LOG_LEVEL", "INFO")

# Default Configuration
DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "database": {
        "filename": "soulsense.db",
        "path": "db"
    },
    "ui": {
        "theme": "light",
        "window_size": "800x600"
    },
    "features": {
        "enable_journal": True,
        "enable_analytics": True
    },
    "capacity_monitoring": {
        "enabled": False,
        "collection_interval_seconds": 300,
        "retention_days": 30,
        "forecast_window_hours": 24,
        "min_historical_points": 10,
        "critical_threshold_pct": 90.0,
        "warning_threshold_pct": 75.0,
        "safety_margin_pct": 20.0
    }
}

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json or return defaults."""
    if not os.path.exists(CONFIG_PATH):
        logging.warning(f"Config file not found at {CONFIG_PATH}. Using defaults.")
        return copy.deepcopy(DEFAULT_CONFIG)
    
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            # Use deepcopy to avoid mutating the global DEFAULT_CONFIG
            merged = copy.deepcopy(DEFAULT_CONFIG)
            for section in ["database", "ui", "features", "capacity_monitoring"]:
                if section in config:
                    merged[section].update(config[section])
            return merged
    except json.JSONDecodeError as e:
        # Critical: File exists but is corrupt
        raise ConfigurationError(f"Configuration file is corrupt: {e}", original_exception=e)
    except Exception as e:
        raise ConfigurationError(f"Failed to load config file: {e}", original_exception=e)

def save_config(new_config: Dict[str, Any]) -> bool:
    """Save configuration to config.json."""
    from app.utils.atomic import atomic_write
    try:
        with atomic_write(CONFIG_PATH, "w") as f:
            json.dump(new_config, f, indent=4)
        logging.info("Configuration saved successfully.")
        return True
    except Exception as e:
        logging.error(f"Failed to save config: {e}")
        # Raising error here allows caller to show UI error if needed
        raise ConfigurationError(f"Failed to save configuration: {e}", original_exception=e)

# Load Config on Import
_config: Dict[str, Any] = load_config()

# Expose Settings
# Expose Settings
DB_DIR_NAME: str = _config["database"]["path"]
DB_FILENAME: str = _config["database"]["filename"]

# Directory Definitions
DATA_DIR: str = os.path.join(BASE_DIR, "data")
LOG_DIR: str = os.path.join(BASE_DIR, "logs")
MODELS_DIR: str = os.path.join(BASE_DIR, "models")

# Ensure directories exist
for directory in [DATA_DIR, LOG_DIR, MODELS_DIR]:
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError:
            pass

# Calculated Paths
# Environment variable takes precedence, then config.json, then defaults
_env_db_path = get_env_var("DB_PATH")

if _env_db_path:
    # Environment variable override - can be absolute or relative to BASE_DIR
    if os.path.isabs(_env_db_path):
        DB_PATH: str = _env_db_path
    else:
        DB_PATH = os.path.join(BASE_DIR, _env_db_path)
elif DB_DIR_NAME == "db":
    # Default: put it in DATA_DIR
    DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)
else:
    # Custom path relative to BASE_DIR if specified in config.json
    DB_PATH = os.path.join(BASE_DIR, DB_DIR_NAME, DB_FILENAME)

# Database Configuration
# FORCE UNIFICATION: Prioritize DATABASE_URL from environment (shared with backend)
DATABASE_URL: str = os.getenv("DATABASE_URL") or get_env_var("DATABASE_URL")

if not DATABASE_URL:
    # Try to import from backend config if available
    try:
        import sys
        # Ensure project root is in path for imports
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        
        # Check if backend directory exists before trying to import
        if os.path.exists(os.path.join(BASE_DIR, "backend")):
            from backend.fastapi.api.config import get_settings_instance
            settings = get_settings_instance()
            DATABASE_URL = settings.database_url
            DB_POOL_SIZE = settings.database_pool_size
            DB_MAX_OVERFLOW = settings.database_max_overflow
            DB_POOL_TIMEOUT = settings.database_pool_timeout
            DB_POOL_RECYCLE = settings.database_pool_recycle
            DB_POOL_PRE_PING = settings.database_pool_pre_ping
            DB_STATEMENT_TIMEOUT = settings.database_statement_timeout
            logging.info(f"Using database settings from backend config (URL: {DATABASE_URL})")
    except (ImportError, Exception) as e:
        logging.debug(f"Could not import backend config: {e}")

# Default values if not set by backend
if 'DB_POOL_SIZE' not in locals():
    DB_POOL_SIZE = get_env_var("DB_POOL_SIZE", 20, int)
    DB_MAX_OVERFLOW = get_env_var("DB_MAX_OVERFLOW", 10, int)
    DB_POOL_TIMEOUT = get_env_var("DB_POOL_TIMEOUT", 30, int)
    DB_POOL_RECYCLE = get_env_var("DB_POOL_RECYCLE", 1800, int)
    DB_POOL_PRE_PING = get_env_var("DB_POOL_PRE_PING", True, bool)
    DB_STATEMENT_TIMEOUT = get_env_var("DB_STATEMENT_TIMEOUT", 30000, int)

if not DATABASE_URL:
    # Fallback to legacy local configuration if shared sources unavailable
    DATABASE_TYPE: str = get_env_var("DATABASE_TYPE", "sqlite")
    if DATABASE_TYPE == "postgresql":
        DB_HOST: str = get_env_var("DB_HOST", "localhost")
        DB_PORT: int = get_env_var("DB_PORT", 5432, int)
        DB_NAME: str = get_env_var("DB_NAME", "soulsense")
        DB_USER: str = get_env_var("DB_USER", "postgres")
        DB_PASSWORD: str = get_env_var("DB_PASSWORD", "password")
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure we handle SQLite directory creation if applicable
if DATABASE_URL.startswith("sqlite:///"):
    # Extract path, handling relative paths (sqlite:///./data/...)
    sqlite_path = DATABASE_URL.replace("sqlite:///", "")
    # Remove leading dots/slashes for path normalization if needed
    if sqlite_path.startswith("./"):
        sqlite_path = os.path.join(BASE_DIR, sqlite_path[2:])
    elif not os.path.isabs(sqlite_path):
        sqlite_path = os.path.join(BASE_DIR, sqlite_path)
    
    db_dir = os.path.dirname(sqlite_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir)
        except OSError:
            pass

# UI Settings
THEME: str = _config["ui"]["theme"]

# Feature Toggles (env vars take precedence over config file)
_cfg_journal = _config["features"]["enable_journal"]
_cfg_analytics = _config["features"]["enable_analytics"]

ENABLE_JOURNAL: bool = get_env_var("ENABLE_JOURNAL", _cfg_journal, bool)
ENABLE_ANALYTICS: bool = get_env_var("ENABLE_ANALYTICS", _cfg_analytics, bool)

APP_CONFIG: Dict[str, Any] = _config

# Feature Flags Manager
# Import here to avoid circular imports since feature_flags may import from config
try:
    from app.feature_flags import feature_flags as FEATURE_FLAGS
except ImportError:
    FEATURE_FLAGS = None  # type: ignore


# Capacity Monitoring Configuration
_capacity_config = _config.get("capacity_monitoring", {})

CAPACITY_MONITORING_ENABLED: bool = get_env_var("CAPACITY_MONITORING_ENABLED", _capacity_config.get("enabled", False), bool)
CAPACITY_COLLECTION_INTERVAL_SECONDS: int = get_env_var("CAPACITY_COLLECTION_INTERVAL_SECONDS", _capacity_config.get("collection_interval_seconds", 300), int)
CAPACITY_RETENTION_DAYS: int = get_env_var("CAPACITY_RETENTION_DAYS", _capacity_config.get("retention_days", 30), int)
CAPACITY_FORECAST_WINDOW_HOURS: int = get_env_var("CAPACITY_FORECAST_WINDOW_HOURS", _capacity_config.get("forecast_window_hours", 24), int)
CAPACITY_MIN_HISTORICAL_POINTS: int = get_env_var("CAPACITY_MIN_HISTORICAL_POINTS", _capacity_config.get("min_historical_points", 10), int)
CAPACITY_CRITICAL_THRESHOLD: float = get_env_var("CAPACITY_CRITICAL_THRESHOLD", _capacity_config.get("critical_threshold_pct", 90.0), float)
CAPACITY_WARNING_THRESHOLD: float = get_env_var("CAPACITY_WARNING_THRESHOLD", _capacity_config.get("warning_threshold_pct", 75.0), float)
CAPACITY_SAFETY_MARGIN: float = get_env_var("CAPACITY_SAFETY_MARGIN", _capacity_config.get("safety_margin_pct", 20.0), float)