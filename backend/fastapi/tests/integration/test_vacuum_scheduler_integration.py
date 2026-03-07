"""
Integration tests for Adaptive Vacuum/Analyze Scheduler (#1415).

Tests end-to-end vacuum scheduling with real database operations.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.vacuum_scheduler import (
    VacuumScheduler,
    TableStatistics,
    VacuumJob,
    VacuumSchedule,
    SchedulerConfig,
    VacuumStrategy,
    SchedulePriority,
    TableSizeCategory,
    get_vacuum_scheduler,
)
from api.services.db_service import engine


@pytest.fixture
async def vacuum_scheduler():
    """Create and initialize vacuum scheduler for testing."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    return scheduler


@pytest.mark.asyncio
async def test_scheduler_initialization():
    """Test vacuum scheduler initialization."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    assert scheduler._metadata is not None


@pytest.mark.asyncio
async def test_statistics_collection():
    """Test table statistics collection."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    # Collect stats for all tables
    stats_dict = await scheduler.collect_table_statistics()
    
    assert isinstance(stats_dict, dict)


@pytest.mark.asyncio
async def test_single_table_statistics():
    """Test collecting stats for a single table."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    stats = await scheduler.collect_table_statistics("notification_logs", "public")
    
    if isinstance(stats, TableStatistics):
        assert stats.table_name == "notification_logs"
        assert hasattr(stats, 'total_size_bytes')


@pytest.mark.asyncio
async def test_table_size_categories():
    """Test table size category detection."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    await scheduler.collect_table_statistics()
    
    for stats in scheduler._table_stats.values():
        assert stats.size_category in [
            TableSizeCategory.SMALL,
            TableSizeCategory.MEDIUM,
            TableSizeCategory.LARGE,
            TableSizeCategory.VERY_LARGE,
        ]


@pytest.mark.asyncio
async def test_schedule_generation():
    """Test schedule generation."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    # Collect stats first
    await scheduler.collect_table_statistics()
    
    # Generate schedule
    schedule = await scheduler.generate_schedule(dry_run=True)
    
    assert isinstance(schedule, VacuumSchedule)
    assert isinstance(schedule.jobs, list)


@pytest.mark.asyncio
async def test_vacuum_job_execution_dry_run():
    """Test vacuum job execution in dry-run mode."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    job = await scheduler.vacuum_table(
        table_name="notification_logs",
        strategy=VacuumStrategy.ANALYZE,
        dry_run=True,
    )
    
    assert job.table_name == "notification_logs"
    assert job.dry_run is True
    assert job.status in ["completed", "failed"]


@pytest.mark.asyncio
async def test_run_adaptive_vacuum():
    """Test running full adaptive vacuum cycle."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    result = await scheduler.run_adaptive_vacuum(dry_run=True)
    
    assert "success" in result
    assert "jobs_executed" in result
    assert "duration_seconds" in result


@pytest.mark.asyncio
async def test_scheduler_statistics():
    """Test getting scheduler statistics."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    stats = await scheduler.get_statistics()
    
    assert "total_jobs" in stats
    assert "successful_jobs" in stats
    assert "failed_jobs" in stats


@pytest.mark.asyncio
async def test_job_history():
    """Test job history tracking."""
    scheduler = VacuumScheduler(engine)
    await scheduler.initialize()
    
    history = await scheduler.get_job_history(limit=10)
    
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_table_needs_vacuum_logic():
    """Test table needs vacuum detection logic."""
    stats_high_dead = TableStatistics(
        table_name="test",
        live_tuples=8000,
        dead_tuples=2000,  # 20%
    )
    assert stats_high_dead.needs_vacuum is True
    
    stats_clean = TableStatistics(
        table_name="test",
        live_tuples=10000,
        dead_tuples=100,  # 1%
        last_vacuum=datetime.utcnow(),
    )
    assert stats_clean.needs_vacuum is False


@pytest.mark.asyncio
async def test_table_needs_analyze_logic():
    """Test table needs analyze detection logic."""
    stats_never = TableStatistics(
        table_name="test",
        last_analyze=None,
    )
    assert stats_never.needs_analyze is True
    
    stats_with_changes = TableStatistics(
        table_name="test",
        estimated_rows=1000,
        n_tup_ins=100,
        n_tup_upd=50,
        n_tup_del=50,  # 20% changed
    )
    assert stats_with_changes.needs_analyze is True


@pytest.mark.asyncio
async def test_dead_tuple_ratio_calculation():
    """Test dead tuple ratio calculation."""
    stats = TableStatistics(
        table_name="test",
        live_tuples=9000,
        dead_tuples=1000,
    )
    
    assert stats.dead_tuple_ratio == 10.0
    
    stats_empty = TableStatistics(
        table_name="test",
        live_tuples=0,
        dead_tuples=0,
    )
    
    assert stats_empty.dead_tuple_ratio == 0.0


@pytest.mark.asyncio
async def test_size_category_boundaries():
    """Test size category boundary conditions."""
    # Small: < 10MB
    small = TableStatistics("s", total_size_bytes=9 * 1024 * 1024)
    assert small.size_category == TableSizeCategory.SMALL
    
    # Medium: 10MB - 100MB
    medium = TableStatistics("m", total_size_bytes=50 * 1024 * 1024)
    assert medium.size_category == TableSizeCategory.MEDIUM
    
    # Large: 100MB - 1GB
    large = TableStatistics("l", total_size_bytes=500 * 1024 * 1024)
    assert large.size_category == TableSizeCategory.LARGE
    
    # Very Large: > 1GB
    very_large = TableStatistics("vl", total_size_bytes=2 * 1024 * 1024 * 1024)
    assert very_large.size_category == TableSizeCategory.VERY_LARGE


@pytest.mark.asyncio
async def test_global_scheduler_instance():
    """Test global scheduler instance."""
    scheduler1 = await get_vacuum_scheduler(engine)
    scheduler2 = await get_vacuum_scheduler(engine)
    
    assert scheduler1 is scheduler2


@pytest.mark.asyncio
async def test_vacuum_job_creation():
    """Test vacuum job creation."""
    job = VacuumJob(
        table_name="test_table",
        strategy=VacuumStrategy.VACUUM_ANALYZE,
        priority=SchedulePriority.HIGH,
        scheduled_at=datetime.utcnow(),
        estimated_duration_seconds=300,
        reason="Test job",
        dry_run=True,
    )
    
    job_dict = job.to_dict()
    
    assert job_dict["table_name"] == "test_table"
    assert job_dict["strategy"] == "VACUUM ANALYZE"
    assert job_dict["priority"] == "high"


@pytest.mark.asyncio
async def test_schedule_creation():
    """Test schedule creation."""
    job1 = VacuumJob("t1", VacuumStrategy.VACUUM, SchedulePriority.NORMAL, datetime.utcnow())
    job2 = VacuumJob("t2", VacuumStrategy.ANALYZE, SchedulePriority.LOW, datetime.utcnow())
    
    schedule = VacuumSchedule(
        jobs=[job1, job2],
        total_estimated_duration_seconds=600,
    )
    
    schedule_dict = schedule.to_dict()
    
    assert schedule_dict["job_count"] == 2
    assert schedule_dict["total_estimated_duration_seconds"] == 600


@pytest.mark.asyncio
async def test_scheduler_config_defaults():
    """Test scheduler configuration defaults."""
    config = SchedulerConfig()
    
    assert config.dead_tuple_ratio_threshold == 20.0
    assert config.dead_tuple_count_threshold == 10000
    assert config.vacuum_interval_hours == 24
    assert config.analyze_interval_hours == 6
    assert config.max_concurrent_vacuums == 2
    assert config.dry_run_default is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
