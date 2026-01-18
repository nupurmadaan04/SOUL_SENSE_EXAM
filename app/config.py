import os
import json
import logging
import copy
from typing import Dict, Any, Union, Optional

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading

from app.exceptions import ConfigurationError

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH: str = os.path.join(BASE_DIR, "config.json")


def get_env_var(name: str, default: Optional[str] = None, 
                var_type: type = str) -> Optional[Any]:
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
            for section in ["database", "ui", "features"]:
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
    try:
        with open(CONFIG_PATH, "w") as f:
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

DATABASE_URL: str = f"sqlite:///{DB_PATH}"



# Ensure DB Directory Exists
if not os.path.exists(os.path.dirname(DB_PATH)):

    try:
        os.makedirs(os.path.dirname(DB_PATH))
    except OSError:
        pass # Handle race condition or permission error

# UI Settings
THEME: str = _config["ui"]["theme"]

# Feature Toggles (env vars take precedence over config file)
_cfg_journal = _config["features"]["enable_journal"]
_cfg_analytics = _config["features"]["enable_analytics"]

ENABLE_JOURNAL: bool = get_env_var("ENABLE_JOURNAL", _cfg_journal, bool)
ENABLE_ANALYTICS: bool = get_env_var("ENABLE_ANALYTICS", _cfg_analytics, bool)

APP_CONFIG: Dict[str, Any] = _config
