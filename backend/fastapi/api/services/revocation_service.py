import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete
from ..models import TokenRevocation
from ..config import get_settings_instance
from .bloom_filter_service import bloom_filter_service

logger = logging.getLogger(__name__)

class RevocationService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.redis = None

    async def _get_redis(self):
        if self.redis:
            return self.redis
        try:
            from ..main import app
            self.redis = getattr(app.state, 'redis_client', None)
        except Exception:
            pass
        return self.redis

    async def revoke_token(self, jti: str, expires_at: datetime, db: AsyncSession):
        """Revoke a token by adding it to the Bloom Filter and the database."""
        # 1. Add to SQL (Source of Truth)
        revocation = TokenRevocation(
            token_str=jti,
            expires_at=expires_at,
            revoked_at=datetime.now(timezone.utc)
        )
        db.add(revocation)
        await db.commit()

        # 2. Add to Bloom Filter (Fast negative cache)
        await bloom_filter_service.add_to_bloom_filter(jti)
        logger.info(f"Token {jti[:8]}... revoked and added to Bloom Filter")

    async def is_revoked(self, jti: str, db: AsyncSession) -> bool:
        """
        Check if a token is revoked using multi-layer validation.
        
        Layer 1: Fast positive cache (Bloom Filter) - may have false positives
        Layer 2: SQL verification (handles false positives)
        """
        # Layer 1: Fast path - Bloom Filter check
        bf_positive, is_definitely_not_revoked = await bloom_filter_service.check_bloom_filter(jti)
        
        # Fast exit: Definitely not in revocation list
        if is_definitely_not_revoked:
            return False
        
        # Layer 2: Slow path - SQL verification (handles false positives)
        stmt = select(TokenRevocation).filter(TokenRevocation.token_str == jti)
        result = await db.execute(stmt)
        is_actually_revoked = result.scalar_one_or_none() is not None
        
        # Record monitoring data for false positive rate tracking
        if bf_positive and not is_actually_revoked:
            bloom_filter_service.monitor.record_check(was_positive=True, actual_revoked=False)
            logger.warning(
                f"Bloom Filter false positive detected for token {jti[:8]}... "
                f"Current FP rate: {bloom_filter_service.monitor.get_fp_rate():.4f}"
            )
        elif bf_positive and is_actually_revoked:
            bloom_filter_service.monitor.record_check(was_positive=True, actual_revoked=True)
        
        return is_actually_revoked

    async def cleanup_expired_tokens(self, db: AsyncSession):
        """Remove expired tokens from the revocation list."""
        now = datetime.now(timezone.utc)
        stmt = delete(TokenRevocation).where(TokenRevocation.expires_at < now)
        await db.execute(stmt)
        await db.commit()
        logger.info("Expired tokens cleaned up from revocation list")


# Singleton instance
revocation_service = RevocationService()
