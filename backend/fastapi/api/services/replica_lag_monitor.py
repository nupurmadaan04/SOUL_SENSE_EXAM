"""
Replica Lag Monitor Service

Monitors replication lag between primary and read-replica databases.
Routes read queries to primary when lag exceeds acceptable threshold.

Key Features:
- Periodic lag checking with configurable intervals
- Cached lag measurements to avoid query overhead
- Fallback to primary on replica failures
- Support for PostgreSQL and MySQL
- Detailed observability and metrics
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings_instance

log = logging.getLogger(__name__)
settings = get_settings_instance()


class ReplicaLagMonitor:
    """
    Monitors replication lag and determines if replica is healthy for reads.
    
    Attributes:
        _last_check_time: Timestamp of last lag check
        _last_lag_ms: Last measured lag in milliseconds
        _replica_healthy: Whether replica is within lag threshold
        _check_in_progress: Lock to prevent concurrent checks
        _error_count: Count of consecutive errors
    """
    
    def __init__(
        self,
        replica_engine: AsyncEngine,
        primary_engine: Optional[AsyncEngine] = None,
        lag_threshold_ms: int = 5000,
        check_interval_seconds: int = 10,
        cache_ttl_seconds: int = 5,
        timeout_seconds: float = 2.0,
        fallback_on_error: bool = True,
    ):
        """
        Initialize the replica lag monitor.
        
        Args:
            replica_engine: AsyncEngine for replica database
            primary_engine: Optional AsyncEngine for primary (needed for some lag checks)
            lag_threshold_ms: Maximum acceptable lag in milliseconds
            check_interval_seconds: How often to check lag
            cache_ttl_seconds: How long to cache lag measurements
            timeout_seconds: Query timeout for lag checks
            fallback_on_error: Whether to mark replica unhealthy on check errors
        """
        self.replica_engine = replica_engine
        self.primary_engine = primary_engine
        self.lag_threshold_ms = lag_threshold_ms
        self.check_interval_seconds = check_interval_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self.fallback_on_error = fallback_on_error
        
        # State tracking
        self._last_check_time: Optional[float] = None
        self._last_lag_ms: Optional[float] = None
        self._replica_healthy: bool = True
        self._check_lock = asyncio.Lock()
        self._error_count: int = 0
        self._max_consecutive_errors = 3
        self._background_task: Optional[asyncio.Task] = None
        
        log.info(
            f"ReplicaLagMonitor initialized: "
            f"threshold={lag_threshold_ms}ms, "
            f"interval={check_interval_seconds}s, "
            f"cache_ttl={cache_ttl_seconds}s"
        )
    
    async def _check_postgresql_lag(self, session: AsyncSession) -> Optional[float]:
        """
        Check PostgreSQL replication lag using pg_stat_replication.
        
        Returns:
            Lag in milliseconds, or None if unavailable
        """
        try:
            # Query for replication lag from replica's perspective
            # This queries pg_stat_replication or pg_last_wal_receive_lsn
            query = text("""
                SELECT CASE 
                    WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() 
                    THEN 0
                    ELSE EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000
                END AS lag_ms
            """)
            
            result = await session.execute(query)
            row = result.fetchone()
            
            if row and row[0] is not None:
                lag_ms = float(row[0])
                log.debug(f"PostgreSQL replica lag: {lag_ms:.2f}ms")
                return lag_ms
            
            log.warning("Unable to determine PostgreSQL replica lag")
            return None
            
        except SQLAlchemyError as e:
            log.error(f"Error checking PostgreSQL replica lag: {e}")
            return None
    
    async def _check_mysql_lag(self, session: AsyncSession) -> Optional[float]:
        """
        Check MySQL replication lag using SHOW SLAVE STATUS.
        
        Returns:
            Lag in milliseconds, or None if unavailable
        """
        try:
            # MySQL/MariaDB replication lag
            query = text("SHOW SLAVE STATUS")
            result = await session.execute(query)
            row = result.fetchone()
            
            if row:
                # Seconds_Behind_Master is typically at index 32
                # Convert to dict for safer access
                columns = result.keys()
                status_dict = dict(zip(columns, row))
                
                seconds_behind = status_dict.get('Seconds_Behind_Master')
                if seconds_behind is not None:
                    lag_ms = float(seconds_behind) * 1000
                    log.debug(f"MySQL replica lag: {lag_ms:.2f}ms")
                    return lag_ms
            
            log.warning("Unable to determine MySQL replica lag")
            return None
            
        except SQLAlchemyError as e:
            log.error(f"Error checking MySQL replica lag: {e}")
            return None
    
    async def _check_sqlite_lag(self, session: AsyncSession) -> Optional[float]:
        """
        SQLite doesn't have native replication, so always return 0.
        
        Returns:
            Always 0 (no lag concept for SQLite)
        """
        log.debug("SQLite detected - no replication lag concept, returning 0")
        return 0.0
    
    async def check_lag(self) -> Optional[float]:
        """
        Check current replication lag.
        
        Returns:
            Lag in milliseconds, or None if check failed
        """
        async with self._check_lock:
            try:
                # Use timeout for the lag check query
                async with asyncio.timeout(self.timeout_seconds):
                    async with self.replica_engine.connect() as conn:
                        async with conn.begin():
                            # Determine database type and use appropriate check
                            db_type = settings.database_type.lower()
                            
                            if "postgres" in db_type:
                                lag_ms = await self._check_postgresql_lag(conn)
                            elif "mysql" in db_type or "mariadb" in db_type:
                                lag_ms = await self._check_mysql_lag(conn)
                            elif "sqlite" in db_type:
                                lag_ms = await self._check_sqlite_lag(conn)
                            else:
                                log.warning(f"Unknown database type: {db_type}, assuming no lag")
                                lag_ms = 0.0
                            
                            if lag_ms is not None:
                                # Update state
                                self._last_lag_ms = lag_ms
                                self._last_check_time = time.time()
                                self._replica_healthy = lag_ms <= self.lag_threshold_ms
                                self._error_count = 0
                                
                                # Log warnings if lag is high
                                if lag_ms > self.lag_threshold_ms:
                                    log.warning(
                                        f"Replica lag ({lag_ms:.2f}ms) exceeds threshold "
                                        f"({self.lag_threshold_ms}ms) - routing reads to primary"
                                    )
                                
                                return lag_ms
                            
                            return None
                            
            except asyncio.TimeoutError:
                log.error(f"Replica lag check timed out after {self.timeout_seconds}s")
                self._error_count += 1
                if self._error_count >= self._max_consecutive_errors and self.fallback_on_error:
                    self._replica_healthy = False
                    log.error("Too many consecutive lag check failures - marking replica unhealthy")
                return None
                
            except Exception as e:
                log.error(f"Unexpected error checking replica lag: {e}")
                self._error_count += 1
                if self._error_count >= self._max_consecutive_errors and self.fallback_on_error:
                    self._replica_healthy = False
                    log.error("Too many consecutive lag check failures - marking replica unhealthy")
                return None
    
    def is_replica_healthy(self) -> bool:
        """
        Check if replica is healthy for reads based on cached state.
        
        Returns:
            True if replica lag is acceptable, False otherwise
        """
        # If lag detection is disabled, always return healthy
        if not settings.enable_replica_lag_detection:
            return True
        
        # If never checked, be conservative and check now
        if self._last_check_time is None:
            log.debug("No cached lag data - assuming replica unhealthy until first check")
            return False
        
        # Check if cache is still valid
        cache_age = time.time() - self._last_check_time
        if cache_age > self.cache_ttl_seconds:
            log.debug(
                f"Lag cache expired ({cache_age:.1f}s > {self.cache_ttl_seconds}s) "
                f"- using last known state: {self._replica_healthy}"
            )
        
        return self._replica_healthy
    
    async def get_lag_metrics(self) -> Dict[str, Any]:
        """
        Get current lag monitoring metrics for observability.
        
        Returns:
            Dictionary with lag metrics
        """
        return {
            "last_lag_ms": self._last_lag_ms,
            "last_check_time": datetime.fromtimestamp(self._last_check_time).isoformat() if self._last_check_time else None,
            "cache_age_seconds": time.time() - self._last_check_time if self._last_check_time else None,
            "replica_healthy": self._replica_healthy,
            "error_count": self._error_count,
            "threshold_ms": self.lag_threshold_ms,
            "check_interval_seconds": self.check_interval_seconds,
        }
    
    async def start_background_monitoring(self):
        """
        Start background task to periodically check replica lag.
        """
        if self._background_task is not None:
            log.warning("Background monitoring already running")
            return
        
        async def monitor_loop():
            log.info("Starting background replica lag monitoring")
            while True:
                try:
                    await self.check_lag()
                    await asyncio.sleep(self.check_interval_seconds)
                except asyncio.CancelledError:
                    log.info("Background replica lag monitoring cancelled")
                    break
                except Exception as e:
                    log.error(f"Error in background lag monitoring: {e}")
                    await asyncio.sleep(self.check_interval_seconds)
        
        self._background_task = asyncio.create_task(monitor_loop())
        log.info("Background replica lag monitoring started")
    
    async def stop_background_monitoring(self):
        """
        Stop background monitoring task.
        """
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
            log.info("Background replica lag monitoring stopped")


# Global instance
_lag_monitor: Optional[ReplicaLagMonitor] = None


def init_lag_monitor(
    replica_engine: AsyncEngine,
    primary_engine: Optional[AsyncEngine] = None
) -> ReplicaLagMonitor:
    """
    Initialize the global replica lag monitor.
    
    Args:
        replica_engine: AsyncEngine for replica database
        primary_engine: Optional AsyncEngine for primary database
        
    Returns:
        Initialized ReplicaLagMonitor instance
    """
    global _lag_monitor
    
    if _lag_monitor is not None:
        log.warning("Replica lag monitor already initialized")
        return _lag_monitor
    
    _lag_monitor = ReplicaLagMonitor(
        replica_engine=replica_engine,
        primary_engine=primary_engine,
        lag_threshold_ms=settings.replica_lag_threshold_ms,
        check_interval_seconds=settings.replica_lag_check_interval_seconds,
        cache_ttl_seconds=settings.replica_lag_cache_ttl_seconds,
        timeout_seconds=settings.replica_lag_timeout_seconds,
        fallback_on_error=settings.replica_lag_fallback_on_error,
    )
    
    return _lag_monitor


def get_lag_monitor() -> Optional[ReplicaLagMonitor]:
    """
    Get the global replica lag monitor instance.
    
    Returns:
        ReplicaLagMonitor instance if initialized, None otherwise
    """
    return _lag_monitor
