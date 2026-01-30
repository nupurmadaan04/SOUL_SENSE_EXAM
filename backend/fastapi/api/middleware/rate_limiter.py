"""Rate limiting middleware and utilities."""
from fastapi import Request, HTTPException, status
from typing import Dict
from datetime import datetime, timedelta
import time


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 30):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove expired entries to prevent memory growth."""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 60  # Remove entries older than 1 minute
        
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                timestamp for timestamp in self.requests[ip]
                if timestamp > cutoff_time
            ]
            
            # Remove IP if no recent requests
            if not self.requests[ip]:
                del self.requests[ip]
        
        self.last_cleanup = current_time
    
    async def check_rate_limit(self, request: Request):
        """
        Check if request is within rate limit.
        
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        current_time = time.time()
        
        # Initialize tracking for this IP if needed
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip]
            if timestamp > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)


# Global rate limiter instances
analytics_rate_limiter = RateLimiter(requests_per_minute=30)
general_rate_limiter = RateLimiter(requests_per_minute=60)


async def rate_limit_analytics(request: Request):
    """
    Rate limit dependency for analytics endpoints.
    
    Limit: 30 requests per minute per IP
    """
    await analytics_rate_limiter.check_rate_limit(request)


async def rate_limit_general(request: Request):
    """
    Rate limit dependency for general endpoints.
    
    Limit: 60 requests per minute per IP
    """
    await general_rate_limiter.check_rate_limit(request)
