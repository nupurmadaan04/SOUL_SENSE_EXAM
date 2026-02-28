import logging
import logging.config
import os
from pythonjsonlogger import jsonlogger
from datetime import datetime

def setup_logging():
    """
    Configures centralized logging for the application.
    Uses structured JSON logging for non-debug environments.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    settings = None
    try:
        from ..api.config import get_settings_instance
        settings = get_settings_instance()
    except Exception:
        # Fallback if config is not loadable during early setup
        pass

    is_debug = settings.debug if settings else True
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "rename_fields": {
                    "levelname": "level",
                    "asctime": "timestamp"
                }
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard" if is_debug else "json",
            },
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(log_dir, "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": "INFO",
            },
            "api.auth": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "api.db": {
                "handlers": ["console", "file", "error_file"],
                "level": "INFO",
                "propagate": False,
            },
            "api.exam": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
        }
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Log that logging is configured
    root_logger = logging.getLogger("api.main")
    root_logger.info("Logging system initialized", extra={
        "debug_mode": is_debug,
        "log_directory": log_dir
    })
