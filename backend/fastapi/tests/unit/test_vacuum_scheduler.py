"""
Unit tests for Adaptive Vacuum/Analyze Scheduler (#1415).

Tests table statistics collection, scheduling algorithms, and vacuum operations.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
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


class TestTableStatistics:
    """Test TableStatistics dataclass."""

    def test_basic_creation(self):
        """Test creating table statistics."""
        stats = TableStatistics(
            table_name="test_table",
            schema_name="public",
            total_size_bytes=1024 * 1024 * 50,  # 50MB
            live_tuples=10000,
            dead_tuples=1000,
        )
        
        assert stats.table_name == "test_table"
        assert stats.total_size_mb == 50.0
        assert stats.live_tuples == 10000
        assert stats.dead_tuples == 1000

    def test_size_categories(self):
        """Test size category determination."""
        small = TableStatistics("t1", total_size_bytes=5 * 1024 * 1024)
        medium = TableStatistics("t2", total_size_bytes=50 * 1024 * 1024)
        large = TableStatistics("t3", total_size_bytes=500 * 1024 * 1024)
        very_large = TableStatistics("t4", total_size_bytes=2 * 1024 * 1024 * 1024)
        
        assert small.size_category == TableSizeCategory.SMALL
        assert medium.size_category == TableSizeCategory.MEDIUM
        assert large.size_category == TableSizeCategory.LARGE
        assert very_large.size_category == TableSizeCategory.VERY_LARGE

    def test_dead_tuple_ratio(self):
        """Test dead tuple ratio calculation."""
        stats = TableStatistics(
            "test",
            live_tuples=9000,
            dead_tuples=1000,
        )
        
        assert stats.dead_tuple_ratio == 10.0  # 1000/10000 = 10%

    def test_needs_vacuum_high_dead_ratio(self):
        """Test vacuum needed with high dead tuple ratio."""
        stats = TableStatistics(
            "test",
            live_tuples=8000,
            dead_tuples=2000,  # 20% dead
        )
        
        assert stats.needs_vacuum is True

    def test_needs_vacuum_high_dead_count(self):
        """Test vacuum needed with high dead tuple count."""
        stats = TableStatistics(
            "test",
            live_tuples=100000,
            dead_tuples=15000,  # > 10000
        )
        
        assert stats.needs_vacuum is True

    def test_needs_vacuum_never_vacuumed(self):
        """Test vacuum needed when never vacuumed."""
        stats = TableStatistics(
            "test",
            live_tuples=1000,
            dead_tuples=100,
            last_vacuum=None,
            last_autovacuum=None,
        )
        
        assert stats.needs_vacuum is True

    def test_needs_vacuum_old_vacuum(self):
        """Test vacuum needed when last vacuum is old."""
        old_date = datetime.utcnow() - timedelta(days=10)
        stats = TableStatistics(
            "test",
            live_tuples=1000,
            dead_tuples=10,
            last_vacuum=old_date,
        )
        
        assert stats.needs_vacuum is True

    def test_no_vacuum_needed(self):
        """Test when vacuum is not needed."""
        recent_date = datetime.utcnow() - timedelta(days=1)
        stats = TableStatistics(
            "test",
            live_tuples=10000,
            dead_tuples=100,  # < 20% and < 10000
            last_vacuum=recent_date,
        )
        
        assert stats.needs_vacuum is False

    def test_needs_analyze_never_analyzed(self):
        """Test analyze needed when never analyzed."""
        stats = TableStatistics(
            "test",
            last_analyze=None,
            last_autoanalyze=None,
        )
        
        assert stats.needs_analyze is True

    def test_needs_analyze_significant_changes(self):
        """Test analyze needed with significant changes."""
        stats = TableStatistics(
            "test",
            estimated_rows=1000,
            n_tup_ins=50,
            n_tup_upd=30,
            n_tup_del=20,  # 100 changes = 10%
        )
        
        assert stats.needs_analyze is True

    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = TableStatistics(
            table_name="test",
            schema_name="public",
            total_size_bytes=1024 * 1024 * 100,
            live_tuples=5000,
            dead_tuples=500,
        )
        
        result = stats.to_dict()
        
        assert result["table_name"] == "test"
        assert result["total_size_mb"] == 100.0
        assert result["size_category"] == "medium"


class TestVacuumJob:
    """Test VacuumJob dataclass."""

    def test_basic_creation(self):
        """Test creating a vacuum job."""
        job = VacuumJob(
            table_name="test_table",
            strategy=VacuumStrategy.VACUUM_ANALYZE,
            priority=SchedulePriority.NORMAL,
            scheduled_at=datetime.utcnow(),
        )
        
        assert job.table_name == "test_table"
        assert job.strategy == VacuumStrategy.VACUUM_ANALYZE
        assert job.status == "pending"

    def test_to_dict(self):
        """Test converting to dictionary."""
        job = VacuumJob(
            table_name="test_table",
            strategy=VacuumStrategy.VACUUM,
            priority=SchedulePriority.HIGH,
            scheduled_at=datetime(2026, 3, 7, 12, 0, 0),
            estimated_duration_seconds=300,
            reason="Dead tuples",
            dry_run=True,
            dead_tuples_before=1000,
            status="completed",
        )
        
        result = job.to_dict()
        
        assert result["table_name"] == "test_table"
        assert result["strategy"] == "VACUUM"
        assert result["priority"] == "high"
        assert result["dry_run"] is True


class TestVacuumSchedule:
    """Test VacuumSchedule dataclass."""

    def test_basic_creation(self):
        """Test creating a schedule."""
        job1 = VacuumJob("t1", VacuumStrategy.VACUUM, SchedulePriority.HIGH, datetime.utcnow())
        job2 = VacuumJob("t2", VacuumStrategy.ANALYZE, SchedulePriority.NORMAL, datetime.utcnow())
        
        schedule = VacuumSchedule(
            jobs=[job1, job2],
            total_estimated_duration_seconds=600,
        )
        
        assert len(schedule.jobs) == 2
        assert schedule.total_estimated_duration_seconds == 600

    def test_to_dict(self):
        """Test converting to dictionary."""
        job = VacuumJob("test", VacuumStrategy.VACUUM, SchedulePriority.NORMAL, datetime.utcnow())
        schedule = VacuumSchedule(jobs=[job])
        
        result = schedule.to_dict()
        
        assert result["job_count"] == 1
        assert len(result["jobs"]) == 1


class TestSchedulerConfig:
    """Test SchedulerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SchedulerConfig()
        
        assert config.dead_tuple_ratio_threshold == 20.0
        assert config.vacuum_interval_hours == 24
        assert config.analyze_interval_hours == 6
        assert config.max_concurrent_vacuums == 2
        assert config.dry_run_default is True

    def test_to_dict(self):
        """Test converting to dictionary."""
        config = SchedulerConfig()
        result = config.to_dict()
        
        assert "dead_tuple_ratio_threshold" in result
        assert "vacuum_interval_hours" in result


class TestVacuumSchedulerInitialization:
    """Test VacuumScheduler initialization."""

    def test_init_with_engine(self):
        """Test initialization with engine."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        assert scheduler.engine == mock_engine
        assert len(scheduler._table_stats) == 0

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test scheduler initialization."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        with patch.object(scheduler, '_ensure_history_tables') as mock_ensure:
            await scheduler.initialize()
            mock_ensure.assert_called_once()


class TestScheduleGeneration:
    """Test schedule generation."""

    @pytest.mark.asyncio
    async def test_generate_schedule_no_stats(self):
        """Test schedule generation with no stats."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        with patch.object(scheduler, 'collect_table_statistics') as mock_collect:
            mock_collect.return_value = {}
            
            schedule = await scheduler.generate_schedule()
            
            assert len(schedule.jobs) == 0

    @pytest.mark.asyncio
    async def test_generate_schedule_with_needs_vacuum(self):
        """Test schedule generation with tables needing vacuum."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        stats = TableStatistics(
            table_name="test_table",
            live_tuples=8000,
            dead_tuples=2000,  # 20% dead
        )
        scheduler._table_stats = {"public.test_table": stats}
        
        schedule = await scheduler.generate_schedule(dry_run=True)
        
        assert len(schedule.jobs) == 1
        assert schedule.jobs[0].table_name == "test_table"

    @pytest.mark.asyncio
    async def test_generate_schedule_critical_priority(self):
        """Test critical priority assignment."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        stats = TableStatistics(
            table_name="test_table",
            live_tuples=5000,
            dead_tuples=5000,  # 50% dead - critical
        )
        scheduler._table_stats = {"public.test_table": stats}
        
        schedule = await scheduler.generate_schedule()
        
        assert schedule.jobs[0].priority == SchedulePriority.CRITICAL


class TestDurationEstimation:
    """Test duration estimation."""

    def test_estimate_small_table(self):
        """Test duration estimation for small table."""
        mock_engine = Mock()
        scheduler = VacuumScheduler(mock_engine)
        
        stats = TableStatistics(
            table_name="small",
            total_size_bytes=1024 * 1024 * 10,  # 10MB
            dead_tuples=1000,
        )
        
        duration = scheduler._estimate_vacuum_duration(stats)
        
        assert duration >= 30  # Base time
        assert duration <= 3600  # Cap at 1 hour


class TestEnums:
    """Test enum classes."""

    def test_vacuum_strategy_values(self):
        """Test vacuum strategy enum values."""
        assert VacuumStrategy.VACUUM.value == "VACUUM"
        assert VacuumStrategy.VACUUM_FULL.value == "VACUUM FULL"
        assert VacuumStrategy.VACUUM_FREEZE.value == "VACUUM FREEZE"
        assert VacuumStrategy.VACUUM_ANALYZE.value == "VACUUM ANALYZE"
        assert VacuumStrategy.ANALYZE.value == "ANALYZE"
        assert VacuumStrategy.REINDEX.value == "REINDEX"

    def test_schedule_priority_values(self):
        """Test schedule priority enum values."""
        assert SchedulePriority.CRITICAL.value == "critical"
        assert SchedulePriority.HIGH.value == "high"
        assert SchedulePriority.NORMAL.value == "normal"
        assert SchedulePriority.LOW.value == "low"

    def test_table_size_category_values(self):
        """Test table size category enum values."""
        assert TableSizeCategory.SMALL.value == "small"
        assert TableSizeCategory.MEDIUM.value == "medium"
        assert TableSizeCategory.LARGE.value == "large"
        assert TableSizeCategory.VERY_LARGE.value == "very_large"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
