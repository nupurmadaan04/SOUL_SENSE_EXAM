import json
import logging
from typing import Callable, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from ..services.cache_service import cache_service

logger = logging.getLogger("api.idempotency")

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    API-Level Idempotency Middleware (#1181).
    
    Prevents duplicate processing of POST, PATCH, and DELETE requests by caching
    responses based on a unique 'X-Idempotency-Key' provided by the client.
    
    Flow:
    1. Check for 'X-Idempotency-Key' header in write requests.
    2. If present, lookup (user_id, key) in Redis.
    3. If cache HIT: Return stored response immediately.
    4. If cache MISS: Proceed to handler, then cache the final status/body in Redis.
    
    TTL: 24 hours (86400 seconds)
    """

    IDEMPOTENT_METHODS = {"POST", "PATCH", "DELETE"}
    IDEMPOTENCY_HEADER = "X-Idempotency-Key"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to mutating requests
        if request.method not in self.IDEMPOTENT_METHODS:
            return await call_next(request)

        idempotency_key = request.headers.get(self.IDEMPOTENCY_HEADER)
        if not idempotency_key:
            # If no key provided, project policy might vary (e.g. enforce or allow).
            # For this implementation, we follow 'opt-in' idempotency to avoid breaking bulk tools.
            return await call_next(request)

        # Ensure we have a user_id (populated by RBAC/Auth middleware earlier in the chain)
        user_id = getattr(request.state, "user_id", "anonymous")
        
        # Redis key format: 'idem:{user_id}:{key}'
        redis_key = f"idem:{user_id}:{idempotency_key}"

        # 1. Check for existing response
        cached_res = await cache_service.get(redis_key)
        if cached_res:
            logger.info(f"Idempotency HIT for key {idempotency_key} - User {user_id}")
            return Response(
                content=cached_res["body"],
                status_code=cached_res["status_code"],
                headers={
                    **cached_res["headers"],
                    "X-Idempotency-Cache": "HIT"
                },
                media_type=cached_res.get("media_type")
            )

        # 2. Process the request
        logger.debug(f"Idempotency MISS for key {idempotency_key} - Executing handler")
        response = await call_next(request)

        # 3. Cache the response if it was successful (2xx)
        # We generally don't cache 4xx/5xx errors as they might be transient or fixable by the user
        if 200 <= response.status_code < 300:
            # Handle StreamingResponse (default for call_next in many cases)
            response_body = b""
            if isinstance(response, StreamingResponse):
                # Consume the stream to cache it
                body_chunks = [chunk async for chunk in response.body_iterator]
                response_body = b"".join(body_chunks)
                # Re-create the response so it can still be sent to the client
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            else:
                response_body = getattr(response, "body", b"")

            # Store in Redis
            cache_payload = {
                "status_code": response.status_code,
                "body": response_body.decode("utf-8") if isinstance(response_body, bytes) else response_body,
                "headers": {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "set-cookie"}},
                "media_type": response.media_type
            }
            
            # 24-hour TTL
            await cache_service.set(redis_key, cache_payload, ttl_seconds=86400)
            logger.debug(f"Idempotency response cached for key {idempotency_key}")

        response.headers["X-Idempotency-Cache"] = "MISS"
        return response
