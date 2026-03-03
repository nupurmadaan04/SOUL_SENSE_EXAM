"""
Worker Management System for #1219: Leak in Long-Lived Async Workers

Provides memory-safe management of long-lived async workers with:
- Automatic cleanup hooks
- Weak reference management
- Periodic health checks and restarts
- Memory usage monitoring
"""

import asyncio
import gc
import logging
import psutil
import tracemalloc
import weakref
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class WorkerHealthMonitor:
    """Monitors worker health and memory usage."""

    def __init__(self, max_memory_mb: int = 500, check_interval: int = 300):
        self.max_memory_mb = max_memory_mb
        self.check_interval = check_interval
        self.snapshots: Dict[str, tracemalloc.Snapshot] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

    async def start_monitoring(self):
        """Start periodic health monitoring."""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Worker health monitoring started")

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Worker health monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                await self._check_memory_usage()
                await self._check_for_leaks()
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_memory_usage(self):
        """Check current memory usage."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.max_memory_mb:
            logger.warning(".1f")
            # Trigger garbage collection
            gc.collect()
            # Check again after GC
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                logger.error(".1f")
                # Could trigger worker restart here

    async def _check_for_leaks(self):
        """Check for memory leaks using tracemalloc."""
        if not tracemalloc.is_tracing():
            return

        current_snapshot = tracemalloc.take_snapshot()
        total_size = sum(stat.size for stat in current_snapshot.statistics('filename'))

        # Compare with previous snapshots to detect growth
        if 'initial' not in self.snapshots:
            self.snapshots['initial'] = current_snapshot
            return

        initial_stats = self.snapshots['initial'].statistics('filename')
        current_stats = current_snapshot.statistics('filename')

        # Check for significant memory growth
        growth_threshold = 50 * 1024 * 1024  # 50MB
        if total_size > growth_threshold:
            logger.warning(".1f")
            # Could trigger cleanup or restart


class WeakReferenceCache:
    """Cache that uses weak references to prevent memory leaks."""

    def __init__(self):
        self._cache: Dict[str, weakref.ReferenceType] = {}
        self._callbacks: Dict[str, Set[Callable]] = {}

    def set(self, key: str, value: Any, callback: Optional[Callable] = None):
        """Store a weak reference to the value."""
        def cleanup(ref):
            self._cache.pop(key, None)
            if callback:
                try:
                    callback(key)
                except Exception as e:
                    logger.error(f"Cleanup callback error for {key}: {e}")

        self._cache[key] = weakref.ref(value, cleanup)
        if callback:
            self._callbacks[key] = {callback}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value if still alive."""
        ref = self._cache.get(key)
        if ref is not None:
            value = ref()
            if value is None:
                # Reference was garbage collected
                self._cache.pop(key, None)
                return None
            return value
        return None

    def delete(self, key: str):
        """Remove item from cache."""
        self._cache.pop(key, None)
        self._callbacks.pop(key, None)

    def clear(self):
        """Clear all cached items."""
        self._cache.clear()
        self._callbacks.clear()

    def size(self) -> int:
        """Get number of live references."""
        # Clean up dead references
        dead_keys = [k for k, ref in self._cache.items() if ref() is None]
        for key in dead_keys:
            self._cache.pop(key, None)
            self._callbacks.pop(key, None)
        return len(self._cache)


class AsyncWorkerManager:
    """Manages long-lived async workers with memory safety."""

    def __init__(self):
        self.workers: Dict[str, asyncio.Task] = {}
        self.worker_factories: Dict[str, Callable] = {}
        self.restart_intervals: Dict[str, int] = {}  # seconds
        self.last_restart: Dict[str, datetime] = {}
        self.health_monitor = WorkerHealthMonitor()
        self.weak_cache = WeakReferenceCache()
        self._cleanup_hooks: List[Callable] = []
        self._shutdown = False

    async def start(self):
        """Start the worker manager."""
        await self.health_monitor.start_monitoring()
        logger.info("AsyncWorkerManager started")

    async def shutdown(self, drain_timeout: int = 10):
        """Shutdown all workers and cleanup.

        Graceful shutdown procedure:
        1. Flip shutdown flag so worker loops stop scheduling new work.
        2. Stop health monitoring.
        3. Wait up to `drain_timeout` seconds for workers to finish naturally.
        4. Cancel any remaining workers and await their cancellation.
        5. Run cleanup hooks and clear caches.

        `drain_timeout` can be tuned for deployments to allow in-flight work to finish.
        """
        self._shutdown = True
        logger.info("Shutting down AsyncWorkerManager (graceful)...")

        # Stop health monitoring first
        await self.health_monitor.stop_monitoring()

        # If no workers, proceed to cleanup
        if not self.workers:
            logger.info("No workers to shut down")
        else:
            # Wait up to drain_timeout seconds for workers to finish
            tasks = list(self.workers.values())
            logger.info(f"Waiting up to {drain_timeout}s for {len(tasks)} workers to finish")
            try:
                done, pending = await asyncio.wait(tasks, timeout=drain_timeout)
            except Exception as e:
                logger.error(f"Error while waiting for workers to finish: {e}")
                pending = tasks

            # Cancel any remaining pending workers
            if pending:
                for t in pending:
                    try:
                        logger.info(f"Cancelling worker task: {t.get_name() if hasattr(t, 'get_name') else t}")
                        t.cancel()
                    except Exception:
                        t.cancel()

                # Await cancellation completion
                await asyncio.gather(*pending, return_exceptions=True)

        # Run cleanup hooks
        for hook in self._cleanup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Cleanup hook error: {e}")

        # Clear weak cache
        self.weak_cache.clear()

        logger.info("AsyncWorkerManager shutdown complete")

    def register_worker(self, name: str, factory: Callable, restart_interval: int = 3600):
        """Register a worker factory function."""
        self.worker_factories[name] = factory
        self.restart_intervals[name] = restart_interval
        logger.info(f"Registered worker: {name} (restart every {restart_interval}s)")

    def add_cleanup_hook(self, hook: Callable):
        """Add a cleanup hook to run on shutdown."""
        self._cleanup_hooks.append(hook)

    async def start_worker(self, name: str):
        """Start a specific worker."""
        if name not in self.worker_factories:
            raise ValueError(f"Worker {name} not registered")

        if name in self.workers and not self.workers[name].done():
            logger.warning(f"Worker {name} is already running")
            return

        factory = self.worker_factories[name]
        task = asyncio.create_task(self._run_worker_with_restart(name, factory))
        self.workers[name] = task
        self.last_restart[name] = datetime.now()
        logger.info(f"Started worker: {name}")

    async def stop_worker(self, name: str):
        """Stop a specific worker."""
        if name in self.workers:
            task = self.workers[name]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.workers[name]
            logger.info(f"Stopped worker: {name}")

    async def _run_worker_with_restart(self, name: str, factory: Callable):
        """Run worker with automatic restart logic."""
        while not self._shutdown:
            try:
                logger.info(f"Starting worker execution: {name}")
                await factory()

            except asyncio.CancelledError:
                logger.info(f"Worker {name} cancelled")
                break

            except Exception as e:
                logger.error(f"Worker {name} crashed: {e}", exc_info=True)

                # Check if we should restart
                restart_interval = self.restart_intervals.get(name, 3600)
                last_restart = self.last_restart.get(name)

                if last_restart and (datetime.now() - last_restart).seconds < restart_interval:
                    logger.warning(f"Worker {name} crashed too soon, waiting before restart")
                    await asyncio.sleep(restart_interval)

                if not self._shutdown:
                    logger.info(f"Restarting worker: {name}")
                    self.last_restart[name] = datetime.now()
                    continue

            # If we get here, worker completed normally - check restart policy
            if not self._shutdown:
                restart_interval = self.restart_intervals.get(name, 3600)
                logger.info(f"Worker {name} completed, restarting in {restart_interval}s")
                await asyncio.sleep(restart_interval)

    def get_worker_status(self) -> Dict[str, Dict]:
        """Get status of all workers."""
        status = {}
        for name in self.worker_factories:
            task = self.workers.get(name)
            if task:
                status[name] = {
                    'running': not task.done(),
                    'last_restart': self.last_restart.get(name),
                    'exception': str(task.exception()) if task.done() and task.exception() else None
                }
            else:
                status[name] = {'running': False, 'last_restart': None, 'exception': None}
        return status

    def cache_with_weak_ref(self, key: str, value: Any, cleanup_callback: Optional[Callable] = None):
        """Cache an object using weak references."""
        self.weak_cache.set(key, value, cleanup_callback)

    def get_cached(self, key: str) -> Optional[Any]:
        """Retrieve cached object."""
        return self.weak_cache.get(key)

    def clear_cache(self):
        """Clear all cached objects."""
        self.weak_cache.clear()


# Global worker manager instance
worker_manager = AsyncWorkerManager()


@asynccontextmanager
async def managed_worker_context():
    """Context manager for worker lifecycle."""
    await worker_manager.start()
    try:
        yield worker_manager
    finally:
        await worker_manager.shutdown()


def periodic_cleanup_hook():
    """Periodic cleanup hook to run garbage collection."""
    gc.collect()
    logger.debug("Periodic garbage collection completed")


# Register the cleanup hook
worker_manager.add_cleanup_hook(periodic_cleanup_hook)