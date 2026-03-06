"""
Clock-Aware Time Operations for NTP Drift Monitoring

Provides centralized time functions that account for NTP clock drift
for all time-sensitive operations (tokens, OTP, sessions).
"""

import time
from datetime import datetime, timedelta, timezone

# Python 3.10 compatibility
UTC = timezone.utc
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# Import the global clock monitor
try:
    from scripts.monitoring.clock_skew_monitor import get_clock_monitor
    CLOCK_MONITOR_AVAILABLE = True
except ImportError:
    CLOCK_MONITOR_AVAILABLE = False
    logger.warning("Clock skew monitor not available - using standard time")


class ClockAwareTime:
    """Centralized clock-aware time operations."""
    
    # Configuration - override via environment
    DRIFT_TOLERANCE_SECONDS = 5  # Default 5s buffer for drift
    
    @staticmethod
    def get_current_time() -> datetime:
        """
        Get current time with clock awareness.
        
        Returns:
            datetime: Current UTC time, adjusted for known drift
        """
        if not CLOCK_MONITOR_AVAILABLE:
            return datetime.now(UTC)
        
        monitor = get_clock_monitor()
        current_timestamp = monitor.get_skew_resistant_time()
        return datetime.fromtimestamp(current_timestamp, tz=UTC)
    
    @staticmethod
    def get_expiry_with_drift_tolerance(ttl_seconds: float) -> datetime:
        """
        Calculate expiry time with drift tolerance buffer.
        
        Adds a safety margin to account for clock drift, ensuring tokens
        don't expire prematurely due to NTP synchronization issues.
        
        Args:
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            datetime: Expiry time with drift tolerance applied
        """
        if not CLOCK_MONITOR_AVAILABLE:
            return ClockAwareTime.get_current_time() + timedelta(seconds=ttl_seconds)
        
        monitor = get_clock_monitor()
        adjusted_ttl, tolerance = monitor.get_time_with_tolerance(ttl_seconds)
        
        current = ClockAwareTime.get_current_time()
        expiry = current + timedelta(seconds=adjusted_ttl)
        
        if tolerance > 0:
            logger.debug(f"Applied drift tolerance: {tolerance:.2f}s to TTL {ttl_seconds:.2f}s")
        
        return expiry
    
    @staticmethod
    def is_expired(expiry_time: datetime) -> bool:
        """
        Check if expiry time has passed with clock drift consideration.
        
        Accounts for potential clock drift when determining expiry.
        
        Args:
            expiry_time: The datetime when something expires
            
        Returns:
            bool: True if expired, False otherwise
        """
        if not CLOCK_MONITOR_AVAILABLE:
            return datetime.now(UTC) > expiry_time
        
        monitor = get_clock_monitor()
        current = monitor.get_skew_resistant_time()
        
        # Add drift tolerance buffer for grace period
        tolerance = ClockAwareTime.DRIFT_TOLERANCE_SECONDS
        current_with_tolerance = current + tolerance
        
        is_expired = current_with_tolerance > expiry_time.timestamp()
        return is_expired
    
    @staticmethod
    def get_clock_health() -> dict:
        """
        Get current clock synchronization health status.
        
        Returns:
            dict: {
                'synchronized': bool,
                'drift_seconds': float,
                'state': str,  # 'synchronized', 'drifting', 'unsynchronized'
                'ntp_available': bool
            }
        """
        if not CLOCK_MONITOR_AVAILABLE:
            return {
                'synchronized': True,
                'drift_seconds': 0,
                'state': 'unknown',
                'ntp_available': False
            }
        
        monitor = get_clock_monitor()
        metrics = monitor.get_clock_metrics()
        
        return {
            'synchronized': monitor.is_clock_synchronized(),
            'drift_seconds': metrics.ntp_offset,
            'state': metrics.state.value,
            'ntp_available': monitor._ntp_available
        }


def get_current_time() -> datetime:
    """Convenience function - get current time with clock awareness."""
    return ClockAwareTime.get_current_time()


def get_expiry_with_drift_tolerance(ttl_seconds: float) -> datetime:
    """Convenience function - get expiry with drift tolerance."""
    return ClockAwareTime.get_expiry_with_drift_tolerance(ttl_seconds)


def is_expired(expiry_time: datetime) -> bool:
    """Convenience function - check expiry with clock awareness."""
    return ClockAwareTime.is_expired(expiry_time)


def get_clock_health() -> dict:
    """Convenience function - get clock health status."""
    return ClockAwareTime.get_clock_health()
