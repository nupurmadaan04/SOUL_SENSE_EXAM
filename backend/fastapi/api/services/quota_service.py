import logging
import json
import time
from datetime import datetime, timezone
UTC = timezone.utc
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..models import TenantQuota
from ..middleware.rate_limiter import TokenBucketLimiter

logger = logging.getLogger(__name__)

# Global limiter instance for quota management
quota_limiter = TokenBucketLimiter("quota", default_capacity=100, default_refill_rate=1.0)

class QuotaService:
    @staticmethod
    async def get_quota(db: AsyncSession, tenant_id: UUID) -> TenantQuota:
        """Fetch or create default quota for a tenant."""
        stmt = select(TenantQuota).filter(TenantQuota.tenant_id == tenant_id)
        result = await db.execute(stmt)
        quota = result.scalar_one_or_none()
        
        if not quota:
            # Create default 'free' tier quota
            quota = TenantQuota(
                tenant_id=tenant_id,
                tier="free",
                max_tokens=50,
                refill_rate=0.5,
                daily_request_limit=1000,
                ml_units_daily_limit=20
            )
            db.add(quota)
            await db.commit()
            await db.refresh(quota)
            
        return quota

    @staticmethod
    async def check_and_consume_quota(
        db: AsyncSession, 
        tenant_id: UUID, 
        tokens_requested: int = 1,
        ml_units_requested: int = 0
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Main entry point for multi-tenant rate limiting and quota management (#1135).
        Returns (allowed, quota_status)
        """
        quota = await QuotaService.get_quota(db, tenant_id)
        
        if not quota.is_active:
            return False, {"error": "Tenant account is inactive"}

        # 1. Check Rate Limit (Token Bucket)
        allowed, remaining = await quota_limiter.is_rate_limited(
            str(tenant_id), 
            capacity=quota.max_tokens, 
            refill_rate=quota.refill_rate
        )
        
        if not allowed:
            return False, {"error": "Rate limit exceeded (Token Bucket)"}

        # 2. Check Daily Request Quota
        now = datetime.now(UTC)
        if quota.last_reset_date.date() < now.date():
            # Reset daily counters if its a new day
            quota.daily_request_count = 0
            quota.ml_units_daily_count = 0
            quota.last_reset_date = now
        
        if quota.daily_request_count + tokens_requested > quota.daily_request_limit:
            return False, {"error": "Daily request quota exceeded"}
            
        if ml_units_requested > 0:
            if quota.ml_units_daily_count + ml_units_requested > quota.ml_units_daily_limit:
                 return False, {"error": "Daily ML compute quota exceeded"}

        # 3. Commit Consumption
        quota.daily_request_count += tokens_requested
        quota.ml_units_daily_count += ml_units_requested
        
        # We don't necessarily need to await commit here for every request if we use 
        # a more optimized approach (like Redis counters), but for strict accuracy 
        # in this demo/impl, we use the DB. 
        # Optimized alternative: Increment in Redis, sync to DB every 5 mins.
        await db.commit()
        
        # 4. Analytics: Feed back usage metadata
        quota_status = {
            "tier": quota.tier,
            "tokens_remaining": remaining,
            "daily_count": quota.daily_request_count,
            "daily_limit": quota.daily_request_limit,
            "ml_units_count": quota.ml_units_daily_count,
            "ml_units_limit": quota.ml_units_daily_limit
        }
        
        return True, quota_status

    @staticmethod
    async def get_usage_analytics(db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
        """Returns quota usage data for the dashboard (#1135)."""
        quota = await QuotaService.get_quota(db, tenant_id)
        return {
            "tenant_id": str(tenant_id),
            "tier": quota.tier,
            "usage_percentage": (quota.daily_request_count / quota.daily_request_limit) * 100 if quota.daily_request_limit > 0 else 0,
            "ml_usage_percentage": (quota.ml_units_daily_count / quota.ml_units_daily_limit) * 100 if quota.ml_units_daily_limit > 0 else 0,
            "is_throttled": not quota.is_active
        }
