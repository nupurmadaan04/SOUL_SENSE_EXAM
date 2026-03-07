"""
Plugin Architecture Celery Tasks (#1441)

Background tasks for plugin operations including:
- Automated plugin activation
- Health monitoring
- Cleanup of old execution logs
- Plugin marketplace sync
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from ..utils.plugin_architecture import (
    get_plugin_manager,
    PluginManager,
    PluginStatus,
    PluginType,
)
from ..services.db_service import engine


logger = logging.getLogger("api.tasks.plugin")


# --- Plugin Lifecycle Tasks ---

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def auto_activate_pending_plugins(self) -> Dict[str, Any]:
    """
    Automatically activate pending plugins after validation.
    
    Returns:
        Activation summary
    """
    logger.info("Auto-activating pending plugins")
    
    async def _activate():
        manager = await get_plugin_manager(engine)
        
        pending = await manager.list_plugins(status=PluginStatus.PENDING)
        activated = []
        failed = []
        
        for plugin in pending:
            try:
                success = await manager.activate_plugin(plugin.plugin_id)
                if success:
                    activated.append({
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.manifest.name,
                    })
                else:
                    failed.append({
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.manifest.name,
                        "reason": "Activation failed",
                    })
            except Exception as e:
                logger.error(f"Failed to activate plugin {plugin.plugin_id}: {e}")
                failed.append({
                    "plugin_id": plugin.plugin_id,
                    "name": plugin.manifest.name,
                    "reason": str(e),
                })
        
        return {
            "status": "completed",
            "activated": len(activated),
            "failed": len(failed),
            "activated_plugins": activated,
            "failed_plugins": failed,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_activate())
    except Exception as exc:
        logger.error(f"Auto-activation failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "error": str(exc),
            }


# --- Monitoring Tasks ---

@shared_task
def check_plugin_health() -> Dict[str, Any]:
    """
    Check health of active plugins.
    
    Returns:
        Health status report
    """
    logger.info("Checking plugin health")
    
    async def _check():
        manager = await get_plugin_manager(engine)
        
        active_plugins = await manager.list_plugins(status=PluginStatus.ACTIVE)
        
        issues = []
        healthy_count = 0
        
        for plugin in active_plugins:
            # Check if plugin instance is loaded
            if not plugin.instance:
                issues.append({
                    "plugin_id": plugin.plugin_id,
                    "name": plugin.manifest.name,
                    "issue": "Instance not loaded",
                })
                continue
            
            # Check error rate
            total_exec = plugin.execution_count + plugin.error_count
            if total_exec > 0:
                error_rate = plugin.error_count / total_exec
                if error_rate > 0.5:  # More than 50% errors
                    issues.append({
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.manifest.name,
                        "issue": f"High error rate: {error_rate:.1%}",
                        "error_count": plugin.error_count,
                        "total_executions": total_exec,
                    })
                else:
                    healthy_count += 1
            else:
                healthy_count += 1
        
        return {
            "status": "healthy" if not issues else "issues_found",
            "total_active": len(active_plugins),
            "healthy": healthy_count,
            "issues_found": len(issues),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_check())
    except Exception as exc:
        return {
            "status": "unknown",
            "error": str(exc),
        }


@shared_task
def monitor_plugin_execution_logs() -> Dict[str, Any]:
    """
    Monitor plugin execution logs for anomalies.
    
    Returns:
        Monitoring summary
    """
    logger.info("Monitoring plugin execution logs")
    
    async def _monitor():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Recent failures (last hour)
            result = await session.execute(
                text("""
                    SELECT plugin_id, COUNT(*) as count
                    FROM plugin_execution_logs
                    WHERE success = FALSE
                    AND executed_at > NOW() - INTERVAL '1 hour'
                    GROUP BY plugin_id
                    HAVING COUNT(*) >= 5
                """)
            )
            failing_plugins = [
                {"plugin_id": r.plugin_id, "failures": r.count}
                for r in result
            ]
            
            # Slow executions (over 10 seconds)
            result = await session.execute(
                text("""
                    SELECT plugin_id, AVG(execution_time_ms) as avg_time
                    FROM plugin_execution_logs
                    WHERE executed_at > NOW() - INTERVAL '1 hour'
                    GROUP BY plugin_id
                    HAVING AVG(execution_time_ms) > 10000
                """)
            )
            slow_plugins = [
                {"plugin_id": r.plugin_id, "avg_time_ms": round(r.avg_time, 2)}
                for r in result
            ]
        
        return {
            "status": "completed",
            "failing_plugins": failing_plugins,
            "slow_plugins": slow_plugins,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_monitor())
    except Exception as exc:
        logger.error(f"Monitoring failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Reporting Tasks ---

@shared_task
def generate_daily_plugin_report() -> Dict[str, Any]:
    """
    Generate daily plugin usage report.
    
    Returns:
        Report data
    """
    logger.info("Generating daily plugin report")
    
    async def _generate():
        manager = await get_plugin_manager(engine)
        
        stats = await manager.get_statistics()
        
        # Get top plugins by execution
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        p.name,
                        COUNT(l.log_id) as executions,
                        SUM(CASE WHEN l.success THEN 1 ELSE 0 END) as successes,
                        AVG(l.execution_time_ms) as avg_time
                    FROM plugins p
                    LEFT JOIN plugin_execution_logs l ON p.plugin_id = l.plugin_id
                    WHERE l.executed_at > NOW() - INTERVAL '24 hours'
                    GROUP BY p.plugin_id, p.name
                    ORDER BY executions DESC
                    LIMIT 10
                """)
            )
            top_plugins = [
                {
                    "name": r.name,
                    "executions": r.executions,
                    "successes": r.successes,
                    "avg_time_ms": round(r.avg_time, 2) if r.avg_time else 0,
                }
                for r in result
            ]
        
        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "summary": stats,
            "top_plugins_24h": top_plugins,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Cleanup Tasks ---

@shared_task
def cleanup_old_execution_logs(retention_days: int = 90) -> Dict[str, Any]:
    """
    Clean up old plugin execution logs.
    
    Args:
        retention_days: Days to retain logs
        
    Returns:
        Cleanup summary
    """
    logger.info(f"Cleaning up execution logs older than {retention_days} days")
    
    async def _cleanup():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    DELETE FROM plugin_execution_logs
                    WHERE executed_at < NOW() - INTERVAL ':days days'
                    RETURNING COUNT(*)
                """),
                {"days": retention_days}
            )
            deleted = result.scalar()
            await session.commit()
        
        return {
            "status": "completed",
            "deleted_logs": deleted,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def archive_deprecated_plugins() -> Dict[str, Any]:
    """
    Archive deprecated plugins that haven't been used recently.
    
    Returns:
        Archival summary
    """
    logger.info("Archiving deprecated plugins")
    
    async def _archive():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Find deprecated plugins with no recent executions
            result = await session.execute(
                text("""
                    UPDATE plugins
                    SET status = 'uninstalled', updated_at = NOW()
                    WHERE status = 'deprecated'
                    AND plugin_id NOT IN (
                        SELECT DISTINCT plugin_id
                        FROM plugin_execution_logs
                        WHERE executed_at > NOW() - INTERVAL '30 days'
                    )
                    RETURNING plugin_id, name
                """)
            )
            archived = result.fetchall()
            await session.commit()
        
        return {
            "status": "completed",
            "archived_count": len(archived),
            "archived_plugins": [{"id": r.plugin_id, "name": r.name} for r in archived],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_archive())
    except Exception as exc:
        logger.error(f"Archival failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Security Tasks ---

@shared_task
def scan_plugin_security() -> Dict[str, Any]:
    """
    Scan plugins for security issues.
    
    Returns:
        Security scan results
    """
    logger.info("Scanning plugins for security issues")
    
    async def _scan():
        manager = await get_plugin_manager(engine)
        
        plugins = await manager.list_plugins()
        
        issues = []
        for plugin in plugins:
            # Check for suspicious permissions
            suspicious_perms = ["exec", "shell", "system", "eval"]
            for perm in plugin.manifest.permissions:
                if any(s in perm.lower() for s in suspicious_perms):
                    issues.append({
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.manifest.name,
                        "issue": f"Suspicious permission: {perm}",
                        "severity": "warning",
                    })
            
            # Check for outdated plugins
            if plugin.manifest.max_platform_version:
                from packaging import version
                try:
                    max_v = version.parse(plugin.manifest.max_platform_version)
                    current_v = version.parse(manager.PLATFORM_VERSION)
                    if current_v > max_v:
                        issues.append({
                            "plugin_id": plugin.plugin_id,
                            "name": plugin.manifest.name,
                            "issue": f"Plugin outdated for platform version {manager.PLATFORM_VERSION}",
                            "severity": "info",
                        })
                except Exception:
                    pass
        
        return {
            "status": "completed",
            "plugins_scanned": len(plugins),
            "issues_found": len(issues),
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_scan())
    except Exception as exc:
        logger.error(f"Security scan failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def verify_plugin_integrity() -> Dict[str, Any]:
    """
    Verify integrity of installed plugins.
    
    Returns:
        Verification results
    """
    logger.info("Verifying plugin integrity")
    
    async def _verify():
        manager = await get_plugin_manager(engine)
        
        plugins = await manager.list_plugins()
        
        mismatches = []
        for plugin in plugins:
            if plugin.source_path and plugin.hash_checksum:
                current_hash = manager._calculate_directory_hash(plugin.source_path)
                if current_hash != plugin.hash_checksum:
                    mismatches.append({
                        "plugin_id": plugin.plugin_id,
                        "name": plugin.manifest.name,
                        "expected_hash": plugin.hash_checksum,
                        "actual_hash": current_hash,
                    })
        
        return {
            "status": "completed",
            "plugins_verified": len(plugins),
            "mismatches_found": len(mismatches),
            "mismatches": mismatches,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_verify())
    except Exception as exc:
        logger.error(f"Integrity verification failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Maintenance Tasks ---

@shared_task
def reload_modified_plugins() -> Dict[str, Any]:
    """
    Reload plugins that have been modified on disk.
    
    Returns:
        Reload summary
    """
    logger.info("Checking for modified plugins")
    
    async def _reload():
        manager = await get_plugin_manager(engine)
        
        plugins = await manager.list_plugins(status=PluginStatus.ACTIVE)
        
        reloaded = []
        for plugin in plugins:
            if plugin.source_path:
                current_hash = manager._calculate_directory_hash(plugin.source_path)
                if current_hash != plugin.hash_checksum:
                    # Plugin modified, reload
                    try:
                        await manager.deactivate_plugin(plugin.plugin_id)
                        plugin.hash_checksum = current_hash
                        await manager.activate_plugin(plugin.plugin_id)
                        reloaded.append({
                            "plugin_id": plugin.plugin_id,
                            "name": plugin.manifest.name,
                        })
                    except Exception as e:
                        logger.error(f"Failed to reload plugin {plugin.plugin_id}: {e}")
        
        return {
            "status": "completed",
            "plugins_checked": len(plugins),
            "reloaded": reloaded,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_reload())
    except Exception as exc:
        logger.error(f"Reload failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Setup Task ---

@shared_task
def setup_plugin_schedules() -> Dict[str, Any]:
    """
    Setup periodic plugin maintenance schedules.
    
    Returns:
        Setup result
    """
    logger.info("Setting up plugin schedules")
    
    return {
        "status": "configured",
        "schedules": [
            {
                "task": "api.tasks.plugin_tasks.auto_activate_pending_plugins",
                "schedule": "every 5 minutes",
            },
            {
                "task": "api.tasks.plugin_tasks.check_plugin_health",
                "schedule": "every 15 minutes",
            },
            {
                "task": "api.tasks.plugin_tasks.monitor_plugin_execution_logs",
                "schedule": "every 30 minutes",
            },
            {
                "task": "api.tasks.plugin_tasks.generate_daily_plugin_report",
                "schedule": "daily at 9:00",
            },
            {
                "task": "api.tasks.plugin_tasks.scan_plugin_security",
                "schedule": "daily",
            },
            {
                "task": "api.tasks.plugin_tasks.verify_plugin_integrity",
                "schedule": "weekly",
            },
            {
                "task": "api.tasks.plugin_tasks.cleanup_old_execution_logs",
                "schedule": "weekly",
            },
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }
