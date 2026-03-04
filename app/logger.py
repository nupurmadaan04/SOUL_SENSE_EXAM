import logging
import os
import glob
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict

from app.config import LOG_DIR, get_env_var

# Log file constants
LOG_FILE: str = "soulsense.log"
ERROR_LOG_FILE: str = "soulsense_errors.log"

# Configurable via environment variables
MAX_BYTES: int = get_env_var("LOG_MAX_BYTES", 10 * 1024 * 1024, int)  # 10MB default
BACKUP_COUNT: int = get_env_var("LOG_BACKUP_COUNT", 5, int)  # 5 backups default
LOG_CLEANUP_ENABLED: bool = get_env_var("LOG_CLEANUP_ENABLED", True, bool)

# Logger cache for module-specific loggers
_loggers: Dict[str, logging.Logger] = {}

# Track if logging has been set up
_logging_initialized: bool = False


def cleanup_old_logs(log_dir: str, max_total_size_mb: int = 100) -> None:
    """
    Clean up old log files if total size exceeds threshold.
    
    Prevents disk inode and space exhaustion by removing oldest
    log files when total directory size exceeds max_total_size_mb.
    
    Args:
        log_dir: Directory containing log files
        max_total_size_mb: Maximum total size in MB before cleanup (default: 100MB)
    """
    if not os.path.exists(log_dir):
        return
    
    try:
        # Find all log files
        log_files = glob.glob(os.path.join(log_dir, "*.log*"))
        
        # Calculate total size
        total_size = sum(os.path.getsize(f) for f in log_files if os.path.isfile(f))
        max_bytes = max_total_size_mb * 1024 * 1024
        
        if total_size > max_bytes:
            # Sort by modification time (oldest first)
            log_files_sorted = sorted(log_files, key=os.path.getmtime)
            
            # Remove oldest files until under threshold
            for log_file in log_files_sorted:
                if total_size <= max_bytes:
                    break
                try:
                    file_size = os.path.getsize(log_file)
                    os.remove(log_file)
                    total_size -= file_size
                    logging.info(f"Cleaned up log file: {log_file}")
                except OSError as e:
                    logging.warning(f"Could not remove log file {log_file}: {e}")
    except Exception as e:
        logging.warning(f"Log cleanup failed: {e}")


def get_log_stats() -> Dict[str, any]:
    """
    Get statistics about current log files.
    
    Useful for monitoring disk usage and inode consumption.
    
    Returns:
        Dictionary with log file statistics
    """
    stats = {
        "log_dir": LOG_DIR,
        "exists": os.path.exists(LOG_DIR),
        "total_size_mb": 0,
        "file_count": 0,
        "files": []
    }
    
    if not os.path.exists(LOG_DIR):
        return stats
    
    try:
        log_files = glob.glob(os.path.join(LOG_DIR, "*.log*"))
        
        for log_file in log_files:
            try:
                size = os.path.getsize(log_file)
                mtime = os.path.getmtime(log_file)
                stats["files"].append({
                    "name": os.path.basename(log_file),
                    "size_mb": size / 1024 / 1024,
                    "size_bytes": size,
                    "mtime": mtime
                })
                stats["total_size_mb"] += size / 1024 / 1024
                stats["file_count"] += 1
            except OSError:
                pass
    except Exception as e:
        logging.warning(f"Could not get log statistics: {e}")
    
    return stats


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure centralized logging for the application.
    
    Sets up:
    - Console handler for all messages
    - File handler for all messages (rotating)
    - Separate error file handler for ERROR+ level (rotating)
    - Automatic log rotation at 10MB per file, max 5 backups
    - Log cleanup to prevent inode exhaustion
    
    Args:
        level: Minimum logging level (default: INFO)
        
    Environment Variables:
        SOULSENSE_LOG_MAX_BYTES: Max bytes per log file (default: 10485760)
        SOULSENSE_LOG_BACKUP_COUNT: Number of backup files (default: 5)
        SOULSENSE_LOG_CLEANUP_ENABLED: Enable cleanup of old logs (default: true)
        SOULSENSE_LOG_LEVEL: Logging level (default: INFO)
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

    # File Handler - All messages with rotation
    file_handler = RotatingFileHandler(
        log_path, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error File Handler - ERROR level and above with rotation
    error_file_handler = RotatingFileHandler(
        error_log_path, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding='utf-8'
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
    
    # Run cleanup if enabled
    if LOG_CLEANUP_ENABLED:
        cleanup_old_logs(LOG_DIR)
    
    logging.info(f"Logging initialized. Max file size: {MAX_BYTES / 1024 / 1024:.0f}MB, Backups: {BACKUP_COUNT}")


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


def log_test_metric(
    test_name: str,
    category: str,
    passed: bool,
    duration_ms: float,
    error: Optional[str] = None
) -> None:
    """
    Log a test execution metric (Issue #1315).
    
    Used by test environment fidelity monitoring to track:
    - Unit, integration, and edge case tests
    - Pass/fail status
    - Execution duration
    - Error details
    
    Args:
        test_name: Name of the test
        category: Test category ('unit', 'integration', 'edge_case')
        passed: Whether test passed
        duration_ms: Test execution duration in milliseconds
        error: Error message if test failed
    """
    status = "PASS" if passed else "FAIL"
    logger = get_logger("tests.fidelity")
    
    msg = f"TEST[{category.upper()}] {test_name}: {status} ({duration_ms:.2f}ms)"
    
    if error:
        logger.error(f"{msg} - Error: {error}")
    else:
        logger.info(msg)


def log_environment_context(environment: str, metadata: Optional[Dict] = None) -> None:
    """
    Log test environment context (Issue #1315).
    
    Used to document environment in which tests run.
    
    Args:
        environment: Environment name ('test', 'ci', 'local', etc.)
        metadata: Optional dict with environment metadata
    """
    logger = get_logger("tests.environment")
    
    msg = f"Environment: {environment}"
    if metadata:
        msg += f" | {metadata}"
    
    logger.info(msg)
