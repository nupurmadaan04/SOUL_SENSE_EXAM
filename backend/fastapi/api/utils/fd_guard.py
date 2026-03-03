import os
import psutil
import logging
import threading
from typing import Optional

logger = logging.getLogger("api.utils.fd_guard")

class FDGuard:
    """
    Utility to monitor and protect against File Descriptor (FD) leaks.
    Logs warnings if the current process exceeds a specific threshold of open handles.
    """
    
    _process = psutil.Process()
    _lock = threading.Lock()
    _warning_threshold = 50  # Per-request context limit (theoretical)
    _critical_threshold = 800 # Process-wide limit (standard soft limit is often 1024)

    @classmethod
    def get_open_fd_count(cls) -> int:
        """Returns the number of open file descriptors for the current process."""
        try:
            return cls._process.num_fds()
        except (psutil.AccessDenied, AttributeError):
            # Fallback for systems where num_fds() might not be available or restricted
            return -1

    @classmethod
    def check_fd_usage(cls, context_name: str = "request"):
        """
        Checks current FD usage and logs a warning if it exceeds thresholds.
        Call this at the beginning or end of heavy I/O operations.
        """
        count = cls.get_open_fd_count()
        if count == -1:
            return

        if count > cls._critical_threshold:
            logger.critical(
                f"[FD_GUARD] CRITICAL: Process-wide File Descriptors at {count}. "
                f"Approaching system limit! Context: {context_name}"
            )
        elif count > 500: # Global warning
             logger.warning(
                f"[FD_GUARD] WARNING: High File Descriptor usage detected ({count}). "
                f"Context: {context_name}"
            )

    @classmethod
    def log_leak_warning(cls, filename: str, count: int):
        """Specifically logs a suspected leak for a file."""
        logger.warning(
            f"[FD_GUARD] SUSPECTED LEAK: File '{filename}' was not closed properly. "
            f"Current process FD count: {count}"
        )

# Global helper for middleware or decorators
def monitor_fd_usage(func):
    """Decorator to monitor FD usage around a function."""
    import functools
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        FDGuard.check_fd_usage(f"before_{func.__name__}")
        try:
            return await func(*args, **kwargs)
        finally:
            FDGuard.check_fd_usage(f"after_{func.__name__}")
    return wrapper
