import logging
import json
import time
from datetime import datetime, UTC
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..models import TenantQuota, TenantUsageReadModel
from ..middleware.rate_limiter import TokenBucketLimiter

logger = logging.getLogger(__name__)

# Global limiter instance for burst rate limiting
quota_limiter = TokenBucketLimiter("quota", default_capacity=100, default_refill_rate=1.0)

class QuotaService:
    @staticmethod
    def _get_redis():
        """Helper to get the global redis client."""
        try:
            from ..main import app
            return getattr(app.state, 'redis_client', None)
        except:
            return None

    @staticmethod
    async def get_quota(db: AsyncSession, tenant_id: UUID) -> TenantQuota:
        """Fetch or create default quota for a tenant."""
        stmt = select(TenantQuota).filter(TenantQuota.tenant_id == tenant_id)
        result = await db.execute(stmt)
        quota = result.scalar_one_or_none()
        
        if not quota:
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
        Optimized Multi-Tenant Quota & Analytics Enforcement (#1135).
        Uses Redis for high-speed counter validation + CQRS Read Model for Dashboard.
        """
        quota = await QuotaService.get_quota(db, tenant_id)
        if not quota.is_active:
            return False, {"error": "Tenant account is inactive"}

        # 1. Burst Rate Limit (Token Bucket)
        allowed, remaining = await quota_limiter.is_rate_limited(
            str(tenant_id), 
            capacity=quota.max_tokens, 
            refill_rate=quota.refill_rate
        )
        if not allowed:
            return False, {"error": "Rate limit exceeded (Token Bucket)"}

        # 2. Daily Quota Check (Redis-backed for high performance)
        redis = QuotaService._get_redis()
        today_key = f"quota:usage:{tenant_id}:{datetime.now(UTC).date().isoformat()}"
        
        if redis:
            # Increment and check against limits in a single atomic pipeline
            pipe = redis.pipeline()
            pipe.incrby(f"{today_key}:requests", tokens_requested)
            pipe.incrby(f"{today_key}:ml_units", ml_units_requested)
            pipe.expire(f"{today_key}:requests", 86400) # 24h TTL
            pipe.expire(f"{today_key}:ml_units", 86400)
            counts = await pipe.execute()
            
            daily_req_count = counts[0]
            daily_ml_count = counts[1]
        else:
            # Fallback to DB if Redis is down (Legacy/Reliability path)
            quota.daily_request_count += tokens_requested
            quota.ml_units_daily_count += ml_units_requested
            await db.commit()
            daily_req_count = quota.daily_request_count
            daily_ml_count = quota.ml_units_daily_count

        if daily_req_count > quota.daily_request_limit:
            return False, {"error": "Daily request quota exceeded"}
        if daily_ml_count > quota.ml_units_daily_limit:
            return False, {"error": "Daily ML compute quota exceeded"}

        # 3. CQRS Projection: Update Dashboard Read Model (Fire and Forget)
        try:
            usage_pct = (daily_req_count / quota.daily_request_limit) * 100
            read_model_stmt = select(TenantUsageReadModel).filter(TenantUsageReadModel.tenant_id == tenant_id)
            read_model = (await db.execute(read_model_stmt)).scalar_one_or_none()
            
            if not read_model:
                read_model = TenantUsageReadModel(tenant_id=tenant_id, tier=quota.tier)
                db.add(read_model)
            
            read_model.total_requests_today = daily_req_count
            read_model.total_ml_units_today = daily_ml_count
            read_model.usage_percentage = usage_pct
            await db.commit()
        except Exception as e:
            logger.error(f"CQRS Projection failed for tenant {tenant_id}: {e}")

        return True, {
            "tier": quota.tier,
            "tokens_remaining": remaining,
            "daily_count": daily_req_count,
            "daily_limit": quota.daily_request_limit,
            "ml_units_count": daily_ml_count,
            "ml_units_limit": quota.ml_units_daily_limit
        }

    @staticmethod
    async def get_usage_analytics(db: AsyncSession, tenant_id: UUID) -> Dict[str, Any]:
        """Returns quota usage data from the CQRS Read Model (#1135)."""
        stmt = select(TenantUsageReadModel).filter(TenantUsageReadModel.tenant_id == tenant_id)
        result = await db.execute(stmt)
        usage = result.scalar_one_or_none()
        
        if not usage:
            return {"error": "Analytics not found for tenant"}
            
        return {
            "tenant_id": str(tenant_id),
            "tier": usage.tier,
            "usage_percentage": usage.usage_percentage,
            "total_requests": usage.total_requests_today,
            "ml_units_consumed": usage.total_ml_units_today,
            "last_updated": usage.last_updated_at
        }
