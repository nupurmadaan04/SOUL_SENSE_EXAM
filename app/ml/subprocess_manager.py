"""
Subprocess Manager for ML Services.

Ensures proper cleanup of ML subprocesses to prevent orphaned processes.
Uses process groups and atexit handlers for reliable termination.
"""

import os
import signal
import atexit
import logging
import psutil
import subprocess
from typing import Dict, Optional, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MLSubprocessManager:
    """
    Manages ML subprocesses with proper cleanup to prevent orphaned processes.

    Features:
    - Process group management for clean termination
    - Automatic cleanup on parent exit
    - Signal handling for graceful shutdown
    - Process monitoring and health checks
    """

    def __init__(self):
        self._processes: Dict[str, psutil.Process] = {}
        self._process_groups: Dict[str, int] = {}
        self._atexit_registered = False
        self._setup_atexit_handler()

    def _setup_atexit_handler(self):
        """Register atexit handler for cleanup"""
        if not self._atexit_registered:
            atexit.register(self.cleanup_all)
            self._atexit_registered = True

    def start_ml_process(self, name: str, cmd: List[str], cwd: Optional[str] = None) -> Optional[psutil.Process]:
        """
        Start an ML subprocess with proper process group management.

        Args:
            name: Unique name for the process
            cmd: Command to execute
            cwd: Working directory

        Returns:
            psutil.Process instance or None if failed
        """
        try:
            # Create new process group for the child
            if hasattr(os, 'setsid'):  # Unix-like systems
                process = psutil.Popen(
                    cmd,
                    cwd=cwd,
                    preexec_fn=os.setsid,  # Create new session/process group
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                pgid = os.getsid(process.pid)
            else:  # Windows
                process = psutil.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                pgid = process.pid  # On Windows, pid is used as process group

            self._processes[name] = process
            self._process_groups[name] = pgid

            logger.info(f"Started ML subprocess '{name}' with PID {process.pid}, PGID {pgid}")
            return process

        except Exception as e:
            logger.error(f"Failed to start ML subprocess '{name}': {e}")
            return None

    def terminate_process(self, name: str, timeout: float = 5.0) -> bool:
        """
        Terminate a specific ML subprocess gracefully.

        Args:
            name: Process name
            timeout: Timeout for graceful termination

        Returns:
            True if terminated successfully
        """
        if name not in self._processes:
            logger.warning(f"Process '{name}' not found")
            return False

        process = self._processes[name]
        pgid = self._process_groups.get(name)

        try:
            if process.is_running():
                logger.info(f"Terminating ML subprocess '{name}' (PID {process.pid})")

                # Try graceful termination first
                if pgid and hasattr(os, 'killpg'):  # Unix-like systems
                    try:
                        os.killpg(pgid, signal.SIGTERM)
                        # Wait for graceful shutdown
                        process.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        # Force kill if graceful shutdown fails
                        os.killpg(pgid, signal.SIGKILL)
                        process.wait(timeout=2.0)
                else:  # Windows or fallback
                    process.terminate()
                    try:
                        process.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2.0)

                logger.info(f"Successfully terminated ML subprocess '{name}'")
                return True
            else:
                logger.info(f"ML subprocess '{name}' already terminated")
                return True

        except Exception as e:
            logger.error(f"Error terminating ML subprocess '{name}': {e}")
            return False
        finally:
            # Clean up references
            self._processes.pop(name, None)
            self._process_groups.pop(name, None)

    def cleanup_all(self):
        """Clean up all ML subprocesses"""
        logger.info("Cleaning up all ML subprocesses...")

        terminated = []
        failed = []

        for name in list(self._processes.keys()):
            if self.terminate_process(name):
                terminated.append(name)
            else:
                failed.append(name)

        if terminated:
            logger.info(f"Successfully terminated processes: {terminated}")
        if failed:
            logger.error(f"Failed to terminate processes: {failed}")

        self._processes.clear()
        self._process_groups.clear()

    def get_running_processes(self) -> List[str]:
        """Get list of currently running ML process names"""
        running = []
        for name, process in self._processes.items():
            if process.is_running():
                running.append(name)
        return running

    def is_process_running(self, name: str) -> bool:
        """Check if a specific process is running"""
        process = self._processes.get(name)
        return process is not None and process.is_running()

    def get_process_info(self, name: str) -> Optional[Dict]:
        """Get information about a specific process"""
        process = self._processes.get(name)
        if process and process.is_running():
            return {
                'pid': process.pid,
                'pgid': self._process_groups.get(name),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(),
                'memory_info': process.memory_info()._asdict()
            }
        return None


# Global instance
_ml_subprocess_manager = None

def get_ml_subprocess_manager() -> MLSubprocessManager:
    """Get the global ML subprocess manager instance"""
    global _ml_subprocess_manager
    if _ml_subprocess_manager is None:
        _ml_subprocess_manager = MLSubprocessManager()
    return _ml_subprocess_manager


@contextmanager
def managed_ml_process(name: str, cmd: List[str], cwd: Optional[str] = None):
    """
    Context manager for ML subprocesses with automatic cleanup.

    Usage:
        with managed_ml_process('inference_server', ['python', 'server.py']):
            # Process is running here
            pass
        # Process is automatically terminated here
    """
    manager = get_ml_subprocess_manager()
    process = manager.start_ml_process(name, cmd, cwd)

    if process is None:
        raise RuntimeError(f"Failed to start ML process '{name}'")

    try:
        yield process
    finally:
        manager.terminate_process(name)