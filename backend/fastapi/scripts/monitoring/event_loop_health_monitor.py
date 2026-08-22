#!/usr/bin/env python3
"""
Event Loop Health Monitor - Epoll Event Loop Exhaustion Prevention #1183

Monitors asyncio event loop health and prevents degradation from FD exhaustion.
Integrates with FD resource manager for comprehensive monitoring.
"""

import asyncio
import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from scripts.utilities.fd_resource_manager import FDResourceManager, EventLoopMonitor, FDType

logger = logging.getLogger(__name__)


class EventLoopState(Enum):
    """States of the event loop health."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DEGRADED = "degraded"


@dataclass
class LoopHealthMetrics:
    """Metrics for event loop health."""
    lag_time: float
    fd_count: int
    fd_usage_ratio: float
    pending_tasks: int
    timestamp: float


class EventLoopHealthMonitor:
    """
    Comprehensive event loop health monitor for FastAPI applications.

    Monitors event loop responsiveness, FD usage, and task backlog.
    Implements backpressure and recovery mechanisms.
    """

    def __init__(self,
                 fd_manager: Optional[FDResourceManager] = None,
                 lag_warning_threshold: float = 0.1,  # 100ms
                 lag_critical_threshold: float = 1.0,  # 1 second
                 fd_warning_threshold: float = 0.8,
                 fd_critical_threshold: float = 0.9,
                 max_pending_tasks: int = 1000,
                 recovery_interval: float = 60.0):
        """
        Initialize event loop health monitor.

        Args:
            fd_manager: FD resource manager instance
            lag_warning_threshold: Warning threshold for loop lag (seconds)
            lag_critical_threshold: Critical threshold for loop lag (seconds)
            fd_warning_threshold: Warning threshold for FD usage ratio
            fd_critical_threshold: Critical threshold for FD usage ratio
            max_pending_tasks: Maximum allowed pending tasks
            recovery_interval: How often to attempt recovery (seconds)
        """
        self.fd_manager = fd_manager
        self.lag_warning_threshold = lag_warning_threshold
        self.lag_critical_threshold = lag_critical_threshold
        self.fd_warning_threshold = fd_warning_threshold
        self.fd_critical_threshold = fd_critical_threshold
        self.max_pending_tasks = max_pending_tasks
        self.recovery_interval = recovery_interval

        # State tracking
        self._current_state = EventLoopState.HEALTHY
        self._last_recovery_attempt = 0.0
        self._consecutive_warnings = 0
        self._consecutive_critical = 0

        # Metrics history
        self._metrics_history: List[LoopHealthMetrics] = []
        self._max_history_size = 100

        # Callbacks
        self._state_change_callbacks: List[Callable] = []
        self._recovery_callbacks: List[Callable] = []

        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False

        # Statistics
        self._stats = {
            'total_checks': 0,
            'state_changes': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'lag_warnings': 0,
            'lag_critical': 0,
            'fd_warnings': 0,
            'fd_critical': 0,
            'task_backlog_warnings': 0
        }

    async def start_monitoring(self):
        """Start monitoring the event loop."""
        logger.info("Starting event loop health monitoring")
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring the event loop."""
        logger.info("Stopping event loop health monitoring")
        self._stop_monitoring = True
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_monitoring:
            try:
                await self._check_health()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")

            await asyncio.sleep(5.0)  # Check every 5 seconds

    async def _check_health(self):
        """Check overall event loop health."""
        self._stats['total_checks'] += 1

        # Measure loop lag
        lag_time = await self._measure_loop_lag()

        # Get FD metrics
        fd_count = self.fd_manager.get_current_fd_count()
        fd_usage_ratio = fd_count / self.fd_manager.max_fds

        # Get pending tasks
        pending_tasks = len(asyncio.all_tasks())

        # Create metrics
        metrics = LoopHealthMetrics(
            lag_time=lag_time,
            fd_count=fd_count,
            fd_usage_ratio=fd_usage_ratio,
            pending_tasks=pending_tasks,
            timestamp=time.time()
        )

        # Store metrics
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history.pop(0)

        # Determine new state
        new_state = self._determine_state(metrics)

        # Handle state changes
        if new_state != self._current_state:
            await self._handle_state_change(new_state, metrics)

        self._current_state = new_state

    async def _measure_loop_lag(self) -> float:
        """Measure event loop lag in seconds."""
        start_time = time.time()
        # Schedule a callback and measure delay
        future = asyncio.Future()

        def callback():
            future.set_result(time.time())

        asyncio.get_event_loop().call_soon(callback)
        end_time = await future
        return end_time - start_time

    def _determine_state(self, metrics: LoopHealthMetrics) -> EventLoopState:
        """Determine the current health state."""
        # Check for critical conditions
        if (metrics.lag_time >= self.lag_critical_threshold or
            metrics.fd_usage_ratio >= self.fd_critical_threshold or
            metrics.pending_tasks >= self.max_pending_tasks * 2):
            return EventLoopState.CRITICAL

        # Check for warning conditions
        if (metrics.lag_time >= self.lag_warning_threshold or
            metrics.fd_usage_ratio >= self.fd_warning_threshold or
            metrics.pending_tasks >= self.max_pending_tasks):
            return EventLoopState.WARNING

        # Check for degraded state (persistent warnings)
        if self._consecutive_warnings >= 3:
            return EventLoopState.DEGRADED

        return EventLoopState.HEALTHY

    async def _handle_state_change(self, new_state: EventLoopState, metrics: LoopHealthMetrics):
        """Handle state changes and trigger recovery if needed."""
        old_state = self._current_state
        self._stats['state_changes'] += 1

        logger.info(f"Event loop state change: {old_state.value} -> {new_state.value}")

        # Update consecutive counters
        if new_state == EventLoopState.WARNING:
            self._consecutive_warnings += 1
            self._consecutive_critical = 0
        elif new_state == EventLoopState.CRITICAL:
            self._consecutive_critical += 1
            self._consecutive_warnings = 0
        else:
            self._consecutive_warnings = 0
            self._consecutive_critical = 0

        # Trigger callbacks
        for callback in self._state_change_callbacks:
            try:
                await callback(new_state, old_state, metrics)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

        # Attempt recovery for critical/degraded states
        if new_state in (EventLoopState.CRITICAL, EventLoopState.DEGRADED):
            await self._attempt_recovery(metrics)

    async def _attempt_recovery(self, metrics: LoopHealthMetrics):
        """Attempt to recover from degraded/critical state."""
        current_time = time.time()
        if current_time - self._last_recovery_attempt < self.recovery_interval:
            return  # Too soon for another recovery attempt

        self._last_recovery_attempt = current_time
        self._stats['recovery_attempts'] += 1

        logger.warning("Attempting event loop recovery...")

        try:
            # Force garbage collection
            import gc
            gc.collect()

            # Force FD cleanup
            cleaned_fds = self.fd_manager.force_cleanup()
            if cleaned_fds > 0:
                logger.info(f"Cleaned up {cleaned_fds} leaked file descriptors")

            # Cancel some pending tasks if too many
            if metrics.pending_tasks > self.max_pending_tasks * 1.5:
                tasks_cancelled = await self._cancel_excess_tasks()
                logger.info(f"Cancelled {tasks_cancelled} excess pending tasks")

            # Trigger recovery callbacks
            for callback in self._recovery_callbacks:
                try:
                    await callback(metrics)
                except Exception as e:
                    logger.error(f"Error in recovery callback: {e}")

            self._stats['successful_recoveries'] += 1
            logger.info("Event loop recovery completed")

        except Exception as e:
            logger.error(f"Error during event loop recovery: {e}")

    async def _cancel_excess_tasks(self) -> int:
        """Cancel excess pending tasks to reduce load."""
        all_tasks = asyncio.all_tasks()
        current_task = asyncio.current_task()

        # Don't cancel the current task or monitoring task
        cancellable_tasks = [
            task for task in all_tasks
            if task != current_task and task != self._monitor_task
        ]

        # Sort by creation time (oldest first)
        cancellable_tasks.sort(key=lambda t: t.get_coro().cr_frame.f_lineno if t.get_coro().cr_frame else 0)

        # Cancel oldest tasks first, keeping some buffer
        max_to_cancel = len(cancellable_tasks) - (self.max_pending_tasks // 2)
        max_to_cancel = max(0, min(max_to_cancel, 50))  # Limit to 50 at a time

        cancelled = 0
        for task in cancellable_tasks[:max_to_cancel]:
            if not task.done():
                task.cancel()
                cancelled += 1

        return cancelled

    def add_state_change_callback(self, callback: Callable):
        """Add a callback for state changes."""
        self._state_change_callbacks.append(callback)

    def add_recovery_callback(self, callback: Callable):
        """Add a callback for recovery attempts."""
        self._recovery_callbacks.append(callback)

    def get_current_state(self) -> EventLoopState:
        """Get the current event loop state."""
        return self._current_state

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            **self._stats,
            'current_state': self._current_state.value,
            'consecutive_warnings': self._consecutive_warnings,
            'consecutive_critical': self._consecutive_critical,
            'metrics_history_size': len(self._metrics_history)
        }

    def get_recent_metrics(self, count: int = 10) -> List[LoopHealthMetrics]:
        """Get recent health metrics."""
        return self._metrics_history[-count:] if self._metrics_history else []


# FastAPI integration
class FastAPIEventLoopMonitor:
    """
    FastAPI-specific event loop monitor with middleware integration.
    """

    def __init__(self, app=None):
        self.app = app
        self.fd_manager = FDResourceManager()
        self.health_monitor = EventLoopHealthMonitor(self.fd_manager)

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with FastAPI app."""
        self.app = app

        # Add startup/shutdown handlers
        app.add_event_handler("startup", self._on_startup)
        app.add_event_handler("shutdown", self._on_shutdown)

        # Add middleware for request tracking
        app.middleware("http")(self._track_request_middleware)

    async def _on_startup(self):
        """Handle application startup."""
        await self.health_monitor.start_monitoring()
        logger.info("FastAPI event loop monitoring started")

    async def _on_shutdown(self):
        """Handle application shutdown."""
        await self.health_monitor.stop_monitoring()
        self.fd_manager.shutdown()
        logger.info("FastAPI event loop monitoring stopped")

    async def _track_request_middleware(self, request, call_next):
        """Middleware to track request FDs and monitor health."""
        # Track the socket FD for this request
        if hasattr(request, 'client') and request.client:
            # This would need to be adapted based on FastAPI version
            # For now, just monitor overall FD usage
            pass

        # Check if we should reject the request due to high load
        if self.health_monitor.get_current_state() == EventLoopState.CRITICAL:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        # Process the request
        response = await call_next(request)
        return response

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status for health checks."""
        state = self.health_monitor.get_current_state()
        stats = self.health_monitor.get_stats()
        fd_stats = self.fd_manager.get_stats()

        return {
            'event_loop_state': state.value,
            'event_loop_stats': stats,
            'fd_stats': fd_stats,
            'healthy': state == EventLoopState.HEALTHY,
            'degraded': state in (EventLoopState.WARNING, EventLoopState.DEGRADED),
            'critical': state == EventLoopState.CRITICAL
        }


# Global instance for easy access
_monitor_instance = None

def get_event_loop_monitor() -> Optional[EventLoopHealthMonitor]:
    """Get the global event loop monitor instance."""
    return _monitor_instance

def init_fastapi_monitor(app) -> FastAPIEventLoopMonitor:
    """Initialize FastAPI event loop monitoring."""
    global _monitor_instance
    monitor = FastAPIEventLoopMonitor(app)
    monitor.init_app(app)
    _monitor_instance = monitor.health_monitor
    return monitor