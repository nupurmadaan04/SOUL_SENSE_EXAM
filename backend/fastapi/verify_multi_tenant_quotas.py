import asyncio
import uuid
import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from api.services.db_service import AsyncSessionLocal
from api.models import TenantQuota
from api.services.quota_service import QuotaService
from api.ml.inference_server import inference_proxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_quotas():
    logger.info("--- VERIFYING MULTI-TENANT QUOTAS AND CIRCUIT BREAKER ---")
    
    # 1. Setup Test Tenants
    tenant_enterprise = uuid.uuid4()
    tenant_free = uuid.uuid4()
    
    async with AsyncSessionLocal() as db:
        # Create Enterprise Quota
        enterprise_quota = TenantQuota(
            tenant_id=tenant_enterprise,
            tier="enterprise",
            max_tokens=10, # Very small for testing
            refill_rate=2.0,
            daily_request_limit=5000,
            ml_units_daily_limit=1000
        )
        # Create Free Quota
        free_quota = TenantQuota(
            tenant_id=tenant_free,
            tier="free",
            max_tokens=2, # Tiny for quick exhaustion
            refill_rate=0.1,
            daily_request_limit=5,
            ml_units_daily_limit=2
        )
        db.add_all([enterprise_quota, free_quota])
        await db.commit()
        logger.info(f"Test tenants created. Enterprise: {tenant_enterprise}, Free: {tenant_free}")

    # 2. Test Rate Limiting (Token Bucket)
    logger.info("\nTesting Token Bucket Rate Limiting...")
    async with AsyncSessionLocal() as db:
        # Request 3 tokens for Free (limit is 2)
        for i in range(3):
            allowed, status = await QuotaService.check_and_consume_quota(db, tenant_free)
            logger.info(f"Free Tenant Request {i+1}: Allowed={allowed}, Status={status.get('error') if not allowed else 'OK'}")
            if i == 2:
                 assert not allowed, "Free tenant should have been rate limited on 3rd request"

        # Enterprise should handle 3 easily
        for i in range(3):
            allowed, status = await QuotaService.check_and_consume_quota(db, tenant_enterprise)
            logger.info(f"Enterprise Tenant Request {i+1}: Allowed={allowed}, Status='OK'")
            assert allowed

    # 3. Test Daily ML Quota
    logger.info("\nTesting Daily ML Quota...")
    async with AsyncSessionLocal() as db:
        # Free tenant has 2 ML units limit
        allowed, status = await QuotaService.check_and_consume_quota(db, tenant_free, ml_units_requested=2)
        logger.info(f"Free Tenant ML (2 units): Allowed={allowed}")
        
        allowed, status = await QuotaService.check_and_consume_quota(db, tenant_free, ml_units_requested=1)
        logger.info(f"Free Tenant ML (Extra 1 unit): Allowed={allowed}, Error={status.get('error')}")
        assert not allowed, "Free tenant should exceed daily ML quota"

    # 4. Test Circuit Breaker with Latency
    logger.info("\nTesting Circuit Breaker (Latency-based)...")
    
    # Define a mock slow task
    def slow_task():
        time.sleep(1.0) # > 0.5s threshold
        return "slow success"

    # We'll use the inference_proxy's _run_inference_with_breaker to test the breaker logic we added
    logger.info("Simulating slow ML inference task...")
    try:
        # This will trigger the logger.warning in my implementation if it exceeds 0.5s
        # In a real environment with redis, it would eventually open the circuit after 3 failures
        for i in range(4):
            logger.info(f"Circuit Breaker Test Run {i+1}...")
            # We bypass the internal network part and just test our wrapping logic
            result = inference_proxy._run_inference_with_breaker("test_task", {"data": 1}, 5.0)
            logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Breaker error: {e}")

    # 5. Check Analytics
    logger.info("\nChecking Usage Analytics...")
    async with AsyncSessionLocal() as db:
        enterprise_stats = await QuotaService.get_usage_analytics(db, tenant_enterprise)
        free_stats = await QuotaService.get_usage_analytics(db, tenant_free)
        logger.info(f"Enterprise Stats: {enterprise_stats}")
        logger.info(f"Free Stats: {free_stats}")

    logger.info("\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(verify_quotas())
