"""
Response optimization middleware.

Implements:
- Response compression
- JSON minification
- ETag generation
- Conditional requests (304 Not Modified)
"""

import gzip
import hashlib
import json
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class ResponseOptimizationMiddleware(BaseHTTPMiddleware):
    """Optimize API responses for performance."""
    
    def __init__(self, app, min_size: int = 1000):
        super().__init__(app)
        self.min_size = min_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Skip optimization for non-JSON responses
        if not response.headers.get("content-type", "").startswith("application/json"):
            return response
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Generate ETag
        etag = hashlib.md5(body).hexdigest()
        
        # Check If-None-Match header
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"etag": etag})
        
        # Compress if large enough and client supports it
        if len(body) >= self.min_size and "gzip" in request.headers.get("accept-encoding", ""):
            body = gzip.compress(body)
            response.headers["content-encoding"] = "gzip"
        
        # Add ETag header
        response.headers["etag"] = etag
        response.headers["cache-control"] = "private, max-age=300"
        
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )


def minify_json_response(data: dict) -> str:
    """Minify JSON response by removing whitespace."""
    return json.dumps(data, separators=(',', ':'))
