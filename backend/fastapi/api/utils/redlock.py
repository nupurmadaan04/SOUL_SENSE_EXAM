import uuid
import logging
from typing import Optional, Tuple
from datetime import datetime, UTC
from ..services.cache_service import cache_service

logger = logging.getLogger("api.utils.redlock")

# Lua script: atomically release ONLY if caller holds the lock (ownership proof)
_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script: atomically renew ONLY if caller holds the lock (watchdog/heartbeat)
_RENEW_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedlockService:
    """
    Single-instance Redis locking with Fencing Tokens for Team Vision Documents (#1178).

    NOTE: This implementation uses a single Redis node with atomic SET NX EX
    and Lua-script-guarded release/renew operations. It is NOT a multi-node
    quorum Redlock (RFC Redlock algorithm). The design is intentionally pragmatic:
    fencing tokens (document version) provide a second layer of safety so that
    even if the lock TTL races, stale writes are rejected at the database level.
    """

    def __init__(self):
        self._lock_prefix = "lock:team_vision:"

    def _lock_key(self, resource_id: str) -> str:
        return f"{self._lock_prefix}{resource_id}"

    async def acquire_lock(
        self, resource_id: str, user_id: int, ttl_seconds: int = 30
    ) -> Tuple[bool, Optional[str]]:
        """
        Acquires an exclusive lease on a resource.
        Returns (success, lock_value).

        lock_value format: "<user_id>:<uuid4>" — embeds ownership + uniqueness.
        The client MUST persist this token and present it on every update call
        and on renew/unlock, to prove they still hold the lease.
        """
        await cache_service.connect()
        lock_key = self._lock_key(resource_id)
        lock_value = f"{user_id}:{uuid.uuid4()}"  # Ownership token

        # NX: Set only if key does not exist (mutual exclusion)
        # EX: Auto-expire after TTL so ghost locks cannot persist
        success = await cache_service.redis.set(
            lock_key,
            lock_value,
            nx=True,
            ex=ttl_seconds
        )

        if success:
            logger.info(f"[Lock] ACQUIRED resource={resource_id} user={user_id} ttl={ttl_seconds}s")
            return True, lock_value

        # Idempotency: if this user already holds the lock, just renew it
        current_val = await cache_service.redis.get(lock_key)
        if current_val and current_val.startswith(f"{user_id}:"):
            await cache_service.redis.expire(lock_key, ttl_seconds)
            logger.info(f"[Lock] RENEWED (idempotent re-acquire) resource={resource_id} user={user_id}")
            return True, current_val

        logger.warning(f"[Lock] DENIED resource={resource_id} by user={user_id} — currently held by {current_val}")
        return False, None

    async def release_lock(self, resource_id: str, lock_value: str) -> bool:
        """
        Releases the lease ONLY if the presented lock_value matches the stored token.
        Uses an atomic Lua script to prevent race conditions (TOCTOU-safe).
        Returns True on success, False if token mismatch or lock already expired.
        """
        await cache_service.connect()
        lock_key = self._lock_key(resource_id)

        result = await cache_service.redis.eval(_RELEASE_LUA, 1, lock_key, lock_value)
        if result == 1:
            logger.info(f"[Lock] RELEASED resource={resource_id}")
            return True

        logger.warning(f"[Lock] Release FAILED resource={resource_id} — invalid token or already expired")
        return False

    async def renew_lock(
        self, resource_id: str, lock_value: str, extend_by_seconds: int = 30
    ) -> bool:
        """
        Watchdog / Heartbeat: Extends the TTL of an active lease if the
        caller presents the correct lock_value token.
        The client should call this endpoint periodically (e.g., every 20s
        if the TTL is 30s) to avoid losing the lock during a long editing session.
        Uses an atomic Lua script (TOCTOU-safe).
        Returns True on success, False if token mismatch or lock expired.
        """
        await cache_service.connect()
        lock_key = self._lock_key(resource_id)

        result = await cache_service.redis.eval(
            _RENEW_LUA, 1, lock_key, lock_value, str(extend_by_seconds)
        )
        if result == 1:
            logger.info(f"[Lock] RENEWED resource={resource_id} +{extend_by_seconds}s")
            return True

        logger.warning(f"[Lock] Renew FAILED resource={resource_id} — invalid token or expired")
        return False

    async def get_lock_info(self, resource_id: str) -> Optional[dict]:
        """
        Returns metadata about who currently holds the lock,
        including the full lock_value token (for exact validation in update endpoint).
        Returns None if the resource is unlocked.
        """
        await cache_service.connect()
        lock_key = self._lock_key(resource_id)
        val = await cache_service.redis.get(lock_key)
        if not val:
            return None

        user_id_str, _ = val.split(":", 1)
        ttl = await cache_service.redis.ttl(lock_key)

        return {
            "user_id": int(user_id_str),
            "lock_value": val,        # Full token — used for exact equality check in update
            "expires_in": ttl
        }


redlock_service = RedlockService()
