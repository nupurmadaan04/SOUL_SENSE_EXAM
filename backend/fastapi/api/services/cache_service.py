from ..config import get_settings_instance
import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
import weakref
import gc
from collections import defaultdict

from api.config import get_settings_instance

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.redis: Optional[redis.Redis] = None
        # Use weak references to prevent memory leaks (#1219)
        self._local_cache: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._cache_cleanup_callbacks: weakref.WeakSet = weakref.WeakSet()
        self._pubsub_connection: Optional[redis.Redis] = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.settings.redis_url, decode_responses=True)

    def cache_with_weak_ref(self, key: str, value: Any, cleanup_callback: Optional[callable] = None):
        """Cache an object using weak references to prevent memory leaks."""
        def cleanup(ref):
            logger.debug(f"Cleaning up weak reference for cache key: {key}")
            if cleanup_callback:
                try:
                    cleanup_callback(key)
                except Exception as e:
                    logger.error(f"Cache cleanup callback error for {key}: {e}")

        self._local_cache[key] = weakref.ref(value, cleanup)
        if cleanup_callback:
            self._cache_cleanup_callbacks.add(cleanup_callback)

    def get_cached_weak(self, key: str) -> Optional[Any]:
        """Retrieve cached object, returns None if garbage collected."""
        ref = self._local_cache.get(key)
        if ref is not None:
            value = ref()
            if value is None:
                # Reference was garbage collected
                del self._local_cache[key]
            return value
        return None

    def clear_weak_cache(self):
        """Clear all weak references and trigger cleanup."""
        self._local_cache.clear()
        # Force garbage collection to clean up weak references
        gc.collect()
        logger.debug("Weak reference cache cleared")

    async def cleanup_resources(self):
        """Explicit cleanup of resources to prevent memory leaks."""
        logger.info("Starting cache service cleanup...")

        # Clear weak references
        self.clear_weak_cache()

        # Close Redis connections
        if self.redis:
            try:
                await self.redis.close()
                logger.debug("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        if self._pubsub_connection:
            try:
                await self._pubsub_connection.close()
                logger.debug("PubSub connection closed")
            except Exception as e:
                logger.error(f"Error closing PubSub connection: {e}")

        logger.info("Cache service cleanup completed")

    async def get(self, key: str) -> Optional[Any]:
        await self.connect()
        try:
            val = await self.redis.get(key)
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Redis get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        await self.connect()
        try:
            await self.redis.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error for {key}: {e}")

    async def delete(self, key: str):
        await self.connect()
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for {key}: {e}")

    async def invalidate_prefix(self, prefix: str):
        await self.connect()
        try:
            # Note: keys is not recommended for very huge datasets but since this is targeted caches, it's fine. 
            # Better approach is SCAN
            cursor = '0'
            while cursor != 0:
                cursor, keys = await self.redis.scan(cursor=cursor, match=f"{prefix}*", count=100)
                if keys:
                    await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis invalidate_prefix error for {prefix}: {e}")

    def sync_invalidate(self, key: str):
        try:
            import redis
            r = redis.from_url(self.settings.redis_url)
            r.delete(key)
        except Exception as e:
            logger.error(f"Redis sync delete error for {key}: {e}")
            
    def sync_invalidate_prefix(self, prefix: str):
        try:
            import redis
            r = redis.from_url(self.settings.redis_url)
            cursor = '0'
            while cursor != 0:
                cursor, keys = r.scan(cursor=cursor, match=f"{prefix}*", count=100)
                if keys:
                    r.delete(*keys)
        except Exception as e:
            logger.error(f"Redis sync invalidate_prefix error for {prefix}: {e}")

    # ==========================================
    # Distributed Cache Invalidation (ISSUE-1123)
    # ==========================================
    
    async def broadcast_invalidation(self, key_or_prefix: str, is_prefix: bool = False):
        """
        Broadcasts an invalidation message across the Redis Pub/Sub channel.
        Use this when modifying entities that might be cached in local memory
        across multiple uncoordinated uvicorn workers.
        """
        await self.connect()
        try:
            message = json.dumps({
                "type": "invalidate_prefix" if is_prefix else "invalidate_key",
                "target": key_or_prefix
            })
            await self.redis.publish("soulsense_cache_invalidation", message)
            logger.info(f"Broadcasted cache invalidation -> {message}")
        except Exception as e:
            logger.error(f"Failed to broadcast cache invalidation: {e}")

    async def start_invalidation_listener(self):
        """
        Background task that subscribes to the Redis Pub/Sub channel.
        Uses weak references and explicit cleanup to prevent memory leaks (#1219).
        """
        await self.connect()

        # Create separate connection for pubsub to avoid connection pool issues
        self._pubsub_connection = redis.from_url(self.settings.redis_url, decode_responses=True)
        pubsub = self._pubsub_connection.pubsub()

        # Use weak references for message processing to prevent accumulation
        processed_messages = weakref.WeakSet()

        try:
            await pubsub.subscribe("soulsense_cache_invalidation")
            logger.info("Subscribed to distributed cache invalidation channel")

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    # Use weak reference to track processed messages
                    message_ref = weakref.ref(message)
                    if message_ref in processed_messages:
                        continue  # Skip duplicate processing

                    processed_messages.add(message_ref)

                    try:
                        data = json.loads(message['data'])
                        action = data.get('type')
                        target = data.get('target')

                        if not action or not target:
                            continue

                        logger.info(f"Received cache invalidation event: {action} -> {target}")

                        # 1. Clear from our custom CacheService weak reference cache
                        if action == "invalidate_key":
                            self._local_cache.pop(target, None)
                        elif action == "invalidate_prefix":
                            # Remove all keys matching prefix
                            keys_to_remove = [k for k in self._local_cache.keys() if k.startswith(target)]
                            for key in keys_to_remove:
                                self._local_cache.pop(key, None)

                        # 2. Clear from FastAPICache (which might be using MemoryBackend locally)
                        from fastapi_cache import FastAPICache
                        backend = FastAPICache.get_backend()
                        if backend:
                            if action == "invalidate_key":
                                try:
                                    await backend.clear(namespace=target)
                                except Exception:
                                    pass
                            elif action == "invalidate_prefix":
                                try:
                                    await backend.clear(namespace=target)
                                except Exception:
                                    pass

                        # Periodic cleanup to prevent weak reference accumulation
                        if len(processed_messages) > 1000:
                            # Clean up dead weak references
                            processed_messages.clear()
                            gc.collect()

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in cache invalidation message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing cache invalidation message: {e}")

        except Exception as e:
            logger.error(f"Cache invalidation listener crashed: {e}")
        finally:
            # Explicit cleanup
            try:
                await pubsub.unsubscribe("soulsense_cache_invalidation")
                await pubsub.close()
                if self._pubsub_connection:
                    await self._pubsub_connection.close()
                    self._pubsub_connection = None
            except Exception as e:
                logger.error(f"Error during pubsub cleanup: {e}")

            # Clear processed messages
            processed_messages.clear()
            gc.collect()

    # ==========================================
    # Generation-based Versioning (ISSUE-1143)
    # ==========================================

    async def update_version(self, entity_type: str, entity_id: Any, version: int):
        """Update the authoritative version for an entity in Redis."""
        await self.connect()
        try:
            key = f"version:{entity_type}:{entity_id}"
            await self.redis.set(key, version) # No TTL, this is the persistent truth
            logger.debug(f"[GenVersion] Updated {key} -> {version}")
        except Exception as e:
            logger.error(f"[GenVersion] Update failed for {entity_type}:{entity_id}: {e}")

    async def get_latest_version(self, entity_type: str, entity_id: Any) -> int:
        """Get the authoritative version for an entity from Redis."""
        await self.connect()
        try:
            key = f"version:{entity_type}:{entity_id}"
            val = await self.redis.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"[GenVersion] Get failed for {entity_type}:{entity_id}: {e}")
            return 0

    async def get_with_version_check(self, key: str, entity_type: str, entity_id: Any) -> Optional[Any]:
        """
        Retrieves data from cache and verifies it against the 
        global authoritative generation/version from Redis.
        Ensures nodes that missed invalidation eventually catch up.
        """
        cached_data = await self.get(key)
        if not cached_data:
            return None
        
        # Verify version
        cached_version = cached_data.get("version", 0)
        latest_version = await self.get_latest_version(entity_type, entity_id)

        # Fallback for missing latest_version in Redis: assume at least 1 if entity exists
        if latest_version == 0 and cached_version > 0:
            logger.debug(f"[GenVersion] Missing latest_version in Redis for {entity_type}:{entity_id}. Assuming cached is acceptable.")
            return cached_data

        if cached_version < latest_version:
            logger.info(f"[GenVersion] Cache stale for {key}: cached={cached_version} latest={latest_version}. Purging.")
            await self.delete(key)
            return None
        
        return cached_data

    async def purge_stale_cache(self, key: str, entity_type: str, entity_id: Any):
        """Forcefully purge an entry if it's known to be stale."""
        await self.delete(key)
        # We don't necessarily update_version here as this is a read-side cleanup

cache_service = CacheService()
