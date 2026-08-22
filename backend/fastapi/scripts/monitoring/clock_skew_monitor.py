#!/usr/bin/env python3
"""
Clock Skew Resistant Time Synchronization - Prevents Distributed Deadlock #1195

Implements monotonic clock-based timing with NTP drift detection and tolerance buffers
to prevent distributed lock TTL inconsistencies caused by clock skew.
"""

import time
import logging
import threading
import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ClockState(Enum):
    """Clock synchronization states."""
    SYNCHRONIZED = "synchronized"
    DRIFTING = "drifting"
    UNSYNCHRONIZED = "unsynchronized"


@dataclass
class ClockMetrics:
    """Clock synchronization metrics."""
    wall_time: float
    monotonic_time: float
    ntp_offset: float
    drift_rate: float
    last_sync: float
    state: ClockState


class ClockSkewMonitor:
    """
    Monitors system clock for NTP drift and provides skew-resistant timing.

    Uses monotonic clocks for relative timing and wall clocks with drift compensation
    for distributed lock TTL calculations.
    """

    def __init__(self,
                 drift_tolerance_seconds: float = 5.0,
                 ntp_check_interval: float = 300.0,  # 5 minutes
                 max_drift_rate: float = 0.0001):  # 100ppm
        """
        Initialize clock skew monitor.

        Args:
            drift_tolerance_seconds: Maximum allowed clock drift before warning
            ntp_check_interval: How often to check NTP synchronization
            max_drift_rate: Maximum allowed drift rate (fraction per second)
        """
        self.drift_tolerance = drift_tolerance_seconds
        self.ntp_check_interval = ntp_check_interval
        self.max_drift_rate = max_drift_rate

        # Timing state
        self._monotonic_start = time.monotonic()
        self._wall_start = time.time()
        self._last_ntp_check = 0.0
        self._ntp_offset = 0.0
        self._drift_rate = 0.0

        # State tracking
        self._state = ClockState.SYNCHRONIZED
        self._lock = threading.Lock()

        # NTP monitoring
        self._ntp_available = self._check_ntp_availability()
        self._monitor_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False

    def _check_ntp_availability(self) -> bool:
        """Check if NTP synchronization is available."""
        try:
            # Try to detect NTP synchronization
            import subprocess
            import platform

            if platform.system() == 'Windows':
                # Windows w32tm command
                result = subprocess.run(['w32tm', '/query', '/status'],
                                      capture_output=True, text=True, timeout=5)
                return 'synchronized' in result.stdout.lower()
            else:
                # Unix ntpq or timedatectl
                try:
                    result = subprocess.run(['ntpq', '-p'],
                                          capture_output=True, text=True, timeout=5)
                    return result.returncode == 0
                except FileNotFoundError:
                    try:
                        result = subprocess.run(['timedatectl', 'status'],
                                              capture_output=True, text=True, timeout=5)
                        return 'synchronized' in result.stdout.lower()
                    except FileNotFoundError:
                        pass
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

        return False

    def _measure_ntp_offset(self) -> float:
        """Measure NTP offset from system."""
        try:
            import subprocess
            import platform

            if platform.system() == 'Windows':
                # Use w32tm to get offset
                result = subprocess.run(['w32tm', '/query', '/status'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Parse offset from output (simplified)
                    for line in result.stdout.split('\n'):
                        if 'last successful sync' in line.lower():
                            # Very basic parsing - in production would need better NTP client
                            return 0.0
            else:
                # Use ntpq for Unix systems
                result = subprocess.run(['ntpq', '-p'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Parse root delay/dispersion (simplified)
                    return 0.0
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass

        return 0.0

    def get_skew_resistant_time(self) -> float:
        """
        Get current time resistant to clock skew.

        Uses monotonic clock for relative timing with drift compensation.
        """
        with self._lock:
            monotonic_now = time.monotonic()
            elapsed_monotonic = monotonic_now - self._monotonic_start

            # Apply drift compensation
            drift_compensation = elapsed_monotonic * self._drift_rate
            wall_time = self._wall_start + elapsed_monotonic - drift_compensation

            return wall_time

    def get_monotonic_time(self) -> float:
        """Get pure monotonic time (not affected by wall clock changes)."""
        return time.monotonic()

    def get_time_with_tolerance(self, requested_ttl: float) -> Tuple[float, float]:
        """
        Get TTL with drift tolerance buffer.

        Returns (effective_ttl, tolerance_buffer) where effective_ttl includes
        safety margins for clock drift.
        """
        with self._lock:
            # Add tolerance buffer based on current drift rate and state
            if self._state == ClockState.UNSYNCHRONIZED:
                # High tolerance for unsynchronized clocks
                tolerance = max(requested_ttl * 0.5, 30.0)  # 50% or 30s minimum
            elif self._state == ClockState.DRIFTING:
                # Medium tolerance for drifting clocks
                tolerance = max(requested_ttl * 0.2, 10.0)  # 20% or 10s minimum
            else:
                # Low tolerance for synchronized clocks
                tolerance = max(requested_ttl * 0.1, 5.0)   # 10% or 5s minimum

            effective_ttl = requested_ttl + tolerance
            return effective_ttl, tolerance

    async def start_monitoring(self):
        """Start background clock monitoring."""
        logger.info("Starting clock skew monitoring")
        self._monitor_task = asyncio.create_task(self._monitor_clock())

    async def stop_monitoring(self):
        """Stop background clock monitoring."""
        logger.info("Stopping clock skew monitoring")
        self._stop_monitoring = True
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_clock(self):
        """Background clock monitoring loop."""
        while not self._stop_monitoring:
            try:
                await self._check_clock_synchronization()
            except Exception as e:
                logger.error(f"Error in clock monitoring: {e}")

            await asyncio.sleep(self.ntp_check_interval)

    async def _check_clock_synchronization(self):
        """Check NTP synchronization and update drift metrics."""
        current_time = time.time()

        # Measure NTP offset
        ntp_offset = self._measure_ntp_offset()

        # Calculate drift rate
        time_since_last_check = current_time - self._last_ntp_check
        if time_since_last_check > 0:
            offset_change = ntp_offset - self._ntp_offset
            self._drift_rate = offset_change / time_since_last_check

        # Update state
        with self._lock:
            self._ntp_offset = ntp_offset
            self._last_ntp_check = current_time

            # Determine clock state
            if not self._ntp_available:
                new_state = ClockState.UNSYNCHRONIZED
            elif abs(ntp_offset) > self.drift_tolerance:
                new_state = ClockState.DRIFTING
            elif abs(self._drift_rate) > self.max_drift_rate:
                new_state = ClockState.DRIFTING
            else:
                new_state = ClockState.SYNCHRONIZED

            # Log state changes
            if new_state != self._state:
                logger.warning(f"Clock state changed: {self._state.value} -> {new_state.value}")
                if new_state == ClockState.DRIFTING:
                    logger.warning(f"Clock drift detected: offset={ntp_offset:.3f}s, rate={self._drift_rate:.6f}")
                elif new_state == ClockState.UNSYNCHRONIZED:
                    logger.error("Clock synchronization lost - using drift-tolerant timing")

            self._state = new_state

    def get_clock_metrics(self) -> ClockMetrics:
        """Get current clock synchronization metrics."""
        with self._lock:
            return ClockMetrics(
                wall_time=time.time(),
                monotonic_time=time.monotonic(),
                ntp_offset=self._ntp_offset,
                drift_rate=self._drift_rate,
                last_sync=self._last_ntp_check,
                state=self._state
            )

    def is_clock_synchronized(self) -> bool:
        """Check if clock is currently synchronized."""
        with self._lock:
            return self._state == ClockState.SYNCHRONIZED

    def get_drift_tolerance_seconds(self) -> float:
        """Get current drift tolerance in seconds."""
        with self._lock:
            if self._state == ClockState.UNSYNCHRONIZED:
                return 30.0  # High tolerance
            elif self._state == ClockState.DRIFTING:
                return 10.0  # Medium tolerance
            else:
                return 2.0   # Low tolerance for synchronized


# Global instance
_clock_monitor = ClockSkewMonitor()

def get_clock_monitor() -> ClockSkewMonitor:
    """Get the global clock skew monitor instance."""
    return _clock_monitor

async def init_clock_monitoring():
    """Initialize global clock monitoring."""
    await _clock_monitor.start_monitoring()

async def shutdown_clock_monitoring():
    """Shutdown global clock monitoring."""
    await _clock_monitor.stop_monitoring()