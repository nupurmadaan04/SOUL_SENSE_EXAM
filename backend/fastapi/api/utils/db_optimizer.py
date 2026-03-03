"""
Database connection pool optimizer.

Implements:
- Connection pool sizing based on load
- Connection health checks
- Query timeout enforcement
- Slow query logging
"""

import time
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event, text

logger = logging.getLogger(__name__)

# Slow query threshold (milliseconds)
SLOW_QUERY_THRESHOLD = 1000


@event.listens_for(AsyncSession, "after_cursor_execute")
def log_slow_queries(conn, cursor, statement, parameters, context, executemany):
    """Log queries that exceed threshold."""
    duration = time.time() - context._query_start_time
    duration_ms = duration * 1000
    
    if duration_ms > SLOW_QUERY_THRESHOLD:
        logger.warning(
            f"Slow query detected: {duration_ms:.2f}ms\n"
            f"Statement: {statement}\n"
            f"Parameters: {parameters}"
        )


@event.listens_for(AsyncSession, "before_cursor_execute")
def start_query_timer(conn, cursor, statement, parameters, context, executemany):
    """Start timer for query execution."""
    context._query_start_time = time.time()


class ConnectionPoolOptimizer:
    """Optimize database connection pool settings."""
    
    @staticmethod
    def get_optimal_pool_size(max_connections: int = 100) -> dict:
        """
        Calculate optimal pool size based on system resources.
        
        Formula: pool_size = (core_count * 2) + effective_spindle_count
        For async: pool_size = core_count * 4
        """
        import os
        
        cpu_count = os.cpu_count() or 4
        
        return {
            'pool_size': min(cpu_count * 4, max_connections),
            'max_overflow': min(cpu_count * 2, 20),
            'pool_timeout': 30,
            'pool_recycle': 3600,  # 1 hour
            'pool_pre_ping': True,  # Health check
        }
    
    @staticmethod
    async def health_check(db: AsyncSession) -> bool:
        """Check database connection health."""
        try:
            await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


@asynccontextmanager
async def optimized_db_session(session_factory):
    """Context manager for optimized database sessions."""
    session = session_factory()
    try:
        # Set statement timeout
        await session.execute(text("SET statement_timeout = '30s'"))
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
