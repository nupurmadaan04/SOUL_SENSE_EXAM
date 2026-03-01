import time
import logging
from typing import Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.network import get_real_ip
from ..services.quota_service import QuotaService
from ..services.db_service import AsyncSessionLocal
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class DynamicQuotaMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Dynamic Multi-Tenant Rate Limiting & Quota Management (#1135).
    Replaces static fixed-rate limits with a Dynamic Token Bucket algorithm.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/health") or not request.url.path.startswith("/api"):
            return await call_next(request)

        # 1. Extract context (tenant_id) — usually populated by RBAC middleware
        tenant_id = getattr(request.state, "tenant_id", None)
        
        # 2. Enforce Quota
        if tenant_id:
            try:
                # We need a DB session to check the quota record
                async with AsyncSessionLocal() as db:
                    allowed, status_data = await QuotaService.check_and_consume_quota(
                        db, tenant_id=tenant_id, tokens_requested=1
                    )
                    
                    if not allowed:
                        logger.warning(f"Quota exceeded for tenant {tenant_id}: {status_data.get('error')}")
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Rate limit or daily quota exceeded: {status_data.get('error')}"
                        )
                    
                    # Store usage for the response headers
                    request.state.quota_info = status_data
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"QuotaMiddleware error for tenant {tenant_id}: {e}", exc_info=True)
                # Fail-open for reliability, but log heavily
                return await call_next(request)
        else:
            # Fallback for anonymous or tenant-less requests (Legacy IP-based limiter)
            from ..middleware.rate_limiter import auth_limiter
            client_ip = get_real_ip(request)
            allowed, remaining = await auth_limiter.is_rate_limited(client_ip)
            if not allowed:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests from this IP")

        # 3. Process Request
        response: Response = await call_next(request)

        # 4. Append Quota Headers to Response
        quota_info = getattr(request.state, "quota_info", None)
        if quota_info:
            response.headers["X-Tenant-Tier"] = quota_info["tier"]
            response.headers["X-Quota-Remaining-Today"] = str(quota_info["daily_limit"] - quota_info["daily_count"])
            response.headers["X-RateLimit-Remaining"] = str(quota_info["tokens_remaining"])
            
            # Analytics Collector Integration: Feed real-time usage back to dashboard context
            # (In a real app, this could be a push to a websocket or analytics stream)
            logger.debug(f"[Analytics] Tenant {tenant_id} usage: {quota_info['daily_count']}/{quota_info['daily_limit']}")

        return response
