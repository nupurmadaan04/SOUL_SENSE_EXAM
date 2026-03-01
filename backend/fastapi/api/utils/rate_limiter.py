import time
from collections import defaultdict
from typing import Dict, Optional
import asyncio


class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.config = {
            "default": {"requests": 100, "window": 60},
            "auth": {"requests": 10, "window": 60},
            "api": {"requests": 1000, "window": 3600},
        }

    def _get_client_id(self, request) -> str:
        if hasattr(request, "client"):
            return request.client.host
        return "unknown"

    def _clean_old_requests(self, client_id: str, window: int):
        current_time = time.time()
        self.requests[client_id] = [
            req_time
            for req_time in self.requests[client_id]
            if current_time - req_time < window
        ]

    async def check_rate_limit(
        self, request, endpoint_type: str = "default"
    ) -> tuple[bool, Optional[str]]:
        client_id = self._get_client_id(request)
        config = self.config.get(endpoint_type, self.config["default"])

        self._clean_old_requests(client_id, config["window"])

        if len(self.requests[client_id]) >= config["requests"]:
            retry_after = config["window"]
            return False, f"Rate limit exceeded. Retry after {retry_after} seconds."

        self.requests[client_id].append(time.time())
        return True, None

    def get_rate_limit_headers(
        self, request, endpoint_type: str = "default"
    ) -> Dict[str, str]:
        client_id = self._get_client_id(request)
        config = self.config.get(endpoint_type, self.config["default"])

        self._clean_old_requests(client_id, config["window"])

        remaining = config["requests"] - len(self.requests[client_id])

        return {
            "X-RateLimit-Limit": str(config["requests"]),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(time.time()) + config["window"]),
        }


rate_limiter = RateLimiter()
