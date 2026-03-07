"""
Celery Background Tasks for Orphan Scanner (#1414)

Provides automated background scanning and cleanup of orphaned records.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from .celery_app import celery_app

logger = logging.getLogger("api.celery_tasks.orphan_scanner")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def scan_table_for_orphans_task(
    self,
    table_name: str,
    foreign_key_column: str,
    referenced_table: str,
    strategy: str = "not_exists"
) -> Dict[str, Any]:
    """
    Scan a specific table for orphaned records.
    
    Args:
        table_name: Table to scan
        foreign_key_column: FK column to check
        referenced_table: Parent table name
        strategy: Scan strategy
        
    Returns:
        Dictionary with scan results
    """
    async def _execute():
        from api.utils.orphan_scanner import get_orphan_scanner, ScanStrategy
        
        scanner = await get_orphan_scanner()
        
        scan_strategy = ScanStrategy(strategy)
        
        result = await scanner.scan_table(
            table_name=table_name,
            foreign_key_column=foreign_key_column,
            referenced_table=referenced_table,
            strategy=scan_strategy,
        )
        
        return result.to_dict()
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"Orphan scan failed for {table_name}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=600)
def run_full_orphan_scan_task(
    self,
    tables: Optional[List[str]] = None,
    strategy: str = "not_exists"
) -> Dict[str, Any]:
    """
    Run full database scan for orphaned records.
    
    This task is designed to run on a schedule (e.g., weekly) to
    automatically detect orphaned records.
    
    Args:
        tables: Specific tables to scan (None = all)
        strategy: Scan strategy
        
    Returns:
        Dictionary with scan report
    """
    async def _execute():
        from api.utils.orphan_scanner import get_orphan_scanner, ScanStrategy
        
        scanner = await get_orphan_scanner()
        
        scan_strategy = ScanStrategy(strategy)
        
        report = await scanner.scan_all(tables=tables, strategy=scan_strategy)
        
        return report.to_dict()
    
    try:
        report = asyncio.run(_execute())
        
        # Log summary
        total_orphans = report.get("total_orphans_found", 0)
        integrity_score = report.get("integrity_score", 100.0)
        
        logger.info(
            f"Full orphan scan completed: "
            f"tables={report.get('tables_scanned')}, "
            f"orphans={total_orphans}, "
            f"integrity_score={integrity_score:.1f}%"
        )
        
        # Alert if orphans found
        if total_orphans > 0:
            logger.warning(
                f"ALERT: Found {total_orphans} orphaned records across database"
            )
        
        return {
            "success": True,
            "tables_scanned": report.get("tables_scanned"),
            "relationships_checked": report.get("relationships_checked"),
            "total_orphans_found": total_orphans,
            "integrity_score": integrity_score,
            "details": report,
        }
        
    except Exception as exc:
        logger.error(f"Full orphan scan failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def cleanup_orphans_task(
    self,
    table_name: str,
    foreign_key_column: str,
    referenced_table: str,
    strategy: str = "report_only",
    dry_run: bool = True,
    batch_size: int = 1000
) -> Dict[str, Any]:
    """
    Clean up orphaned records for a specific relationship.
    
    Args:
        table_name: Table to clean
        foreign_key_column: FK column
        referenced_table: Parent table
        strategy: Cleanup strategy
        dry_run: If True, only simulate
        batch_size: Rows per batch
        
    Returns:
        Dictionary with cleanup results
    """
    async def _execute():
        from api.utils.orphan_scanner import get_orphan_scanner, CleanupStrategy
        
        scanner = await get_orphan_scanner()
        
        cleanup_strategy = CleanupStrategy(strategy)
        
        result = await scanner.cleanup_orphans(
            table_name=table_name,
            foreign_key_column=foreign_key_column,
            referenced_table=referenced_table,
            strategy=cleanup_strategy,
            dry_run=dry_run,
            batch_size=batch_size,
            create_backup=True,
        )
        
        return result.to_dict()
    
    try:
        result = asyncio.run(_execute())
        
        logger.info(
            f"Orphan cleanup completed for {table_name}: "
            f"found={result.get('orphans_found')}, "
            f"processed={result.get('orphans_processed')}, "
            f"dry_run={result.get('dry_run')}"
        )
        
        return result
        
    except Exception as exc:
        logger.error(f"Orphan cleanup failed for {table_name}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=600)
def auto_cleanup_known_orphans_task(self) -> Dict[str, Any]:
    """
    Automatically clean up known orphan patterns.
    
    This task runs cleanup on tables known to accumulate orphans,
    using the safest strategies (soft delete or report only).
    
    Returns:
        Dictionary with results for each table
    """
    async def _execute():
        from api.utils.orphan_scanner import (
            get_orphan_scanner,
            CleanupStrategy,
            ScanResult
        )
        
        scanner = await get_orphan_scanner()
        
        # First scan all
        report = await scanner.scan_all()
        
        results = {}
        
        # For tables with orphans, attempt safe cleanup
        for scan_result in report.table_results:
            if scan_result.has_orphans:
                # Choose safest strategy based on table structure
                if scan_result.table_name in ["notification_logs", "audit_logs"]:
                    strategy = CleanupStrategy.SOFT_DELETE
                else:
                    strategy = CleanupStrategy.REPORT_ONLY
                
                # Run cleanup in dry-run first
                dry_run_result = await scanner.cleanup_orphans(
                    table_name=scan_result.table_name,
                    foreign_key_column=scan_result.foreign_key_column,
                    referenced_table=scan_result.referenced_table,
                    strategy=strategy,
                    dry_run=True,
                )
                
                results[scan_result.table_name] = {
                    "scan": scan_result.to_dict(),
                    "cleanup_preview": dry_run_result.to_dict(),
                }
        
        return {
            "tables_with_orphans": len(results),
            "total_orphans": report.total_orphans_found,
            "results": results,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"Auto cleanup task failed: {exc}")
        raise self.retry(exc=exc)


# Schedule configuration (to be added to Celery beat schedule)
"""
CELERY_BEAT_SCHEDULE = {
    # ... existing schedules ...
    
    'orphan-scan-weekly': {
        'task': 'api.celery_tasks_orphan_scanner.run_full_orphan_scan_task',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
        'kwargs': {'strategy': 'not_exists'},
    },
    
    'orphan-auto-cleanup-daily': {
        'task': 'api.celery_tasks_orphan_scanner.auto_cleanup_known_orphans_task',
        'schedule': crontab(hour=4, minute=0),
    },
}
"""
