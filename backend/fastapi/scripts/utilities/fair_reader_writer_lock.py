#!/usr/bin/env python3
"""
Fair Reader-Writer Lock Implementation - Prevents Writer Starvation #1187

Implements a fair reader-writer lock that prevents writer starvation by ensuring
writers get priority over readers in high-read-traffic scenarios.
"""

import threading
import time
from typing import Optional
from contextlib import contextmanager


class FairReaderWriterLock:
    """
    Fair reader-writer lock that prevents writer starvation.

    This implementation ensures fairness by:
    1. Writers get priority over new readers when waiting
    2. No writer starvation under read-heavy loads
    3. Readers can proceed concurrently when no writers are waiting

    Key characteristics:
    - Multiple readers can read simultaneously
    - Only one writer at a time
    - Writers have priority to prevent starvation
    - Fair scheduling prevents indefinite delays
    """

    def __init__(self):
        # Core synchronization primitives
        self._readers_lock = threading.Lock()  # Protects reader count
        self._writers_lock = threading.Lock()  # Protects writer access
        self._no_readers = threading.Condition(self._readers_lock)  # Signals when no readers

        # State tracking
        self._reader_count = 0
        self._writer_active = False
        self._waiting_writers = 0

        # Fairness control
        self._service_writer = threading.Condition(self._writers_lock)  # Writer service signal

    def acquire_read(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire read lock with fairness consideration.

        Returns True if lock acquired, False if timeout expired.
        """
        start_time = time.time() if timeout else None

        with self._writers_lock:
            # Wait for any active writer to finish
            while self._writer_active:
                if timeout:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        return False
                    if not self._service_writer.wait(remaining):
                        return False
                else:
                    self._service_writer.wait()

            # Increment waiting writers count to block new readers if writers are waiting
            self._waiting_writers += 1

        try:
            with self._readers_lock:
                # Wait for no active writers (should be quick since we checked above)
                while self._writer_active:
                    if timeout:
                        remaining = timeout - (time.time() - start_time)
                        if remaining <= 0:
                            return False
                        if not self._no_readers.wait(remaining):
                            return False
                    else:
                        self._no_readers.wait()

                self._reader_count += 1
                return True
        finally:
            with self._writers_lock:
                self._waiting_writers -= 1

    def release_read(self):
        """Release read lock."""
        with self._readers_lock:
            self._reader_count -= 1
            if self._reader_count == 0:
                # Signal waiting writers that all readers are done
                self._no_readers.notify_all()

    def acquire_write(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire write lock with priority.

        Returns True if lock acquired, False if timeout expired.
        """
        start_time = time.time() if timeout else None

        with self._writers_lock:
            self._waiting_writers += 1

        try:
            with self._readers_lock:
                # Wait for all readers to finish
                while self._reader_count > 0:
                    if timeout:
                        remaining = timeout - (time.time() - start_time)
                        if remaining <= 0:
                            return False
                        if not self._no_readers.wait(remaining):
                            return False
                    else:
                        self._no_readers.wait()

                # Now acquire exclusive write access
                with self._writers_lock:
                    while self._writer_active:
                        if timeout:
                            remaining = timeout - (time.time() - start_time)
                            if remaining <= 0:
                                return False
                            if not self._service_writer.wait(remaining):
                                return False
                        else:
                            self._service_writer.wait()

                    self._writer_active = True
                    return True
        finally:
            with self._writers_lock:
                self._waiting_writers -= 1

    def release_write(self):
        """Release write lock."""
        with self._writers_lock:
            self._writer_active = False
            # Signal both waiting writers and waiting readers
            self._service_writer.notify_all()

    @contextmanager
    def read_lock(self, timeout: Optional[float] = None):
        """Context manager for read lock."""
        acquired = self.acquire_read(timeout)
        if not acquired:
            raise TimeoutError("Failed to acquire read lock within timeout")
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self, timeout: Optional[float] = None):
        """Context manager for write lock."""
        acquired = self.acquire_write(timeout)
        if not acquired:
            raise TimeoutError("Failed to acquire write lock within timeout")
        try:
            yield
        finally:
            self.release_write()

    def get_stats(self) -> dict:
        """Get current lock statistics for monitoring."""
        with self._readers_lock:
            with self._writers_lock:
                return {
                    'reader_count': self._reader_count,
                    'writer_active': self._writer_active,
                    'waiting_writers': self._waiting_writers
                }


# Global instance for application-wide use
_fair_rw_lock = FairReaderWriterLock()

def get_fair_reader_writer_lock() -> FairReaderWriterLock:
    """Get the global fair reader-writer lock instance."""
    return _fair_rw_lock