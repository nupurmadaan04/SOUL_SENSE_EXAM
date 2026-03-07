"""
Adaptive Vacuum/Analyze Scheduler (#1415)

Provides intelligent, adaptive scheduling of PostgreSQL VACUUM and ANALYZE
operations based on table activity, bloat levels, and query patterns.

This scheduler optimizes database performance by:
- Monitoring table statistics and dead tuple ratios
- Automatically scheduling VACUUM when bloat thresholds are exceeded
- Running ANALYZE when table data significantly changes
- Adapting schedule based on query patterns and load
- Providing dry-run mode for safe testing

Features:
- Automatic table statistics collection
- Bloat detection and monitoring
- Adaptive scheduling based on activity
- Multiple vacuum strategies (FULL, FREEZE, ANALYZE)
- Concurrent operation management
- Comprehensive observability

Example:
    from api.utils.vacuum_scheduler import VacuumScheduler, VacuumStrategy
    
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    # Run adaptive vacuum
    result = await scheduler.run_adaptive_vacuum()
    
    # Schedule specific table
    result = await scheduler.vacuum_table(
        "responses",
        strategy=VacuumStrategy.VACUUM_ANALYZE
    )
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import json

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text, select, func

from ..services.db_service import AsyncSessionLocal


logger = logging.getLogger("api.vacuum_scheduler")


class VacuumStrategy(str, Enum):
    """Vacuum operation strategy."""
    VACUUM = "VACUUM"  # Standard vacuum
    VACUUM_FULL = "VACUUM FULL"  # Full vacuum (locks table)
    VACUUM_FREEZE = "VACUUM FREEZE"  # Freeze old tuples
    VACUUM_ANALYZE = "VACUUM ANALYZE"  # Vacuum + analyze
    ANALYZE = "ANALYZE"  # Update statistics only
    REINDEX = "REINDEX"  # Rebuild indexes


class SchedulePriority(str, Enum):
    """Scheduling priority level."""
    CRITICAL = "critical"  # Immediate execution
    HIGH = "high"  # Execute within 1 hour
    NORMAL = "normal"  # Execute during maintenance window
    LOW = "low"  # Execute when idle


class TableSizeCategory(str, Enum):
    """Table size category for scheduling decisions."""
    SMALL = "small"  # < 10MB
    MEDIUM = "medium"  # 10MB - 100MB
    LARGE = "large"  # 100MB - 1GB
    VERY_LARGE = "very_large"  # > 1GB


@dataclass
class TableStatistics:
    """Statistics for a database table."""
    table_name: str
    schema_name: str = "public"
    
    # Size metrics
    total_size_bytes: int = 0
    data_size_bytes: int = 0
    index_size_bytes: int = 0
    toast_size_bytes: int = 0
    
    # Row metrics
    live_tuples: int = 0
    dead_tuples: int = 0
    estimated_rows: int = 0
    
    # Activity metrics
    seq_scans: int = 0
    idx_scans: int = 0
    n_tup_ins: int = 0
    n_tup_upd: int = 0
    n_tup_del: int = 0
    
    # Maintenance info
    last_vacuum: Optional[datetime] = None
    last_autovacuum: Optional[datetime] = None
    last_analyze: Optional[datetime] = None
    last_autoanalyze: Optional[datetime] = None
    vacuum_count: int = 0
    autovacuum_count: int = 0
    analyze_count: int = 0
    autoanalyze_count: int = 0
    
    # Bloat metrics
    dead_tuple_ratio: float = 0.0
    bloat_ratio: float = 0.0
    
    collected_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)
    
    @property
    def size_category(self) -> TableSizeCategory:
        mb = self.total_size_mb
        if mb < 10:
            return TableSizeCategory.SMALL
        elif mb < 100:
            return TableSizeCategory.MEDIUM
        elif mb < 1024:
            return TableSizeCategory.LARGE
        return TableSizeCategory.VERY_LARGE
    
    @property
    def needs_vacuum(self) -> bool:
        """Determine if table needs vacuum based on metrics."""
        # High dead tuple ratio
        if self.dead_tuple_ratio > 20:  # >20% dead tuples
            return True
        # Large number of dead tuples
        if self.dead_tuples > 10000:
            return True
        # Never vacuumed
        if self.last_vacuum is None and self.last_autovacuum is None:
            return True
        # Old vacuum
        if self.last_vacuum:
            if datetime.utcnow() - self.last_vacuum > timedelta(days=7):
                return True
        return False
    
    @property
    def needs_analyze(self) -> bool:
        """Determine if table needs analyze."""
        # Never analyzed
        if self.last_analyze is None and self.last_autoanalyze is None:
            return True
        # Significant changes
        total_changes = self.n_tup_ins + self.n_tup_upd + self.n_tup_del
        if total_changes > self.estimated_rows * 0.1:  # >10% changed
            return True
        # Old analyze
        if self.last_analyze:
            if datetime.utcnow() - self.last_analyze > timedelta(hours=6):
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "total_size_mb": round(self.total_size_mb, 2),
            "size_category": self.size_category.value,
            "live_tuples": self.live_tuples,
            "dead_tuples": self.dead_tuples,
            "dead_tuple_ratio": round(self.dead_tuple_ratio, 2),
            "bloat_ratio": round(self.bloat_ratio, 2),
            "seq_scans": self.seq_scans,
            "idx_scans": self.idx_scans,
            "n_tup_ins": self.n_tup_ins,
            "n_tup_upd": self.n_tup_upd,
            "n_tup_del": self.n_tup_del,
            "last_vacuum": self.last_vacuum.isoformat() if self.last_vacuum else None,
            "last_analyze": self.last_analyze.isoformat() if self.last_analyze else None,
            "vacuum_count": self.vacuum_count,
            "analyze_count": self.analyze_count,
            "needs_vacuum": self.needs_vacuum,
            "needs_analyze": self.needs_analyze,
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass
class VacuumJob:
    """Represents a vacuum/analyze job."""
    table_name: str
    strategy: VacuumStrategy
    priority: SchedulePriority
    scheduled_at: datetime
    estimated_duration_seconds: int = 300
    reason: str = ""
    dry_run: bool = False
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    dead_tuples_before: int = 0
    dead_tuples_after: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "strategy": self.strategy.value,
            "priority": self.priority.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "dead_tuples_before": self.dead_tuples_before,
            "dead_tuples_after": self.dead_tuples_after,
        }


@dataclass
class VacuumSchedule:
    """Schedule for vacuum operations."""
    jobs: List[VacuumJob] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    total_estimated_duration_seconds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobs": [j.to_dict() for j in self.jobs],
            "created_at": self.created_at.isoformat(),
            "total_estimated_duration_seconds": self.total_estimated_duration_seconds,
            "job_count": len(self.jobs),
        }


@dataclass
class SchedulerConfig:
    """Configuration for vacuum scheduler."""
    # Thresholds
    dead_tuple_ratio_threshold: float = 20.0  # %
    dead_tuple_count_threshold: int = 10000
    bloat_ratio_threshold: float = 30.0  # %
    
    # Timing
    vacuum_interval_hours: int = 24
    analyze_interval_hours: int = 6
    maintenance_window_start: str = "02:00"  # HH:MM
    maintenance_window_end: str = "06:00"  # HH:MM
    
    # Concurrency
    max_concurrent_vacuums: int = 2
    max_concurrent_large_table_vacuums: int = 1
    
    # Size limits
    large_table_threshold_mb: int = 100
    very_large_table_threshold_mb: int = 1024
    
    # Safety
    dry_run_default: bool = True
    skip_tables: List[str] = field(default_factory=list)
    prioritize_tables: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dead_tuple_ratio_threshold": self.dead_tuple_ratio_threshold,
            "dead_tuple_count_threshold": self.dead_tuple_count_threshold,
            "bloat_ratio_threshold": self.bloat_ratio_threshold,
            "vacuum_interval_hours": self.vacuum_interval_hours,
            "analyze_interval_hours": self.analyze_interval_hours,
            "maintenance_window_start": self.maintenance_window_start,
            "maintenance_window_end": self.maintenance_window_end,
            "max_concurrent_vacuums": self.max_concurrent_vacuums,
            "dry_run_default": self.dry_run_default,
        }


class VacuumScheduler:
    """
    Adaptive vacuum/analyze scheduler for PostgreSQL.
    
    Automatically schedules and executes VACUUM and ANALYZE operations
    based on table statistics, bloat levels, and configured thresholds.
    
    Example:
        scheduler = VacuumScheduler(engine)
        await scheduler.initialize()
        
        # Collect statistics
        stats = await scheduler.collect_table_statistics()
        
        # Generate adaptive schedule
        schedule = await scheduler.generate_schedule()
        
        # Execute schedule
        results = await scheduler.execute_schedule(schedule)
    """
    
    def __init__(
        self,
        engine: AsyncEngine,
        config: Optional[SchedulerConfig] = None
    ):
        self.engine = engine
        self.config = config or SchedulerConfig()
        self._table_stats: Dict[str, TableStatistics] = {}
        self._running_jobs: Dict[str, VacuumJob] = {}
        self._job_callbacks: List[Callable[[VacuumJob], None]] = []
    
    async def initialize(self) -> None:
        """Initialize scheduler and ensure history tables exist."""
        await self._ensure_history_tables()
        logger.info("VacuumScheduler initialized")
    
    async def _ensure_history_tables(self) -> None:
        """Ensure vacuum history tables exist."""
        async with self.engine.begin() as conn:
            # Check if PostgreSQL
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            if "postgresql" not in version.lower():
                logger.warning("VacuumScheduler requires PostgreSQL")
                return
            
            # Create history table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vacuum_scheduler_history (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    schema_name VARCHAR(255) DEFAULT 'public',
                    strategy VARCHAR(50) NOT NULL,
                    priority VARCHAR(50) NOT NULL,
                    scheduled_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    dead_tuples_before INTEGER DEFAULT 0,
                    dead_tuples_after INTEGER DEFAULT 0,
                    duration_ms INTEGER,
                    dry_run BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Create indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vacuum_history_table 
                ON vacuum_scheduler_history(table_name, created_at DESC)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vacuum_history_status 
                ON vacuum_scheduler_history(status, created_at DESC)
            """))
        
        logger.info("Vacuum scheduler history tables ensured")
    
    async def collect_table_statistics(
        self,
        table_name: Optional[str] = None,
        schema: str = "public"
    ) -> Union[TableStatistics, Dict[str, TableStatistics]]:
        """
        Collect statistics for one or all tables.
        
        Args:
            table_name: Specific table (None = all tables)
            schema: Schema name
            
        Returns:
            TableStatistics or dict of table_name -> TableStatistics
        """
        if table_name:
            stats = await self._collect_single_table_stats(table_name, schema)
            self._table_stats[f"{schema}.{table_name}"] = stats
            return stats
        
        # Collect for all tables
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname = :schema
                AND tablename NOT LIKE 'pg_%'
                AND tablename NOT LIKE 'sql_%'
            """), {"schema": schema})
            
            tables = [(row.schemaname, row.tablename) for row in result]
        
        for schema_name, tbl_name in tables:
            try:
                stats = await self._collect_single_table_stats(tbl_name, schema_name)
                self._table_stats[f"{schema_name}.{tbl_name}"] = stats
            except Exception as e:
                logger.warning(f"Failed to collect stats for {tbl_name}: {e}")
        
        return self._table_stats
    
    async def _collect_single_table_stats(
        self,
        table_name: str,
        schema: str = "public"
    ) -> TableStatistics:
        """Collect statistics for a single table."""
        stats = TableStatistics(table_name=table_name, schema_name=schema)
        
        async with AsyncSessionLocal() as session:
            # Get table size
            size_result = await session.execute(
                text("""
                    SELECT 
                        pg_total_relation_size(:full_name) as total_size,
                        pg_relation_size(:full_name) as data_size,
                        pg_indexes_size(:full_name) as index_size,
                        COALESCE(pg_relation_size(:toast_name), 0) as toast_size
                """),
                {
                    "full_name": f"{schema}.{table_name}",
                    "toast_name": f"{schema}.pg_toast.pg_toast_{table_name}_oid",
                }
            )
            size_row = size_result.fetchone()
            if size_row:
                stats.total_size_bytes = size_row.total_size or 0
                stats.data_size_bytes = size_row.data_size or 0
                stats.index_size_bytes = size_row.index_size or 0
                stats.toast_size_bytes = size_row.toast_size or 0
            
            # Get pg_stats info
            stats_result = await session.execute(
                text("""
                    SELECT 
                        n_live_tup,
                        n_dead_tup,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        seq_scan,
                        idx_scan,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze,
                        vacuum_count,
                        autovacuum_count,
                        analyze_count,
                        autoanalyze_count
                    FROM pg_stat_user_tables
                    WHERE schemaname = :schema
                    AND relname = :table
                """),
                {"schema": schema, "table": table_name}
            )
            stats_row = stats_result.fetchone()
            
            if stats_row:
                stats.live_tuples = stats_row.n_live_tup or 0
                stats.dead_tuples = stats_row.n_dead_tup or 0
                stats.n_tup_ins = stats_row.n_tup_ins or 0
                stats.n_tup_upd = stats_row.n_tup_upd or 0
                stats.n_tup_del = stats_row.n_tup_del or 0
                stats.seq_scans = stats_row.seq_scan or 0
                stats.idx_scans = stats_row.idx_scan or 0
                stats.last_vacuum = stats_row.last_vacuum
                stats.last_autovacuum = stats_row.last_autovacuum
                stats.last_analyze = stats_row.last_analyze
                stats.last_autoanalyze = stats_row.last_autoanalyze
                stats.vacuum_count = stats_row.vacuum_count or 0
                stats.autovacuum_count = stats_row.autovacuum_count or 0
                stats.analyze_count = stats_row.analyze_count or 0
                stats.autoanalyze_count = stats_row.autoanalyze_count or 0
                
                # Calculate dead tuple ratio
                total_tuples = stats.live_tuples + stats.dead_tuples
                if total_tuples > 0:
                    stats.dead_tuple_ratio = (stats.dead_tuples / total_tuples) * 100
                
                stats.estimated_rows = stats.live_tuples
        
        return stats
    
    async def generate_schedule(
        self,
        dry_run: bool = True
    ) -> VacuumSchedule:
        """
        Generate adaptive vacuum schedule based on table statistics.
        
        Args:
            dry_run: If True, don't actually execute
            
        Returns:
            VacuumSchedule with prioritized jobs
        """
        schedule = VacuumSchedule()
        
        # Ensure we have current stats
        if not self._table_stats:
            await self.collect_table_statistics()
        
        now = datetime.utcnow()
        
        for full_name, stats in self._table_stats.items():
            # Skip configured tables
            if stats.table_name in self.config.skip_tables:
                continue
            
            # Determine if vacuum needed
            if stats.needs_vacuum:
                # Determine priority
                if stats.dead_tuple_ratio > 50 or stats.dead_tuples > 100000:
                    priority = SchedulePriority.CRITICAL
                elif stats.dead_tuple_ratio > 30:
                    priority = SchedulePriority.HIGH
                elif stats.size_category == TableSizeCategory.VERY_LARGE:
                    priority = SchedulePriority.LOW
                else:
                    priority = SchedulePriority.NORMAL
                
                # Determine strategy
                if stats.dead_tuple_ratio > 40:
                    strategy = VacuumStrategy.VACUUM_ANALYZE
                else:
                    strategy = VacuumStrategy.VACUUM
                
                # Estimate duration
                estimated_seconds = self._estimate_vacuum_duration(stats)
                
                job = VacuumJob(
                    table_name=stats.table_name,
                    strategy=strategy,
                    priority=priority,
                    scheduled_at=now,
                    estimated_duration_seconds=estimated_seconds,
                    reason=f"Dead tuple ratio: {stats.dead_tuple_ratio:.1f}%",
                    dry_run=dry_run,
                    dead_tuples_before=stats.dead_tuples,
                )
                schedule.jobs.append(job)
            
            # Determine if analyze needed (separate from vacuum)
            elif stats.needs_analyze:
                job = VacuumJob(
                    table_name=stats.table_name,
                    strategy=VacuumStrategy.ANALYZE,
                    priority=SchedulePriority.NORMAL,
                    scheduled_at=now,
                    estimated_duration_seconds=min(60, stats.total_size_mb / 10),
                    reason="Statistics stale",
                    dry_run=dry_run,
                )
                schedule.jobs.append(job)
        
        # Sort by priority
        priority_order = {
            SchedulePriority.CRITICAL: 0,
            SchedulePriority.HIGH: 1,
            SchedulePriority.NORMAL: 2,
            SchedulePriority.LOW: 3,
        }
        schedule.jobs.sort(key=lambda j: priority_order.get(j.priority, 99))
        
        # Calculate total duration
        schedule.total_estimated_duration_seconds = sum(
            j.estimated_duration_seconds for j in schedule.jobs
        )
        
        logger.info(
            f"Generated schedule with {len(schedule.jobs)} jobs, "
            f"estimated duration: {schedule.total_estimated_duration_seconds}s"
        )
        
        return schedule
    
    def _estimate_vacuum_duration(self, stats: TableStatistics) -> int:
        """Estimate vacuum duration based on table size and dead tuples."""
        base_time = 30  # Base 30 seconds
        
        # Size factor
        size_factor = stats.total_size_mb / 100  # ~1s per 100MB
        
        # Dead tuple factor
        dead_tuple_factor = stats.dead_tuples / 10000  # ~1s per 10k dead tuples
        
        estimated = base_time + size_factor + dead_tuple_factor
        return min(int(estimated), 3600)  # Cap at 1 hour
    
    async def execute_schedule(
        self,
        schedule: VacuumSchedule,
        max_concurrent: Optional[int] = None
    ) -> List[VacuumJob]:
        """
        Execute a vacuum schedule.
        
        Args:
            schedule: VacuumSchedule to execute
            max_concurrent: Max concurrent operations
            
        Returns:
            List of completed VacuumJob objects
        """
        if max_concurrent is None:
            max_concurrent = self.config.max_concurrent_vacuums
        
        completed_jobs = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_job(job: VacuumJob) -> VacuumJob:
            async with semaphore:
                return await self._execute_single_job(job)
        
        # Execute all jobs
        tasks = [execute_job(job) for job in schedule.jobs]
        completed_jobs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        results = []
        for job in completed_jobs:
            if isinstance(job, Exception):
                logger.error(f"Job failed with exception: {job}")
            else:
                results.append(job)
        
        return results
    
    async def _execute_single_job(self, job: VacuumJob) -> VacuumJob:
        """Execute a single vacuum job."""
        job.started_at = datetime.utcnow()
        job.status = "running"
        
        try:
            if job.dry_run:
                logger.info(f"[DRY RUN] Would execute: {job.strategy.value} {job.table_name}")
                await asyncio.sleep(1)  # Simulate work
                job.status = "completed"
            else:
                logger.info(f"Executing: {job.strategy.value} {job.table_name}")
                
                async with AsyncSessionLocal() as session:
                    # Execute vacuum/analyze
                    await session.execute(
                        text(f"{job.strategy.value} {job.table_name}")
                    )
                    await session.commit()
                
                # Collect after stats
                after_stats = await self._collect_single_table_stats(job.table_name)
                job.dead_tuples_after = after_stats.dead_tuples
                job.status = "completed"
                
                logger.info(
                    f"Completed {job.strategy.value} {job.table_name}: "
                    f"dead tuples {job.dead_tuples_before} -> {job.dead_tuples_after}"
                )
            
            job.completed_at = datetime.utcnow()
            
            # Record in history
            await self._record_job_history(job)
            
            # Trigger callbacks
            for callback in self._job_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job)
                    else:
                        callback(job)
                except Exception as e:
                    logger.error(f"Job callback failed: {e}")
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            logger.error(f"Job failed for {job.table_name}: {e}")
        
        return job
    
    async def vacuum_table(
        self,
        table_name: str,
        strategy: VacuumStrategy = VacuumStrategy.VACUUM_ANALYZE,
        dry_run: bool = True
    ) -> VacuumJob:
        """
        Vacuum a specific table.
        
        Args:
            table_name: Table to vacuum
            strategy: Vacuum strategy
            dry_run: If True, only simulate
            
        Returns:
            Completed VacuumJob
        """
        # Collect before stats
        before_stats = await self._collect_single_table_stats(table_name)
        
        job = VacuumJob(
            table_name=table_name,
            strategy=strategy,
            priority=SchedulePriority.HIGH,
            scheduled_at=datetime.utcnow(),
            estimated_duration_seconds=self._estimate_vacuum_duration(before_stats),
            reason="Manual execution",
            dry_run=dry_run,
            dead_tuples_before=before_stats.dead_tuples,
        )
        
        return await self._execute_single_job(job)
    
    async def run_adaptive_vacuum(
        self,
        dry_run: bool = True,
        max_concurrent: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run full adaptive vacuum cycle.
        
        Args:
            dry_run: If True, only simulate
            max_concurrent: Max concurrent operations
            
        Returns:
            Results summary dictionary
        """
        start_time = datetime.utcnow()
        
        # Collect statistics
        await self.collect_table_statistics()
        
        # Generate schedule
        schedule = await self.generate_schedule(dry_run=dry_run)
        
        if not schedule.jobs:
            return {
                "success": True,
                "message": "No tables need vacuum/analyze",
                "jobs_executed": 0,
                "duration_seconds": 0,
            }
        
        # Execute schedule
        completed_jobs = await self.execute_schedule(schedule, max_concurrent)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Build summary
        successful = sum(1 for j in completed_jobs if j.status == "completed")
        failed = sum(1 for j in completed_jobs if j.status == "failed")
        
        summary = {
            "success": failed == 0,
            "jobs_executed": len(completed_jobs),
            "jobs_successful": successful,
            "jobs_failed": failed,
            "duration_seconds": round(duration, 2),
            "dry_run": dry_run,
            "jobs": [j.to_dict() for j in completed_jobs],
        }
        
        logger.info(
            f"Adaptive vacuum completed: {successful} successful, {failed} failed, "
            f"duration: {duration:.2f}s"
        )
        
        return summary
    
    async def _record_job_history(self, job: VacuumJob) -> None:
        """Record job execution in history table."""
        try:
            duration_ms = 0
            if job.started_at and job.completed_at:
                duration_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)
            
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        INSERT INTO vacuum_scheduler_history (
                            table_name, strategy, priority, scheduled_at,
                            started_at, completed_at, status, error_message,
                            dead_tuples_before, dead_tuples_after, duration_ms, dry_run
                        ) VALUES (
                            :table_name, :strategy, :priority, :scheduled_at,
                            :started_at, :completed_at, :status, :error_message,
                            :dead_tuples_before, :dead_tuples_after, :duration_ms, :dry_run
                        )
                    """),
                    {
                        "table_name": job.table_name,
                        "strategy": job.strategy.value,
                        "priority": job.priority.value,
                        "scheduled_at": job.scheduled_at,
                        "started_at": job.started_at,
                        "completed_at": job.completed_at,
                        "status": job.status,
                        "error_message": job.error_message,
                        "dead_tuples_before": job.dead_tuples_before,
                        "dead_tuples_after": job.dead_tuples_after,
                        "duration_ms": duration_ms,
                        "dry_run": job.dry_run,
                    }
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record job history: {e}")
    
    async def get_job_history(
        self,
        table_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get job execution history."""
        async with AsyncSessionLocal() as session:
            if table_name:
                result = await session.execute(
                    text("""
                        SELECT * FROM vacuum_scheduler_history
                        WHERE table_name = :table_name
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"table_name": table_name, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM vacuum_scheduler_history
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            history = []
            for row in result:
                history.append({
                    "id": row.id,
                    "table_name": row.table_name,
                    "strategy": row.strategy,
                    "priority": row.priority,
                    "status": row.status,
                    "dead_tuples_before": row.dead_tuples_before,
                    "dead_tuples_after": row.dead_tuples_after,
                    "duration_ms": row.duration_ms,
                    "dry_run": row.dry_run,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
            
            return history
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        async with AsyncSessionLocal() as session:
            # Total jobs
            result = await session.execute(
                text("SELECT COUNT(*) FROM vacuum_scheduler_history")
            )
            total_jobs = result.scalar()
            
            # Successful jobs
            result = await session.execute(
                text("SELECT COUNT(*) FROM vacuum_scheduler_history WHERE status = 'completed'")
            )
            successful_jobs = result.scalar()
            
            # Failed jobs
            result = await session.execute(
                text("SELECT COUNT(*) FROM vacuum_scheduler_history WHERE status = 'failed'")
            )
            failed_jobs = result.scalar()
            
            # Recent jobs (24h)
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM vacuum_scheduler_history
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
            )
            recent_jobs = result.scalar()
            
            # Total dead tuples removed
            result = await session.execute(
                text("""
                    SELECT COALESCE(SUM(dead_tuples_before - dead_tuples_after), 0)
                    FROM vacuum_scheduler_history
                    WHERE status = 'completed' AND dry_run = FALSE
                """)
            )
            dead_tuples_removed = result.scalar()
            
            return {
                "total_jobs": total_jobs,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_jobs,
                "recent_jobs_24h": recent_jobs,
                "dead_tuples_removed": dead_tuples_removed,
                "tables_monitored": len(self._table_stats),
            }
    
    def register_job_callback(self, callback: Callable[[VacuumJob], None]) -> None:
        """Register a callback for job completion."""
        self._job_callbacks.append(callback)


# Global instance
_vacuum_scheduler: Optional[VacuumScheduler] = None


async def get_vacuum_scheduler(
    engine: Optional[AsyncEngine] = None
) -> VacuumScheduler:
    """Get or create the global vacuum scheduler."""
    global _vacuum_scheduler
    
    if _vacuum_scheduler is None:
        if engine is None:
            from ..services.db_service import engine
        _vacuum_scheduler = VacuumScheduler(engine)
        await _vacuum_scheduler.initialize()
    
    return _vacuum_scheduler
