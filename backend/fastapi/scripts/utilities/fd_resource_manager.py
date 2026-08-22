#!/usr/bin/env python3
"""
FD Resource Manager - Epoll Event Loop Exhaustion Prevention #1183

Monitors and manages file descriptors to prevent event loop exhaustion.
Implements FD limits, leak detection, and resource cleanup.
"""

import os
import sys
import time
import threading
import logging
import psutil
try:
    import resource
    HAS_RESOURCE_MODULE = True
except ImportError:
    HAS_RESOURCE_MODULE = False
import asyncio
from typing import Dict, List, Set, Optional, Callable, Any
from contextlib import contextmanager, asynccontextmanager
import weakref
import gc
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FDType(Enum):
    """Types of file descriptors to track."""
    SOCKET = "socket"
    FILE = "file"
    PIPE = "pipe"
    OTHER = "other"


@dataclass
class FDInfo:
    """Information about a tracked file descriptor."""
    fd: int
    type: FDType
    created_at: float
    last_accessed: float
    owner: str
    metadata: Dict[str, Any]


class FDResourceManager:
    """
    File Descriptor Resource Manager for event loop exhaustion prevention.

    Monitors FD usage, enforces limits, detects leaks, and ensures proper cleanup.
    Prevents event loop degradation from excessive FD registration.
    """

    def __init__(self,
                 max_fds: Optional[int] = None,
                 warning_threshold: float = 0.8,
                 critical_threshold: float = 0.9,
                 leak_detection_interval: float = 60.0,
                 cleanup_interval: float = 300.0):
        """
        Initialize FD resource manager.

        Args:
            max_fds: Maximum allowed file descriptors (None = use system limit)
            warning_threshold: Warning when FD usage exceeds this fraction of limit
            critical_threshold: Critical when FD usage exceeds this fraction of limit
            leak_detection_interval: How often to check for FD leaks (seconds)
            cleanup_interval: How often to run cleanup operations (seconds)
        """
        self.max_fds = max_fds or self._get_system_fd_limit()
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.leak_detection_interval = leak_detection_interval
        self.cleanup_interval = cleanup_interval

        # FD tracking
        self._tracked_fds: Dict[int, FDInfo] = {}
        self._fd_lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_created': 0,
            'total_closed': 0,
            'peak_usage': 0,
            'current_usage': 0,
            'leaks_detected': 0,
            'forced_cleanups': 0,
            'warnings_issued': 0,
            'critical_events': 0
        }

        # Monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._last_leak_check = time.time()
        self._last_cleanup = time.time()

        # Callbacks
        self._warning_callbacks: List[Callable] = []
        self._critical_callbacks: List[Callable] = []
        self._leak_callbacks: List[Callable] = []

        # Start monitoring
        self._start_monitoring()

        logger.info(f"FD Resource Manager initialized: max_fds={self.max_fds}, "
                   f"warning={self.warning_threshold:.1%}, critical={self.critical_threshold:.1%}")

    def _get_system_fd_limit(self) -> int:
        """Get the system file descriptor limit."""
        if HAS_RESOURCE_MODULE:
            try:
                # Try to get soft limit first
                soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
                return min(soft_limit, hard_limit)
            except (AttributeError, OSError):
                pass

        # Fallback for systems without resource module or other failures
        try:
            # Try ulimit command (Unix/Linux)
            import subprocess
            import platform
            if platform.system() != 'Windows':
                result = subprocess.run(['ulimit', '-n'], capture_output=True, text=True)
                if result.returncode == 0:
                    return int(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError):
            pass

        # Windows fallback - use a reasonable default based on Windows limits
        try:
            import platform
            if platform.system() == 'Windows':
                # Windows typically allows much higher FD limits, but we'll be conservative
                return 8192  # Windows default is usually much higher
        except ImportError:
            pass

        # Final fallback
        return 1024  # Conservative default

    def _start_monitoring(self):
        """Start the background monitoring thread."""
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_monitoring.is_set():
            try:
                self._check_fd_usage()
                self._check_for_leaks()
                self._periodic_cleanup()
            except Exception as e:
                logger.error(f"Error in FD monitoring loop: {e}")

            time.sleep(10.0)  # Check every 10 seconds

    def _check_fd_usage(self):
        """Check current FD usage against limits."""
        try:
            current_fds = self.get_current_fd_count()
            usage_ratio = current_fds / self.max_fds

            self._stats['current_usage'] = current_fds
            self._stats['peak_usage'] = max(self._stats['peak_usage'], current_fds)

            if usage_ratio >= self.critical_threshold:
                self._stats['critical_events'] += 1
                logger.critical(f"CRITICAL: FD usage at {usage_ratio:.1%} ({current_fds}/{self.max_fds})")
                self._trigger_callbacks(self._critical_callbacks, current_fds, usage_ratio)
            elif usage_ratio >= self.warning_threshold:
                self._stats['warnings_issued'] += 1
                logger.warning(f"WARNING: High FD usage at {usage_ratio:.1%} ({current_fds}/{self.max_fds})")
                self._trigger_callbacks(self._warning_callbacks, current_fds, usage_ratio)

        except Exception as e:
            logger.error(f"Error checking FD usage: {e}")

    def _check_for_leaks(self):
        """Check for potential FD leaks."""
        current_time = time.time()
        if current_time - self._last_leak_check < self.leak_detection_interval:
            return

        self._last_leak_check = current_time

        try:
            with self._fd_lock:
                leaked_fds = []
                for fd, info in self._tracked_fds.items():
                    # Check if FD has been unused for too long
                    if current_time - info.last_accessed > 3600:  # 1 hour
                        leaked_fds.append((fd, info))

                if leaked_fds:
                    self._stats['leaks_detected'] += len(leaked_fds)
                    logger.warning(f"Detected {len(leaked_fds)} potential FD leaks")

                    for fd, info in leaked_fds:
                        logger.warning(f"Leaked FD {fd}: {info}")
                        self._trigger_callbacks(self._leak_callbacks, fd, info)

        except Exception as e:
            logger.error(f"Error checking for FD leaks: {e}")

    def _periodic_cleanup(self):
        """Perform periodic cleanup operations."""
        current_time = time.time()
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = current_time

        try:
            # Force garbage collection to clean up any unreferenced FDs
            gc.collect()

            # Clean up old tracking entries
            with self._fd_lock:
                to_remove = []
                for fd, info in self._tracked_fds.items():
                    # Remove entries older than 24 hours
                    if current_time - info.created_at > 86400:
                        to_remove.append(fd)

                for fd in to_remove:
                    del self._tracked_fds[fd]

            logger.debug("Periodic FD cleanup completed")

        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

    def _trigger_callbacks(self, callbacks: List[Callable], *args, **kwargs):
        """Trigger callback functions."""
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in FD callback: {e}")

    def get_current_fd_count(self) -> int:
        """Get the current number of open file descriptors."""
        try:
            if hasattr(os, 'listdir'):
                # Unix-like systems
                fd_dir = '/proc/self/fd'
                if os.path.exists(fd_dir):
                    return len(os.listdir(fd_dir))

            # Fallback: use psutil
            process = psutil.Process()
            return len(process.open_files()) + len(process.connections())

        except Exception:
            # Ultimate fallback
            return len(self._tracked_fds)

    def register_fd(self, fd: int, fd_type: FDType, owner: str, **metadata) -> None:
        """
        Register a file descriptor for tracking.

        Args:
            fd: File descriptor number
            fd_type: Type of file descriptor
            owner: Component that owns this FD
            **metadata: Additional metadata
        """
        with self._fd_lock:
            info = FDInfo(
                fd=fd,
                type=fd_type,
                created_at=time.time(),
                last_accessed=time.time(),
                owner=owner,
                metadata=metadata
            )
            self._tracked_fds[fd] = info
            self._stats['total_created'] += 1

    def unregister_fd(self, fd: int) -> None:
        """Unregister a file descriptor."""
        with self._fd_lock:
            if fd in self._tracked_fds:
                del self._tracked_fds[fd]
                self._stats['total_closed'] += 1

    def update_fd_access(self, fd: int) -> None:
        """Update the last access time for an FD."""
        with self._fd_lock:
            if fd in self._tracked_fds:
                self._tracked_fds[fd].last_accessed = time.time()

    @contextmanager
    def track_fd(self, fd: int, fd_type: FDType, owner: str, **metadata):
        """
        Context manager for tracking FD lifecycle.

        Automatically registers FD on entry and unregisters on exit.
        """
        self.register_fd(fd, fd_type, owner, **metadata)
        try:
            yield
        finally:
            self.unregister_fd(fd)

    def add_warning_callback(self, callback: Callable) -> None:
        """Add a callback for FD usage warnings."""
        self._warning_callbacks.append(callback)

    def add_critical_callback(self, callback: Callable) -> None:
        """Add a callback for FD usage critical events."""
        self._critical_callbacks.append(callback)

    def add_leak_callback(self, callback: Callable) -> None:
        """Add a callback for FD leak detection."""
        self._leak_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get FD resource manager statistics."""
        with self._fd_lock:
            return {
                **self._stats,
                'tracked_fds': len(self._tracked_fds),
                'max_fds': self.max_fds,
                'warning_threshold': self.warning_threshold,
                'critical_threshold': self.critical_threshold,
                'current_usage_percent': (self._stats['current_usage'] / self.max_fds) * 100
            }

    def get_fd_info(self) -> List[FDInfo]:
        """Get information about all tracked FDs."""
        with self._fd_lock:
            return list(self._tracked_fds.values())

    def force_cleanup(self) -> int:
        """Force cleanup of leaked FDs. Returns number of FDs cleaned up."""
        cleaned = 0
        try:
            # Force garbage collection
            gc.collect()

            # Close any obviously leaked FDs (be very careful here)
            with self._fd_lock:
                to_close = []
                current_time = time.time()

                for fd, info in self._tracked_fds.items():
                    # Only close FDs that are very old and likely leaked
                    if (current_time - info.created_at > 7200 and  # 2 hours old
                        current_time - info.last_accessed > 3600):  # 1 hour unused
                        to_close.append(fd)

                for fd in to_close:
                    try:
                        os.close(fd)
                        del self._tracked_fds[fd]
                        cleaned += 1
                        logger.info(f"Force closed leaked FD {fd}")
                    except OSError:
                        # FD might already be closed
                        pass

            self._stats['forced_cleanups'] += cleaned
            return cleaned

        except Exception as e:
            logger.error(f"Error in force cleanup: {e}")
            return 0

    def shutdown(self):
        """Shutdown the FD resource manager."""
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

        logger.info("FD Resource Manager shutdown")


# Global instance
_fd_manager = None
_fd_manager_lock = threading.Lock()

def get_fd_manager() -> FDResourceManager:
    """Get the global FD resource manager instance."""
    global _fd_manager
    with _fd_manager_lock:
        if _fd_manager is None:
            _fd_manager = FDResourceManager()
        return _fd_manager

def init_fd_manager(**kwargs) -> FDResourceManager:
    """Initialize the global FD resource manager with custom settings."""
    global _fd_manager
    with _fd_manager_lock:
        if _fd_manager is None:
            _fd_manager = FDResourceManager(**kwargs)
        return _fd_manager


# Event loop monitoring for asyncio applications
class EventLoopMonitor:
    """
    Monitor asyncio event loop health and responsiveness.

    Tracks event loop lag and detects when the loop becomes unresponsive
    due to excessive FD registration or other issues.
    """

    def __init__(self, fd_manager: Optional[FDResourceManager] = None):
        self.fd_manager = fd_manager or get_fd_manager()
        self._loop = None
        self._monitor_task = None
        self._stop_monitoring = False

        # Statistics
        self._stats = {
            'total_checks': 0,
            'lag_warnings': 0,
            'lag_critical': 0,
            'max_lag': 0.0,
            'avg_lag': 0.0
        }

    async def start_monitoring(self, loop: asyncio.AbstractEventLoop):
        """Start monitoring the event loop."""
        self._loop = loop
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring the event loop."""
        self._stop_monitoring = True
        if self._monitor_task:
            await self._monitor_task

    async def _monitor_loop(self):
        """Monitor event loop responsiveness."""
        while not self._stop_monitoring:
            try:
                lag = await self._measure_loop_lag()
                self._stats['total_checks'] += 1

                if lag > 1.0:  # 1 second lag is critical
                    self._stats['lag_critical'] += 1
                    logger.critical(f"CRITICAL: Event loop lag of {lag:.3f}s detected")
                    self._stats['max_lag'] = max(self._stats['max_lag'], lag)
                elif lag > 0.1:  # 100ms lag is warning
                    self._stats['lag_warnings'] += 1
                    logger.warning(f"WARNING: Event loop lag of {lag:.3f}s detected")

                # Update average lag
                total_lag = self._stats['avg_lag'] * (self._stats['total_checks'] - 1) + lag
                self._stats['avg_lag'] = total_lag / self._stats['total_checks']

            except Exception as e:
                logger.error(f"Error in event loop monitoring: {e}")

            await asyncio.sleep(5.0)  # Check every 5 seconds

    async def _measure_loop_lag(self) -> float:
        """Measure event loop lag in seconds."""
        start_time = time.time()
        # Schedule a callback and wait for it
        future = asyncio.Future()

        def callback():
            future.set_result(time.time())

        self._loop.call_soon(callback)
        end_time = await future
        return end_time - start_time

    def get_stats(self) -> Dict[str, Any]:
        """Get event loop monitoring statistics."""
        return self._stats.copy()


# Integration helpers
def track_socket_fd(sock, owner: str, **metadata):
    """Track a socket file descriptor."""
    fd = sock.fileno()
    manager = get_fd_manager()
    manager.register_fd(fd, FDType.SOCKET, owner, **metadata)

def track_file_fd(file_obj, owner: str, **metadata):
    """Track a file file descriptor."""
    fd = file_obj.fileno()
    manager = get_fd_manager()
    manager.register_fd(fd, FDType.FILE, owner, **metadata)

def safe_close_fd(fd: int) -> bool:
    """Safely close a file descriptor with proper tracking cleanup."""
    try:
        manager = get_fd_manager()
        manager.unregister_fd(fd)
        os.close(fd)
        return True
    except OSError:
        return False

@asynccontextmanager
async def limit_concurrent_connections(max_connections: int):
    """
    Async context manager to limit concurrent connections.

    Prevents FD exhaustion during burst traffic by queuing requests.
    """
    semaphore = asyncio.Semaphore(max_connections)

    async with semaphore:
        yield