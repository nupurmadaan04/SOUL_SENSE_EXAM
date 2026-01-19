import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict

from app.config import LOG_DIR

# Log file constants
LOG_FILE: str = "soulsense.log"
ERROR_LOG_FILE: str = "soulsense_errors.log"
MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT: int = 5

# Logger cache for module-specific loggers
_loggers: Dict[str, logging.Logger] = {}

# Track if logging has been set up
_logging_initialized: bool = False


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure centralized logging for the application.
    
    Sets up:
    - Console handler for all messages
    - File handler for all messages (rotating)
    - Separate error file handler for ERROR+ level (rotating)
    
    Args:
        level: Minimum logging level (default: INFO)
    """
    global _logging_initialized
    
    if _logging_initialized:
        return
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_path = os.path.join(LOG_DIR, LOG_FILE)
    error_log_path = os.path.join(LOG_DIR, ERROR_LOG_FILE)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove default handlers if any (to avoid duplication)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Define log format with structured info
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )

    # File Handler - All messages
    file_handler = RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error File Handler - ERROR level and above only
    error_file_handler = RotatingFileHandler(
        error_log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    _logging_initialized = True
    logging.info("Logging initialized.")


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    This provides a consistent way to get module-specific loggers
    that inherit from the root logger configuration.
    
    Args:
        module_name: Name of the module (typically __name__)
        
    Returns:
        Logger instance for the module
        
    Example:
        logger = get_logger(__name__)
        logger.info("Module initialized")
    """
    if module_name not in _loggers:
        _loggers[module_name] = logging.getLogger(module_name)
    return _loggers[module_name]


def log_exception(
    exception: Exception,
    message: str = "An error occurred",
    module: Optional[str] = None,
    level: int = logging.ERROR
) -> None:
    """
    Log an exception with consistent formatting.
    
    Args:
        exception: The exception to log
        message: Context message
        module: Module name (optional)
        level: Logging level (default: ERROR)
    """
    logger = get_logger(module) if module else logging.getLogger()
    
    error_type = type(exception).__name__
    full_message = f"{message}: [{error_type}] {exception}"
    
    logger.log(level, full_message, exc_info=(level >= logging.ERROR))

