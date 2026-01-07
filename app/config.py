import os
import json
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Default Configuration
DEFAULT_CONFIG = {
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

def load_config():
    """Load configuration from config.json or return defaults."""
    if not os.path.exists(CONFIG_PATH):
        logging.warning(f"Config file not found at {CONFIG_PATH}. Using defaults.")
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            # Use deepcopy to avoid mutating the global DEFAULT_CONFIG
            import copy
            merged = copy.deepcopy(DEFAULT_CONFIG)
            for section in ["database", "ui", "features"]:
                if section in config:
                    merged[section].update(config[section])
            return merged
    except Exception as e:
        logging.error(f"Failed to load config file: {e}. Using defaults.")
        # Return a deepcopy to be safe against downstream mutations too
        import copy
        return copy.deepcopy(DEFAULT_CONFIG)

# Load Config on Import
_config = load_config()

# Expose Settings
DB_DIR_NAME = _config["database"]["path"]
DB_FILENAME = _config["database"]["filename"]

# Calculated Paths
DB_PATH = os.path.join(BASE_DIR, DB_DIR_NAME, DB_FILENAME)
DATABASE_URL = f"sqlite:///{DB_PATH}"


# Ensure DB Directory Exists
if not os.path.exists(os.path.dirname(DB_PATH)):

    try:
        os.makedirs(os.path.dirname(DB_PATH))
    except OSError:
        pass # Handle race condition or permission error

# UI Settings
THEME = _config["ui"]["theme"]

# Feature Toggles
ENABLE_JOURNAL = _config["features"]["enable_journal"]
ENABLE_ANALYTICS = _config["features"]["enable_analytics"]
