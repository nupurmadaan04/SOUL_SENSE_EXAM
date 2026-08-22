"""
Database Connection Manager for TIME_WAIT Socket Exhaustion Prevention.

Implements connection pooling and reuse to prevent TCP TIME_WAIT socket exhaustion
from rapid reconnections. Uses persistent connections with proper lifecycle management.
Integrates with FD resource manager to prevent epoll event loop exhaustion.
"""

import sqlite3
import threading
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import os
from scripts.utilities.poison_resistant_lock import PoisonResistantRLock, register_lock

# Import FD resource manager for tracking database file descriptors
try:
    from scripts.utilities.fd_resource_manager import get_fd_manager, FDType
    _fd_manager_available = True
except ImportError:
    _fd_manager_available = False
    logger.warning("FD resource manager not available, FD tracking disabled")

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Thread-safe SQLite connection pool to prevent TIME_WAIT socket exhaustion.

    Features:
    - Connection reuse to minimize new TCP connections
    - Automatic connection health checking
    - Configurable pool size and timeouts
    - Thread-safe operations
    - Graceful cleanup on application exit
    """

    def __init__(self, db_path: str, max_connections: int = 5, timeout: float = 30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool: List[sqlite3.Connection] = []
        self._lock = PoisonResistantRLock()
        self._closed = False

        # Register lock for monitoring
        register_lock(self._lock)

        # Connection health check
        self._last_health_check = time.time()
        self._health_check_interval = 300  # 5 minutes

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            isolation_level=None,  # Enable autocommit mode to prevent locks
            check_same_thread=False  # Allow multi-threaded access
        )

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=1000")  # 1MB cache
        conn.execute("PRAGMA temp_store=MEMORY")

        # Track the database file descriptor if FD manager is available
        if _fd_manager_available:
            try:
                # Get the file descriptor for the database file
                # Note: SQLite connections don't directly expose FDs, but we can track the file
                fd_manager = get_fd_manager()
                # Track the database file itself (not the connection FD)
                if os.path.exists(self.db_path):
                    db_fd = os.open(self.db_path, os.O_RDONLY)
                    fd_manager.register_fd(
                        db_fd,
                        FDType.FILE,
                        f"db_connection_pool_{id(self)}",
                        db_path=self.db_path,
                        connection_type="sqlite"
                    )
                    # Store FD in connection for cleanup
                    conn._tracked_fd = db_fd
                    os.close(db_fd)  # Close our reference, SQLite keeps its own
            except Exception as e:
                logger.debug(f"Could not track database FD: {e}")

        return conn

    def _is_connection_healthy(self, conn: sqlite3.Connection) -> bool:
        """Check if a connection is still healthy."""
        try:
            # Simple health check query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except sqlite3.Error:
            return False

    def _health_check(self):
        """Perform health check on all connections in the pool."""
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return

        with self._lock:
            healthy_connections = []
            for conn in self._pool:
                if self._is_connection_healthy(conn):
                    healthy_connections.append(conn)
                else:
                    try:
                        conn.close()
                    except:
                        pass

            self._pool = healthy_connections
            self._last_health_check = current_time

            logger.debug(f"Health check completed. Pool size: {len(self._pool)}")

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        self._health_check()

        with self._lock:
            # Try to reuse an existing connection
            if self._pool:
                conn = self._pool.pop()
                if self._is_connection_healthy(conn):
                    return conn
                else:
                    try:
                        conn.close()
                    except:
                        pass

            # Create new connection if pool is empty or unhealthy
            if len(self._pool) < self.max_connections:
                try:
                    return self._create_connection()
                except sqlite3.Error as e:
                    logger.error(f"Failed to create database connection: {e}")
                    raise

            # Pool is full, wait for a connection to become available
            # For now, create a new connection (could be improved with a queue)
            logger.warning("Connection pool full, creating additional connection")
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        if self._closed:
            try:
                # Unregister FD if tracked
                if _fd_manager_available and hasattr(conn, '_tracked_fd'):
                    try:
                        get_fd_manager().unregister_fd(conn._tracked_fd)
                    except Exception as e:
                        logger.debug(f"Could not unregister FD: {e}")
                conn.close()
            except:
                pass
            return

        with self._lock:
            if len(self._pool) < self.max_connections and self._is_connection_healthy(conn):
                self._pool.append(conn)
            else:
                try:
                    # Unregister FD if tracked
                    if _fd_manager_available and hasattr(conn, '_tracked_fd'):
                        try:
                            get_fd_manager().unregister_fd(conn._tracked_fd)
                        except Exception as e:
                            logger.debug(f"Could not unregister FD: {e}")
                    conn.close()
                except:
                    pass

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            self._closed = True
            for conn in self._pool:
                try:
                    # Unregister FD if tracked
                    if _fd_manager_available and hasattr(conn, '_tracked_fd'):
                        try:
                            get_fd_manager().unregister_fd(conn._tracked_fd)
                        except Exception as e:
                            logger.debug(f"Could not unregister FD: {e}")
                    conn.close()
                except:
                    pass
            self._pool.clear()
            logger.info("All database connections closed")


# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool(db_path: Optional[str] = None) -> ConnectionPool:
    """Get the global connection pool instance."""
    global _connection_pool

    if db_path is None:
        # Default database path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "data", "soulsense.db")

    with _pool_lock:
        if _connection_pool is None:
            _connection_pool = ConnectionPool(db_path)
            logger.info(f"Initialized database connection pool for {db_path}")

    return _connection_pool


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)


def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> List[tuple]:
    """
    Execute a SELECT query and return results.

    Args:
        query: SQL query string
        params: Query parameters
        db_path: Optional database path override

    Returns:
        List of result tuples
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_write(query: str, params: tuple = (), db_path: Optional[str] = None):
    """
    Execute an INSERT/UPDATE/DELETE query.

    Args:
        query: SQL query string
        params: Query parameters
        db_path: Optional database path override
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()


def init_database_schema():
    """Initialize the database schema using the connection pool."""
    schema_queries = [
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            age INTEGER,
            total_score INTEGER,
            avg_response REAL,
            max_response INTEGER,
            min_response INTEGER,
            score_variance REAL,
            questions_attempted INTEGER,
            completion_ratio REAL,
            avg_time_per_question REAL,
            time_taken_seconds INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
        """
    ]

    for query in schema_queries:
        execute_write(query)

    logger.info("Database schema initialized")


# Cleanup on application exit
import atexit
atexit.register(lambda: _connection_pool.close_all() if _connection_pool else None)