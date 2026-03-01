import logging
import logging.config
import os
import re
from pythonjsonlogger import jsonlogger
from datetime import datetime

# Regex for masking credentials in URLs (e.g., postgres://user:password@host:port/db)
URL_CREDENTIAL_RE = re.compile(r'(?P<prefix>://[^:]+:)(?P<password>[^@]+)(?P<suffix>@)')

def mask_sensitive_data(data):
    """
    Recursively masks sensitive keys in a dictionary or list.
    """
    SENSITIVE_KEYS = {
        'password', 'token', 'otp', 'secret', 'credential', 
        'cvv', 'auth', 'authorization', 'api_key', 'access_token',
        'refresh_token', 'private_key', 'passphrase', 'signature',
        'cookie', 'session', 'jwt'
    }
    
    if isinstance(data, dict):
        return {
            k: ("********" if any(s in k.lower() for s in SENSITIVE_KEYS) else mask_sensitive_data(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        # Mask credentials in URLs
        return URL_CREDENTIAL_RE.sub(r'\g<prefix>********\g<suffix>', data)
    return data

class SensitiveDataFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that masks sensitive information in 'extra' fields and messages.
    """
    def add_fields(self, log_record, record, message_dict):
        super(SensitiveDataFormatter, self).add_fields(log_record, record, message_dict)
        
        # Keys that might contain sensitive data or stack traces
        TEXT_KEYS = {'message', 'exc_info', 'stack_trace', 'traceback', 'exception'}

        # Mask fields in the log record
        for key in list(log_record.keys()):
            if key in TEXT_KEYS and isinstance(log_record[key], str):
                # Apply regex masking for common patterns in text/stack traces
                log_record[key] = re.sub(
                    r'(password|token|otp|secret|credential|api_key|auth|authorization)=[^&\s\n\',"]+', 
                    r'\1=********', 
                    log_record[key], 
                    flags=re.IGNORECASE
                )
                # Also mask URLs in text
                log_record[key] = mask_sensitive_data(log_record[key])
            else:
                log_record[key] = mask_sensitive_data(log_record[key])

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

    # Safety: Default to False (structured/non-debug) if we can't determine the env
    is_debug = settings.debug if settings else False
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "()": SensitiveDataFormatter,
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "rename_fields": {
                    "levelname": "level",
                    "asctime": "timestamp"
                }
            },
        },
        "handlers": {
            "console": {
                "level": "INFO" if not is_debug else "DEBUG",
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
                "level": "INFO" if not is_debug else "DEBUG",
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
