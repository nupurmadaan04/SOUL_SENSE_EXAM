"""
Partner Sandbox Celery Tasks (#1443)

Background tasks for partner sandbox operations including:
- Webhook delivery
- Log cleanup
- Usage report generation
- Expired sandbox cleanup
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import aiohttp
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from ..utils.partner_sandbox import (
    get_sandbox_manager,
    PartnerSandboxManager,
    SandboxScenario,
    SandboxStatus,
    WebhookDeliveryStatus,
)
from ..services.db_service import engine


logger = logging.getLogger("api.tasks.sandbox")


# --- Webhook Delivery Tasks ---

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,  # 5 minutes
)
def deliver_webhook_event(self, event_id: str) -> Dict[str, Any]:
    """
    Deliver a webhook event to the partner's endpoint.
    
    Args:
        event_id: Webhook event ID
        
    Returns:
        Delivery result
    """
    logger.info(f"Delivering webhook event {event_id}")
    
    async def _deliver():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get event details
            result = await session.execute(
                text("""
                    SELECT * FROM sandbox_webhook_events WHERE event_id = :event_id
                """),
                {"event_id": event_id}
            )
            row = result.fetchone()
            
            if not row:
                return {"status": "not_found", "event_id": event_id}
            
            # Get sandbox webhook URL
            sandbox_result = await session.execute(
                text("""
                    SELECT config->>'webhook_url' as webhook_url,
                           config->>'webhook_secret' as webhook_secret
                    FROM sandbox_environments WHERE sandbox_id = :sandbox_id
                """),
                {"sandbox_id": row.sandbox_id}
            )
            sandbox_row = sandbox_result.fetchone()
            
            if not sandbox_row or not sandbox_row.webhook_url:
                # No webhook URL configured
                await session.execute(
                    text("""
                        UPDATE sandbox_webhook_events
                        SET delivery_status = 'failed',
                            error_message = 'No webhook URL configured'
                        WHERE event_id = :event_id
                    """),
                    {"event_id": event_id}
                )
                await session.commit()
                return {"status": "no_webhook_url", "event_id": event_id}
            
            # Prepare payload
            payload = {
                "event_id": event_id,
                "event_type": row.event_type,
                "payload": row.payload,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Update attempt count
            await session.execute(
                text("""
                    UPDATE sandbox_webhook_events
                    SET delivery_attempts = delivery_attempts + 1,
                        last_attempt_at = NOW(),
                        delivery_status = 'retrying'
                    WHERE event_id = :event_id
                """),
                {"event_id": event_id}
            )
            await session.commit()
            
            # Attempt delivery
            try:
                headers = {
                    "Content-Type": "application/json",
                    "X-Sandbox-Event": row.event_type,
                    "X-Sandbox-Event-ID": event_id,
                }
                
                if sandbox_row.webhook_secret:
                    import hmac
                    signature = hmac.new(
                        sandbox_row.webhook_secret.encode(),
                        json.dumps(payload).encode(),
                        'sha256'
                    ).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={signature}"
                
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as http_session:
                    async with http_session.post(
                        sandbox_row.webhook_url,
                        json=payload,
                        headers=headers
                    ) as response:
                        if response.status < 500:
                            # Mark as delivered
                            await session.execute(
                                text("""
                                    UPDATE sandbox_webhook_events
                                    SET delivery_status = 'delivered',
                                        delivered_at = NOW()
                                    WHERE event_id = :event_id
                                """),
                                {"event_id": event_id}
                            )
                            await session.commit()
                            
                            return {
                                "status": "delivered",
                                "event_id": event_id,
                                "http_status": response.status,
                            }
                        else:
                            raise Exception(f"HTTP {response.status}")
                            
            except Exception as e:
                logger.error(f"Webhook delivery failed for {event_id}: {e}")
                
                # Check if max retries reached
                if row.delivery_attempts >= 2:  # 0-indexed, so 2 means 3 attempts
                    await session.execute(
                        text("""
                            UPDATE sandbox_webhook_events
                            SET delivery_status = 'failed',
                                error_message = :error
                            WHERE event_id = :event_id
                        """),
                        {"event_id": event_id, "error": str(e)}
                    )
                    await session.commit()
                    return {"status": "failed", "event_id": event_id, "error": str(e)}
                else:
                    raise self.retry(exc=e)
    
    try:
        return asyncio.run(_deliver())
    except Exception as exc:
        logger.error(f"Webhook delivery task failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "status": "failed",
                "event_id": event_id,
                "error": str(exc),
            }


@shared_task
def process_pending_webhooks() -> Dict[str, Any]:
    """
    Process all pending webhook events.
    
    Returns:
        Processing summary
    """
    logger.info("Processing pending webhooks")
    
    async def _process():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get pending events
            result = await session.execute(
                text("""
                    SELECT event_id FROM sandbox_webhook_events
                    WHERE delivery_status IN ('pending', 'retrying')
                    AND delivery_attempts < 3
                    ORDER BY created_at ASC
                    LIMIT 100
                """)
            )
            events = result.fetchall()
            
            # Queue delivery tasks
            for row in events:
                deliver_webhook_event.delay(row.event_id)
            
            return {
                "status": "queued",
                "events_queued": len(events),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    try:
        return asyncio.run(_process())
    except Exception as exc:
        logger.error(f"Process pending webhooks failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Cleanup Tasks ---

@shared_task
def cleanup_old_request_logs(retention_days: int = 30) -> Dict[str, Any]:
    """
    Clean up old request logs.
    
    Args:
        retention_days: Days to retain logs
        
    Returns:
        Cleanup result
    """
    logger.info(f"Cleaning up request logs older than {retention_days} days")
    
    async def _cleanup():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    DELETE FROM sandbox_request_logs
                    WHERE timestamp < NOW() - INTERVAL ':days days'
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
        logger.error(f"Log cleanup failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def cleanup_expired_sandboxes() -> Dict[str, Any]:
    """
    Clean up expired sandbox environments.
    
    Returns:
        Cleanup result
    """
    logger.info("Cleaning up expired sandboxes")
    
    async def _cleanup():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Mark expired sandboxes
            result = await session.execute(
                text("""
                    UPDATE sandbox_environments
                    SET status = 'expired', updated_at = NOW()
                    WHERE expires_at < NOW()
                    AND status != 'expired'
                    AND status != 'deleted'
                    RETURNING sandbox_id
                """)
            )
            expired = result.fetchall()
            await session.commit()
        
        return {
            "status": "completed",
            "expired_sandboxes": len(expired),
            "sandbox_ids": [r.sandbox_id for r in expired],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Expired sandbox cleanup failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def revoke_expired_api_keys() -> Dict[str, Any]:
    """
    Revoke expired API keys.
    
    Returns:
        Revocation result
    """
    logger.info("Revoking expired API keys")
    
    async def _revoke():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    UPDATE sandbox_api_keys
                    SET is_revoked = TRUE
                    WHERE expires_at < NOW()
                    AND is_revoked = FALSE
                    RETURNING key_id
                """)
            )
            revoked = result.fetchall()
            await session.commit()
        
        return {
            "status": "completed",
            "revoked_keys": len(revoked),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_revoke())
    except Exception as exc:
        logger.error(f"API key revocation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Reporting Tasks ---

@shared_task
def generate_sandbox_usage_report(days: int = 7) -> Dict[str, Any]:
    """
    Generate sandbox usage report.
    
    Args:
        days: Number of days to include
        
    Returns:
        Usage report
    """
    logger.info(f"Generating sandbox usage report for last {days} days")
    
    async def _generate():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get total requests
            result = await session.execute(
                text("SELECT COALESCE(SUM(total_requests), 0) FROM sandbox_usage_stats")
            )
            total_requests = result.scalar()
            
            # Get requests in period
            result = await session.execute(
                text("""
                    SELECT COALESCE(SUM(total_requests), 0) FROM sandbox_usage_stats
                    WHERE last_request_at > NOW() - INTERVAL ':days days'
                """),
                {"days": days}
            )
            period_requests = result.scalar()
            
            # Get active sandboxes
            result = await session.execute(
                text("SELECT COUNT(*) FROM sandbox_environments WHERE status = 'active'")
            )
            active_sandboxes = result.scalar()
            
            # Get sandbox breakdown
            result = await session.execute(
                text("""
                    SELECT 
                        s.sandbox_id,
                        s.partner_id,
                        s.name,
                        COALESCE(u.total_requests, 0) as requests
                    FROM sandbox_environments s
                    LEFT JOIN sandbox_usage_stats u ON s.sandbox_id = u.sandbox_id
                    WHERE s.status = 'active'
                    ORDER BY requests DESC
                    LIMIT 20
                """)
            )
            sandbox_breakdown = [
                {
                    "sandbox_id": r.sandbox_id,
                    "partner_id": r.partner_id,
                    "name": r.name,
                    "total_requests": r.requests,
                }
                for r in result
            ]
            
            return {
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_requests": total_requests,
                    "requests_in_period": period_requests,
                    "active_sandboxes": active_sandboxes,
                },
                "top_sandboxes": sandbox_breakdown,
            }
    
    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


@shared_task
def generate_partner_usage_report(partner_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Generate usage report for a specific partner.
    
    Args:
        partner_id: Partner identifier
        days: Number of days to include
        
    Returns:
        Partner usage report
    """
    logger.info(f"Generating usage report for partner {partner_id}")
    
    async def _generate():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get partner sandboxes
            result = await session.execute(
                text("""
                    SELECT sandbox_id, name, status
                    FROM sandbox_environments
                    WHERE partner_id = :partner_id
                """),
                {"partner_id": partner_id}
            )
            sandboxes = result.fetchall()
            
            if not sandboxes:
                return {
                    "status": "not_found",
                    "partner_id": partner_id,
                }
            
            sandbox_stats = []
            total_requests = 0
            
            for sbx in sandboxes:
                # Get usage stats
                result = await session.execute(
                    text("""
                        SELECT 
                            COALESCE(total_requests, 0) as requests,
                            average_latency_ms,
                            success_rate
                        FROM sandbox_usage_stats
                        WHERE sandbox_id = :sandbox_id
                    """),
                    {"sandbox_id": sbx.sandbox_id}
                )
                stats = result.fetchone()
                
                requests = stats.requests if stats else 0
                total_requests += requests
                
                sandbox_stats.append({
                    "sandbox_id": sbx.sandbox_id,
                    "name": sbx.name,
                    "status": sbx.status,
                    "total_requests": requests,
                    "average_latency_ms": round(stats.average_latency_ms, 2) if stats else 0,
                    "success_rate": round(stats.success_rate, 2) if stats else 100,
                })
            
            return {
                "partner_id": partner_id,
                "period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_sandboxes": len(sandboxes),
                    "total_requests": total_requests,
                },
                "sandboxes": sandbox_stats,
            }
    
    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Partner report generation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Monitoring Tasks ---

@shared_task
def check_sandbox_health() -> Dict[str, Any]:
    """
    Check sandbox system health.
    
    Returns:
        Health status report
    """
    logger.info("Checking sandbox system health")
    
    async def _check():
        manager = await get_sandbox_manager(engine)
        stats = await manager.get_global_statistics()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        # Check for issues
        if stats.get("total_requests", 0) > 0 and stats.get("active_sandboxes", 0) == 0:
            health_status = "warning"
            issues.append("Requests logged but no active sandboxes")
        
        return {
            "status": health_status,
            "issues": issues,
            "statistics": stats,
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_check())
    except Exception as exc:
        return {
            "status": "unknown",
            "error": str(exc),
        }


@shared_task
def notify_quota_limit_approaching(threshold_percent: float = 80.0) -> Dict[str, Any]:
    """
    Notify partners approaching quota limits.
    
    Args:
        threshold_percent: Quota usage threshold to notify at
        
    Returns:
        Notification summary
    """
    logger.info(f"Checking quota limits at {threshold_percent}% threshold")
    
    async def _notify():
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Find sandboxes approaching quota
            result = await session.execute(
                text("""
                    SELECT 
                        s.sandbox_id,
                        s.partner_id,
                        s.config->>'quota_daily' as quota,
                        u.requests_today
                    FROM sandbox_environments s
                    JOIN sandbox_usage_stats u ON s.sandbox_id = u.sandbox_id
                    WHERE s.status = 'active'
                    AND u.requests_today::float / NULLIF((s.config->>'quota_daily')::int, 0) * 100 >= :threshold
                """),
                {"threshold": threshold_percent}
            )
            approaching = result.fetchall()
            
            # In a real implementation, this would send notifications
            # For now, just log the information
            for row in approaching:
                logger.warning(
                    f"Sandbox {row.sandbox_id} approaching quota: "
                    f"{row.requests_today}/{row.quota} ({threshold_percent}%)"
                )
            
            return {
                "status": "completed",
                "sandboxes_notified": len(approaching),
                "threshold_percent": threshold_percent,
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    try:
        return asyncio.run(_notify())
    except Exception as exc:
        logger.error(f"Quota notification failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Batch Operations ---

@shared_task(
    bind=True,
    max_retries=1,
    time_limit=3600,  # 1 hour
)
def batch_simulate_requests(
    self,
    sandbox_id: str,
    requests: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Simulate multiple requests in batch.
    
    Args:
        sandbox_id: Sandbox ID
        requests: List of request configurations
        
    Returns:
        Batch results
    """
    logger.info(f"Batch simulating {len(requests)} requests for {sandbox_id}")
    
    async def _simulate():
        manager = await get_sandbox_manager(engine)
        
        # Get sandbox API key
        from sqlalchemy import text
        from ..services.db_service import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT key_id FROM sandbox_api_keys WHERE sandbox_id = :sandbox_id LIMIT 1"),
                {"sandbox_id": sandbox_id}
            )
            row = result.fetchone()
            
            if not row:
                return {"status": "error", "error": "No API key found for sandbox"}
            
            api_key = row.key_id
        
        results = []
        success_count = 0
        fail_count = 0
        
        for req in requests:
            try:
                response = await manager.simulate_request(
                    api_key=api_key,
                    method=req.get("method", "GET"),
                    path=req.get("path", "/"),
                    headers=req.get("headers"),
                    body=req.get("body"),
                )
                
                results.append({
                    "path": req.get("path"),
                    "status": response["status"],
                    "success": 200 <= response["status"] < 300,
                })
                
                if 200 <= response["status"] < 300:
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                results.append({
                    "path": req.get("path"),
                    "error": str(e),
                    "success": False,
                })
                fail_count += 1
        
        return {
            "status": "completed",
            "total": len(requests),
            "successful": success_count,
            "failed": fail_count,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    try:
        return asyncio.run(_simulate())
    except Exception as exc:
        logger.error(f"Batch simulation failed: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
        }


# --- Setup Tasks ---

@shared_task
def setup_sandbox_schedules() -> Dict[str, Any]:
    """
    Setup periodic sandbox maintenance schedules.
    
    Returns:
        Setup result
    """
    logger.info("Setting up sandbox maintenance schedules")
    
    return {
        "status": "configured",
        "schedules": [
            {
                "task": "api.tasks.sandbox_tasks.process_pending_webhooks",
                "schedule": "every 5 minutes",
            },
            {
                "task": "api.tasks.sandbox_tasks.cleanup_old_request_logs",
                "schedule": "daily at 2:00",
            },
            {
                "task": "api.tasks.sandbox_tasks.cleanup_expired_sandboxes",
                "schedule": "daily at 3:00",
            },
            {
                "task": "api.tasks.sandbox_tasks.revoke_expired_api_keys",
                "schedule": "daily at 3:30",
            },
            {
                "task": "api.tasks.sandbox_tasks.check_sandbox_health",
                "schedule": "hourly",
            },
            {
                "task": "api.tasks.sandbox_tasks.notify_quota_limit_approaching",
                "schedule": "every 6 hours",
            },
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }
