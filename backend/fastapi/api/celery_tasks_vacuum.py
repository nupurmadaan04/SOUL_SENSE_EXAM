"""
Celery Background Tasks for Vacuum Scheduler (#1415)

Provides automated background vacuum and analyze operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .celery_app import celery_app

logger = logging.getLogger("api.celery_tasks.vacuum")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def vacuum_table_task(
    self,
    table_name: str,
    strategy: str = "VACUUM ANALYZE",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Vacuum a specific table.
    
    Args:
        table_name: Table to vacuum
        strategy: Vacuum strategy
        dry_run: If True, only simulate
        
    Returns:
        Dictionary with job results
    """
    async def _execute():
        from api.utils.vacuum_scheduler import get_vacuum_scheduler, VacuumStrategy
        
        scheduler = await get_vacuum_scheduler()
        
        # Parse strategy
        strategy_map = {
            "VACUUM": VacuumStrategy.VACUUM,
            "VACUUM FULL": VacuumStrategy.VACUUM_FULL,
            "VACUUM FREEZE": VacuumStrategy.VACUUM_FREEZE,
            "VACUUM ANALYZE": VacuumStrategy.VACUUM_ANALYZE,
            "ANALYZE": VacuumStrategy.ANALYZE,
        }
        vacuum_strategy = strategy_map.get(strategy, VacuumStrategy.VACUUM_ANALYZE)
        
        job = await scheduler.vacuum_table(
            table_name=table_name,
            strategy=vacuum_strategy,
            dry_run=dry_run,
        )
        
        return job.to_dict()
    
    try:
        result = asyncio.run(_execute())
        
        logger.info(
            f"Vacuum task completed for {table_name}: "
            f"status={result['status']}, dry_run={dry_run}"
        )
        
        return result
        
    except Exception as exc:
        logger.error(f"Vacuum task failed for {table_name}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=600)
def run_adaptive_vacuum_task(
    self,
    dry_run: bool = False,
    max_concurrent: int = 2
) -> Dict[str, Any]:
    """
    Run full adaptive vacuum cycle.
    
    This task is designed to run on a schedule (e.g., daily) to
    automatically maintain database performance.
    
    Args:
        dry_run: If True, only simulate
        max_concurrent: Max concurrent vacuum operations
        
    Returns:
        Dictionary with vacuum results
    """
    async def _execute():
        from api.utils.vacuum_scheduler import get_vacuum_scheduler
        
        scheduler = await get_vacuum_scheduler()
        
        result = await scheduler.run_adaptive_vacuum(
            dry_run=dry_run,
            max_concurrent=max_concurrent,
        )
        
        return result
    
    try:
        result = asyncio.run(_execute())
        
        logger.info(
            f"Adaptive vacuum completed: "
            f"jobs={result['jobs_executed']}, "
            f"successful={result['jobs_successful']}, "
            f"failed={result['jobs_failed']}, "
            f"duration={result['duration_seconds']:.2f}s"
        )
        
        return result
        
    except Exception as exc:
        logger.error(f"Adaptive vacuum task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def analyze_all_tables_task(self, dry_run: bool = False) -> Dict[str, Any]:
    """
    Run ANALYZE on all tables that need it.
    
    Args:
        dry_run: If True, only simulate
        
    Returns:
        Dictionary with analyze results
    """
    async def _execute():
        from api.utils.vacuum_scheduler import (
            get_vacuum_scheduler,
            VacuumStrategy,
            VacuumJob,
            SchedulePriority,
        )
        
        scheduler = await get_vacuum_scheduler()
        
        # Collect statistics
        await scheduler.collect_table_statistics()
        
        # Find tables needing analyze
        tables_to_analyze = []
        for full_name, stats in scheduler._table_stats.items():
            if stats.needs_analyze and not stats.needs_vacuum:
                tables_to_analyze.append(stats.table_name)
        
        if not tables_to_analyze:
            return {
                "success": True,
                "message": "No tables need analyze",
                "tables_analyzed": 0,
            }
        
        # Create jobs
        jobs = []
        for table_name in tables_to_analyze:
            job = VacuumJob(
                table_name=table_name,
                strategy=VacuumStrategy.ANALYZE,
                priority=SchedulePriority.NORMAL,
                scheduled_at=datetime.utcnow(),
                reason="Statistics update needed",
                dry_run=dry_run,
            )
            jobs.append(job)
        
        # Execute jobs
        schedule = scheduler.VacuumSchedule(jobs=jobs)
        completed = await scheduler.execute_schedule(schedule)
        
        successful = sum(1 for j in completed if j.status == "completed")
        
        return {
            "success": True,
            "tables_analyzed": len(completed),
            "successful": successful,
            "dry_run": dry_run,
        }
    
    try:
        from datetime import datetime
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"Analyze all tables task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def vacuum_large_tables_task(
    self,
    dry_run: bool = False,
    size_threshold_mb: int = 1024
) -> Dict[str, Any]:
    """
    Vacuum only large tables (> threshold).
    
    Args:
        dry_run: If True, only simulate
        size_threshold_mb: Size threshold in MB
        
    Returns:
        Dictionary with vacuum results
    """
    async def _execute():
        from api.utils.vacuum_scheduler import (
            get_vacuum_scheduler,
            VacuumStrategy,
            TableSizeCategory,
        )
        
        scheduler = await get_vacuum_scheduler()
        
        # Collect statistics
        await scheduler.collect_table_statistics()
        
        # Find large tables needing vacuum
        large_tables = []
        for full_name, stats in scheduler._table_stats.items():
            if (stats.size_category in (TableSizeCategory.LARGE, TableSizeCategory.VERY_LARGE)
                and stats.needs_vacuum):
                large_tables.append(stats.table_name)
        
        if not large_tables:
            return {
                "success": True,
                "message": "No large tables need vacuum",
                "tables_vacuumed": 0,
            }
        
        # Vacuum large tables one at a time
        results = []
        for table_name in large_tables:
            job = await scheduler.vacuum_table(
                table_name=table_name,
                strategy=VacuumStrategy.VACUUM_ANALYZE,
                dry_run=dry_run,
            )
            results.append(job.to_dict())
        
        successful = sum(1 for r in results if r["status"] == "completed")
        
        return {
            "success": True,
            "tables_vacuumed": len(results),
            "successful": successful,
            "dry_run": dry_run,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"Vacuum large tables task failed: {exc}")
        raise self.retry(exc=exc)


# Schedule configuration (to be added to Celery beat schedule)
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # ... existing schedules ...
    
    'adaptive-vacuum-daily': {
        'task': 'api.celery_tasks_vacuum.run_adaptive_vacuum_task',
        'schedule': crontab(hour=2, minute=30),  # Daily at 2:30 AM
        'kwargs': {'dry_run': False, 'max_concurrent': 2},
    },
    
    'analyze-all-hourly': {
        'task': 'api.celery_tasks_vacuum.analyze_all_tables_task',
        'schedule': crontab(minute=0),  # Every hour
        'kwargs': {'dry_run': False},
    },
    
    'vacuum-large-tables-weekly': {
        'task': 'api.celery_tasks_vacuum.vacuum_large_tables_task',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
        'kwargs': {'dry_run': False, 'size_threshold_mb': 1024},
    },
}
"""
