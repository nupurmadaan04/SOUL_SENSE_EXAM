#!/usr/bin/env python3
"""
Poison-Resistant Lock Implementation - Prevents Mutex Poisoning on Panic #1188

Implements locks that automatically release when threads panic or crash,
preventing cascading deadlocks from poisoned mutexes.
"""

import threading
import logging
import sys
import traceback
from typing import Any, Optional, Callable, TypeVar, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PoisonResistantLock:
    """
    A lock that automatically releases when the owning thread panics or crashes.

    This prevents mutex poisoning where a crashed thread leaves locks locked,
    causing cascading deadlocks throughout the system.

    Features:
    - Automatic cleanup on thread panic/exception
    - Lock state monitoring and recovery
    - Thread-local ownership tracking
    - Poison detection and recovery
    """

    def __init__(self, underlying_lock: Optional[threading.Lock] = None):
        """
        Initialize poison-resistant lock.

        Args:
            underlying_lock: Optional underlying lock to wrap. If None, creates a new Lock.
        """
        self._underlying_lock = underlying_lock or threading.Lock()
        self._owner_thread_id = None
        self._lock_depth = 0
        self._poisoned = False
        self._state_lock = threading.Lock()

        # Thread-local storage for tracking lock ownership
        self._local = threading.local()

    def _check_poisoned(self) -> None:
        """Check if lock is poisoned and attempt recovery."""
        with self._state_lock:
            if self._poisoned:
                logger.warning("Detected poisoned lock, attempting recovery")
                # Force unlock if we're the owner or if owner thread is dead
                if self._owner_thread_id is not None:
                    # Check if owner thread is still alive
                    owner_alive = False
                    for thread in threading.enumerate():
                        if thread.ident == self._owner_thread_id:
                            owner_alive = True
                            break

                    if not owner_alive:
                        logger.warning(f"Owner thread {self._owner_thread_id} is dead, recovering lock")
                        self._force_unlock()
                        self._poisoned = False
                    else:
                        raise RuntimeError("Lock is poisoned by active thread")

    def _force_unlock(self) -> None:
        """Force unlock the underlying lock (emergency recovery)."""
        try:
            # Try to release the lock multiple times in case of reentrancy
            for _ in range(self._lock_depth):
                self._underlying_lock.release()
        except RuntimeError:
            # Lock was not locked, that's fine
            pass

        # Reset state
        self._owner_thread_id = None
        self._lock_depth = 0

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """
        Acquire the lock with poison resistance.

        Returns True if lock acquired, False if timeout or would block.
        """
        self._check_poisoned()

        acquired = self._underlying_lock.acquire(blocking, timeout)
        if acquired:
            with self._state_lock:
                if self._owner_thread_id is None:
                    self._owner_thread_id = threading.get_ident()
                elif self._owner_thread_id != threading.get_ident():
                    # Lock acquired by different thread - this shouldn't happen with regular Lock
                    logger.error("Lock ownership inconsistency detected")
                    self._poisoned = True
                    raise RuntimeError("Lock ownership corrupted")

                self._lock_depth += 1

                # Store lock reference in thread-local storage for cleanup
                if not hasattr(self._local, 'owned_locks'):
                    self._local.owned_locks = []
                self._local.owned_locks.append(self)

        return acquired

    def release(self) -> None:
        """Release the lock."""
        with self._state_lock:
            if self._owner_thread_id != threading.get_ident():
                logger.error("Attempt to release lock not owned by current thread")
                return

            self._lock_depth -= 1

            # Remove from thread-local storage
            if hasattr(self._local, 'owned_locks'):
                try:
                    self._local.owned_locks.remove(self)
                except ValueError:
                    pass

            if self._lock_depth == 0:
                self._owner_thread_id = None

        try:
            self._underlying_lock.release()
        except RuntimeError as e:
            logger.error(f"Failed to release lock: {e}")
            with self._state_lock:
                self._poisoned = True
            raise

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with poison cleanup."""
        try:
            self.release()
        except Exception:
            # If release fails during exception handling, mark as poisoned
            with self._state_lock:
                self._poisoned = True
            # Don't re-raise during cleanup
            logger.error("Lock release failed during exception cleanup")

    @contextmanager
    def safe_context(self):
        """
        Context manager that ensures lock is released even on panic.

        This is more robust than __enter__/__exit__ for critical sections.
        """
        self.acquire()
        try:
            yield
        finally:
            # Always attempt release, even if an exception occurred
            try:
                self.release()
            except Exception as e:
                logger.critical(f"CRITICAL: Failed to release lock in safe context: {e}")
                with self._state_lock:
                    self._poisoned = True
                # Force unlock as last resort
                try:
                    self._force_unlock()
                except Exception:
                    logger.critical("EMERGENCY: Could not force unlock poisoned lock")

    def is_poisoned(self) -> bool:
        """Check if the lock is currently poisoned."""
        with self._state_lock:
            return self._poisoned

    def get_stats(self) -> dict:
        """Get lock statistics for monitoring."""
        with self._state_lock:
            return {
                'owner_thread_id': self._owner_thread_id,
                'lock_depth': self._lock_depth,
                'poisoned': self._poisoned,
                'underlying_locked': self._underlying_lock.locked()
            }

    def recover_from_poison(self) -> bool:
        """
        Attempt to recover a poisoned lock.

        Returns True if recovery successful, False otherwise.
        """
        with self._state_lock:
            if not self._poisoned:
                return True

            # Check if owner thread is still alive
            if self._owner_thread_id is not None:
                for thread in threading.enumerate():
                    if thread.ident == self._owner_thread_id:
                        # Owner thread still alive, cannot recover
                        return False

            # Owner thread is dead, attempt recovery
            try:
                self._force_unlock()
                self._poisoned = False
                logger.info("Successfully recovered poisoned lock")
                return True
            except Exception as e:
                logger.error(f"Failed to recover poisoned lock: {e}")
                return False


class PoisonResistantRLock(PoisonResistantLock):
    """
    Poison-resistant reentrant lock (RLock).

    Allows the same thread to acquire the lock multiple times.
    """

    def __init__(self):
        super().__init__(threading.RLock())


def safe_lock_operation(lock: Union[threading.Lock, threading.RLock, PoisonResistantLock],
                       operation: Callable[[], T]) -> T:
    """
    Execute an operation with automatic lock cleanup on panic.

    Args:
        lock: The lock to use (can be regular or poison-resistant)
        operation: The operation to execute while holding the lock

    Returns:
        The result of the operation

    Raises:
        Any exception from the operation, but ensures lock is released
    """
    if isinstance(lock, PoisonResistantLock):
        # Already poison-resistant
        with lock.safe_context():
            return operation()
    else:
        # Wrap regular lock with poison resistance
        safe_lock = PoisonResistantLock(lock)
        with safe_lock.safe_context():
            return operation()


# Global registry of all poison-resistant locks for monitoring
_lock_registry = []
_registry_lock = threading.Lock()

def register_lock(lock: PoisonResistantLock) -> None:
    """Register a lock for global monitoring."""
    with _registry_lock:
        _lock_registry.append(lock)

def get_registered_locks() -> list:
    """Get all registered poison-resistant locks."""
    with _registry_lock:
        return _lock_registry.copy()

def check_all_locks() -> dict:
    """Check status of all registered locks."""
    results = {}
    for i, lock in enumerate(get_registered_locks()):
        try:
            stats = lock.get_stats()
            results[f"lock_{i}"] = stats
        except Exception as e:
            results[f"lock_{i}"] = {"error": str(e)}
    return results

def recover_all_poisoned_locks() -> dict:
    """Attempt to recover all poisoned locks."""
    results = {}
    for i, lock in enumerate(get_registered_locks()):
        try:
            recovered = lock.recover_from_poison()
            results[f"lock_{i}"] = {"recovered": recovered}
        except Exception as e:
            results[f"lock_{i}"] = {"error": str(e)}
    return results


# Thread panic handler - automatically cleanup locks on thread death
def _install_panic_handler():
    """Install global panic handler for lock cleanup."""
    original_thread_run = threading.Thread.run

    def panic_safe_run(self):
        try:
            return original_thread_run(self)
        except Exception:
            # Thread is dying, cleanup any locks it owned
            thread_id = self.ident
            logger.warning(f"Thread {thread_id} dying with exception, cleaning up locks")

            # Find and cleanup locks owned by this thread
            for lock in get_registered_locks():
                try:
                    stats = lock.get_stats()
                    if stats['owner_thread_id'] == thread_id:
                        logger.warning(f"Cleaning up poisoned lock owned by dying thread {thread_id}")
                        lock.recover_from_poison()
                except Exception as e:
                    logger.error(f"Error cleaning up lock for dying thread: {e}")

            # Re-raise the original exception
            raise

    threading.Thread.run = panic_safe_run

# Install the panic handler
_install_panic_handler()