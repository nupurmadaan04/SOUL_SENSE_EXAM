"""
Enhanced Bloom Filter Service with False Positive Rate Control
Addresses Issue #1194: Bloom Filter False Positive Storm
"""

import logging
import math
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models import TokenRevocation

logger = logging.getLogger(__name__)


class BloomFilterParameters:
    """Calculate optimal Bloom Filter parameters"""
    
    def __init__(self, expected_elements: int = 1000, false_positive_rate: float = 0.001):
        """
        Calculate Bloom Filter parameters using standard formulas.
        
        Args:
            expected_elements: Expected number of elements to store
            false_positive_rate: Target false positive rate (default: 0.1%)
        """
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        self.filter_size = self._calculate_filter_size()
        self.hash_functions = self._calculate_hash_functions()
    
    def _calculate_filter_size(self) -> int:
        """
        Calculate optimal filter size (m).
        Formula: m = -1 / ln(2)^2 * n * ln(p)
        where n = expected_elements, p = false_positive_rate
        """
        numerator = -self.expected_elements * math.log(self.false_positive_rate)
        denominator = math.log(2) ** 2
        m = int(numerator / denominator)
        # Ensure at least 1024 bits
        return max(m, 1024)
    
    def _calculate_hash_functions(self) -> int:
        """
        Calculate optimal number of hash functions (k).
        Formula: k = (m / n) * ln(2)
        """
        k = int((self.filter_size / self.expected_elements) * math.log(2))
        # Ensure at least 1 and at most 16 hash functions
        return max(1, min(k, 16))


class BloomFilterMonitor:
    """Monitor Bloom Filter false positive rate and health"""
    
    def __init__(self):
        self.total_checks = 0
        self.false_positives = 0
        self.lookups_since_rebuild = 0
        self.fp_rate_threshold = 0.01  # 1% threshold
        self.last_rebuild = datetime.now(timezone.utc)
        self.needs_rebuild = False
    
    def record_check(self, was_positive: bool, actual_revoked: bool) -> None:
        """Record a bloom filter lookup result"""
        self.total_checks += 1
        self.lookups_since_rebuild += 1
        
        # False positive: BF says positive but actually not revoked
        if was_positive and not actual_revoked:
            self.false_positives += 1
            logger.warning(
                f"Bloom Filter false positive detected. "
                f"Current FP rate: {self.get_fp_rate():.4f} ({self.false_positives}/{self.total_checks})"
            )
    
    def get_fp_rate(self) -> float:
        """Get current false positive rate"""
        if self.total_checks == 0:
            return 0.0
        return self.false_positives / self.total_checks
    
    def should_rebuild(self) -> bool:
        """Check if filter should be rebuilt"""
        if self.get_fp_rate() > self.fp_rate_threshold:
            logger.error(
                f"Bloom Filter FP rate {self.get_fp_rate():.4f} exceeds threshold "
                f"{self.fp_rate_threshold}. Rebuild recommended."
            )
            self.needs_rebuild = True
            return True
        return self.needs_rebuild
    
    def reset(self) -> None:
        """Reset monitoring stats after rebuild"""
        self.total_checks = 0
        self.false_positives = 0
        self.lookups_since_rebuild = 0
        self.last_rebuild = datetime.now(timezone.utc)
        self.needs_rebuild = False


class BloomFilterService:
    """Enhanced Bloom Filter service with FP rate control"""
    
    def __init__(self):
        self.settings = None
        self.redis = None
        self.bloom_key = "token_revocation_bloom"
        self.params = BloomFilterParameters(expected_elements=5000, false_positive_rate=0.001)
        self.monitor = BloomFilterMonitor()
    
    async def _get_redis(self):
        """Get Redis connection"""
        if self.redis:
            return self.redis
        try:
            from ..main import app
            self.redis = getattr(app.state, 'redis_client', None)
        except Exception:
            pass
        return self.redis
    
    async def check_bloom_filter(self, token_jti: str) -> Tuple[bool, bool]:
        """
        Check if token might be revoked using Bloom Filter.
        
        Returns:
            (would_be_positive, is_definitely_not_revoked)
            - would_be_positive: BF says token might be revoked
            - is_definitely_not_revoked: If True, token definitely NOT revoked (fast path)
        """
        redis = await self._get_redis()
        if not redis:
            logger.debug("Redis not available for Bloom Filter check")
            return False, False  # Default to checking SQL
        
        try:
            # Try RedisBloom module first (optimized)
            exists = await redis.execute_command("BF.EXISTS", self.bloom_key, token_jti)
            
            if exists == 0:
                # Definitely not in filter = definitely not revoked (fast path)
                return False, True
            
            # exists == 1: Might be in filter (could be false positive)
            return True, False
            
        except Exception as e:
            logger.warning(f"RedisBloom check failed: {e}. Falling back to Redis Set.")
            
            # Fallback to standard Redis Set
            try:
                is_member = await redis.sismember(self.bloom_key + ":set", token_jti)
                if is_member:
                    return True, False
                return False, True
            except Exception as e2:
                logger.error(f"Redis Set check also failed: {e2}")
                return False, False
    
    async def add_to_bloom_filter(self, token_jti: str) -> None:
        """Add token JTI to Bloom Filter"""
        redis = await self._get_redis()
        if not redis:
            logger.warning("Redis not available for adding to Bloom Filter")
            return
        
        try:
            await redis.execute_command("BF.ADD", self.bloom_key, token_jti)
            logger.debug(f"Token {token_jti[:8]}... added to Bloom Filter")
        except Exception as e:
            logger.warning(f"RedisBloom BF.ADD failed: {e}. Using Redis Set fallback.")
            try:
                await redis.sadd(self.bloom_key + ":set", token_jti)
                await redis.expire(self.bloom_key + ":set", 86400)  # 24h TTL
            except Exception as e2:
                logger.error(f"Redis Set add also failed: {e2}")
    
    async def get_stats(self) -> dict:
        """Get Bloom Filter statistics"""
        return {
            "total_checks": self.monitor.total_checks,
            "false_positives": self.monitor.false_positives,
            "fp_rate": self.monitor.get_fp_rate(),
            "filter_size_bits": self.params.filter_size,
            "hash_functions": self.params.hash_functions,
            "expected_elements": self.params.expected_elements,
            "needs_rebuild": self.monitor.needs_rebuild,
            "last_rebuild": self.monitor.last_rebuild.isoformat()
        }


# Singleton instance
bloom_filter_service = BloomFilterService()
