"""
JWT Blacklist Management

Redis-backed JWT token blacklist for immediate token invalidation on logout.
"""

import logging
import redis.asyncio as redis
from typing import Optional
from datetime import datetime, timezone
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

class JWTBlacklist:
    """
    Redis-backed JWT token blacklist for immediate token invalidation.

    Stores token JTI (JWT ID) with TTL based on token expiry time.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.key_prefix = "jwt_blacklist:"

    async def blacklist_token(self, token: str) -> bool:
        """
        Add a JWT token to the blacklist.

        Extracts JTI and expiry time from token, stores in Redis with TTL.

        Args:
            token: The JWT token to blacklist

        Returns:
            bool: True if successfully blacklisted, False otherwise
        """
        try:
            # Decode token without verification to extract claims
            # We don't verify signature here since we're just extracting claims
            header = jwt.get_unverified_header(token)
            payload = jwt.get_unverified_claims(token)

            # Extract JTI (JWT ID) - if not present, create one from token hash
            jti = payload.get('jti')
            if not jti:
                import hashlib
                jti = hashlib.sha256(token.encode()).hexdigest()[:16]

            # Extract expiry time
            exp = payload.get('exp')
            if not exp:
                logger.warning("Token has no expiry time, cannot blacklist")
                return False

            # Calculate TTL (time until expiry)
            now = datetime.now(timezone.utc).timestamp()
            ttl = int(exp - now)

            if ttl <= 0:
                logger.info("Token already expired, no need to blacklist")
                return True

            # Store in Redis with TTL
            key = f"{self.key_prefix}{jti}"
            await self.redis.setex(key, ttl, "revoked")

            logger.info(f"Token blacklisted: JTI={jti}, TTL={ttl}s")
            return True

        except JWTError as e:
            logger.error(f"Failed to decode token for blacklisting: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error blacklisting token: {e}")
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a JWT token is blacklisted.

        Args:
            token: The JWT token to check

        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        try:
            # Decode token without verification to extract JTI
            payload = jwt.get_unverified_claims(token)

            # Extract JTI
            jti = payload.get('jti')
            if not jti:
                import hashlib
                jti = hashlib.sha256(token.encode()).hexdigest()[:16]

            # Check Redis
            key = f"{self.key_prefix}{jti}"
            result = await self.redis.get(key)

            return result == "revoked"

        except JWTError as e:
            logger.warning(f"Failed to decode token for blacklist check: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking token blacklist: {e}")
            return False

    async def get_blacklist_size(self) -> int:
        """
        Get the current size of the blacklist (for monitoring).

        Returns:
            int: Number of blacklisted tokens
        """
        try:
            keys = await self.redis.keys(f"{self.key_prefix}*")
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get blacklist size: {e}")
            return 0


# Global blacklist instance
_jwt_blacklist: Optional[JWTBlacklist] = None

def get_jwt_blacklist() -> JWTBlacklist:
    """Get the global JWT blacklist instance."""
    if _jwt_blacklist is None:
        raise RuntimeError("JWT blacklist not initialized. Call init_jwt_blacklist() first.")
    return _jwt_blacklist

def init_jwt_blacklist(redis_client: redis.Redis) -> JWTBlacklist:
    """Initialize the global JWT blacklist instance."""
    global _jwt_blacklist
    _jwt_blacklist = JWTBlacklist(redis_client)
    logger.info("JWT blacklist initialized with Redis backend")
    return _jwt_blacklist