import httpx
import time
import asyncio
import os
from typing import Dict, Any, Optional
from api.config import get_settings_instance


class GitHubClient:
    """Handles all HTTP communication with the GitHub API."""

    def __init__(self) -> None:
        self.settings = get_settings_instance()
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SoulSense-Contributions-Dashboard"
        }
        if self.settings.github_token:
            self.headers["Authorization"] = f"token {self.settings.github_token}"

        self.owner = self.settings.github_repo_owner
        self.repo = self.settings.github_repo_name

        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(5.0, connect=3.0)
            )
        return self._client

    async def get(self, endpoint: str, params: Dict = None, ttl: Optional[int] = None, refresh: bool = False) -> Any:
        """
        Make a GET request to the GitHub API.

        Args:
            endpoint: API endpoint (e.g., "/repos/owner/repo/events")
            params: Query parameters
            ttl: Time-to-live for caching (not implemented here, handled by service layer)
            refresh: Force refresh flag (not implemented here, handled by service layer)

        Returns:
            JSON response data or None on failure
        """
        client = self._get_client()
        try:
            url = f"{self.base_url}{endpoint}"
            response = await client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 202:
                print(f"[WAIT] GitHub API: Stats are being calculated for {url}. Try again soon.")
                return []
            elif response.status_code in [403, 429]:
                retry_after = response.headers.get("Retry-After", "60")
                if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                    print(f"[WARN] GitHub 403 Rate Limit Exceeded. Retry-After: {retry_after}s")
                else:
                    print(f"[WARN] GitHub API [{response.status_code}]. Retry-After: {retry_after}s")
                return None
            else:
                print(f"[ERR] GitHub API Error [{response.status_code}] for {url}")
                return None
        except Exception as e:
            print(f"[ERR] GitHub Request Failed: {e}")
            return None

    async def get_with_semaphore(self, endpoint: str, semaphore: asyncio.Semaphore, ttl: Optional[int] = None) -> Any:
        """Make a GET request with semaphore control for rate limiting."""
        async with semaphore:
            return await self.get(endpoint, ttl=ttl)