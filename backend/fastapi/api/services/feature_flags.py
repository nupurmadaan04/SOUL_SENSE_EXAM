import json
import logging
import asyncio
from typing import Dict, Any, Optional
try:
    import consul
except ImportError:
    consul = None
from cachetools import TTLCache
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class FeatureFlagService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.consul_host = getattr(self.settings, 'consul_host', 'localhost')
        self.consul_port = getattr(self.settings, 'consul_port', 8500)
        if consul:
            try:
                self.client = consul.Consul(host=self.consul_host, port=self.consul_port)
            except Exception:
                self.client = None
        else:
            self.client = None
        # Local cache for 30 seconds
        self.cache = TTLCache(maxsize=100, ttl=30)
        self.prefix = "soulsense/features/"

    def get_all_flags(self) -> Dict[str, Any]:
        """Fetch all flags from Consul with local caching."""
        if "all_flags" in self.cache:
            return self.cache["all_flags"]

        if not self.client:
            # Fallback default flags when Consul is not installed/running
            default_flags = {
                "dark_mode": {"enabled": True},
                "new_assessment_flow": {"enabled": True},
                "enable_analytics": {"enabled": True}
            }
            self.cache["all_flags"] = default_flags
            return default_flags

        flags = {}
        try:
            index, data = self.client.kv.get(self.prefix, recurse=True)
            if data:
                for item in data:
                    key = item['Key'].replace(self.prefix, "")
                    if key:
                        try:
                            val = json.loads(item['Value'])
                            flags[key] = val if isinstance(val, dict) else {"enabled": bool(val)}
                        except Exception:
                            logger.warning(f"Failed to parse flag value for {key}")
            
            self.cache["all_flags"] = flags
            return flags
        except Exception as e:
            logger.error(f"Error connecting to Consul: {e}. Returning empty flags.")
            return {}

    def is_enabled(self, feature_name: str, user_id: Optional[int] = None, tenant_id: Optional[str] = None) -> bool:
        """Check if a feature is enabled for a specific user/tenant."""
        flags = self.get_all_flags()
        flag = flags.get(feature_name)
        
        if flag is None:
            return False
        
        if isinstance(flag, bool):
            return flag

        if isinstance(flag, dict):
            if not flag.get('enabled', False):
                return False

            # Tenant Override
            if tenant_id and flag.get('tenant_overrides', {}).get(str(tenant_id)) is not None:
                return flag['tenant_overrides'][str(tenant_id)]

            # Rollout percentage (probabilistic)
            if user_id and flag.get('rollout_percentage', 100) < 100:
                import hashlib
                # Deterministic hash for consistent user experience
                hash_val = int(hashlib.md5(f"{feature_name}:{user_id}".encode()).hexdigest(), 16)
                return (hash_val % 100) < flag['rollout_percentage']

            return True

        return bool(flag)

    def set_flag(self, feature_name: str, config: Dict[str, Any]):
        """Create or update a flag in Consul."""
        try:
            self.client.kv.put(f"{self.prefix}{feature_name}", json.dumps(config))
            self.cache.clear() # Invalidate local cache
            return True
        except Exception as e:
            logger.error(f"Failed to write to Consul: {e}")
            return False

_feature_service = None

def get_feature_service() -> FeatureFlagService:
    global _feature_service
    if _feature_service is None:
        _feature_service = FeatureFlagService()
    return _feature_service
