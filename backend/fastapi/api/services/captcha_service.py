import random
import string
import secrets
from typing import Tuple
from cachetools import TTLCache

class CaptchaService:
    """
    Service for generating and validating CAPTCHAs.
    Uses in-memory cache with TTL for session-based CAPTCHA storage.
    """

    def __init__(self, cache_ttl: int = 300):  # 5 minutes TTL
        # Cache: session_id -> captcha_code
        self.captcha_cache = TTLCache(maxsize=10000, ttl=cache_ttl)

    def generate_captcha(self, session_id: str) -> str:
        """
        Generate a random CAPTCHA code and store it for the session.
        Returns the CAPTCHA code to display to the user.
        """
        # Generate random 5-character code: letters and digits
        characters = string.ascii_letters + string.digits
        captcha_code = ''.join(secrets.choice(characters) for _ in range(5))

        # Store in cache
        self.captcha_cache[session_id] = captcha_code.upper()

        return captcha_code

    def validate_captcha(self, session_id: str, user_input: str) -> bool:
        """
        Validate user input against stored CAPTCHA.
        Case-insensitive comparison.
        Removes CAPTCHA from cache after validation (one-time use).
        """
        if not session_id or not user_input:
            return False

        stored_code = self.captcha_cache.get(session_id)
        if not stored_code:
            return False

        # Case-insensitive comparison
        is_valid = stored_code.lower() == user_input.strip().lower()

        # Remove from cache (one-time use)
        if session_id in self.captcha_cache:
            del self.captcha_cache[session_id]

        return is_valid

    def invalidate_captcha(self, session_id: str) -> None:
        """
        Manually invalidate a CAPTCHA (e.g., on refresh).
        """
        if session_id in self.captcha_cache:
            del self.captcha_cache[session_id]

# Global instance
captcha_service = CaptchaService()