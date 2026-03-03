"""
Payload Size Limits and DoS Protection Middleware.

This middleware provides protection against:
- Oversized request bodies
- Deeply nested JSON payloads
- Compression bombs (gzip/zip)
- Malformed multipart requests
- Excessive array/object sizes

Issue #1068: Add Payload Size Limits and DoS Protection
"""

import json
import logging
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from ..config import get_settings_instance
from ..constants.errors import ErrorCode
from ..exceptions import (
    PayloadTooLargeException,
    PayloadDepthExceededException,
    PayloadMalformedException,
    CompressionBombException,
    MultipartTooManyPartsException,
)
from ..utils.payload_validator import (
    validate_json_payload,
    check_compression_bomb,
    check_zip_bomb,
    get_content_length,
    should_validate_content_type,
    validate_content_length,
    PayloadValidationError,
)

logger = logging.getLogger("api.payload_limit")


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce payload size limits and DoS protection.
    
    This middleware checks:
    1. Content-Length header against max_request_size_bytes
    2. Actual body size against max_request_size_bytes
    3. JSON payload structure (depth, array size, object keys)
    4. Compression bombs (gzip/zip)
    5. Multipart form boundaries and part counts
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings_instance()
        self.max_request_size = self.settings.max_request_size_bytes
        self.max_json_depth = self.settings.max_json_depth
        self.max_multipart_parts = self.settings.max_multipart_parts
        self.max_array_size = self.settings.max_array_size
        self.max_object_keys = self.settings.max_object_keys
        self.enable_compression_check = self.settings.enable_compression_bomb_check
        self.compression_ratio = self.settings.compression_bomb_ratio
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with payload size validation."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Skip validation for certain paths
        if self._should_skip_validation(request.url.path):
            return await call_next(request)
        
        # Check content length header early
        content_length = get_content_length(request.headers)
        try:
            validate_content_length(content_length, self.max_request_size)
        except Exception as e:
            logger.warning(
                f"Content-Length validation failed: {e}",
                extra={"request_id": request_id, "path": request.url.path}
            )
            return self._create_error_response(
                ErrorCode.PAYLOAD_TOO_LARGE,
                str(e),
                413,
                {"max_size_bytes": self.max_request_size}
            )
        
        # Get content type
        content_type = request.headers.get("content-type", "")
        
        # Only validate certain content types
        if should_validate_content_type(content_type):
            # Read and validate body
            body = await self._read_body_with_limit(request, request_id)
            if body is None:
                # Error response already created in _read_body_with_limit
                return self._create_error_response(
                    ErrorCode.PAYLOAD_TOO_LARGE,
                    "Request body too large",
                    413,
                    {"max_size_bytes": self.max_request_size}
                )
            
            # Validate based on content type
            try:
                if 'application/json' in content_type:
                    await self._validate_json_body(body, request_id)
                elif 'gzip' in content_type or body.startswith(b'\x1f\x8b'):
                    await self._validate_compressed_body(body, request_id)
                elif 'multipart/form-data' in content_type:
                    await self._validate_multipart_body(body, content_type, request_id)
                elif 'application/zip' in content_type or body.startswith(b'PK'):
                    await self._validate_zip_body(body, request_id)
                    
            except PayloadTooLargeException:
                raise
            except PayloadDepthExceededException:
                raise
            except CompressionBombException:
                raise
            except MultipartTooManyPartsException:
                raise
            except PayloadValidationError as e:
                logger.warning(
                    f"Payload validation error: {e.message}",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "code": e.code,
                        "details": e.details
                    }
                )
                return self._create_error_response(
                    ErrorCode.PAYLOAD_MALFORMED,
                    e.message,
                    400,
                    e.details
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error during payload validation: {e}",
                    extra={"request_id": request_id, "path": request.url.path},
                    exc_info=True
                )
                # Continue with request even if validation fails unexpectedly
        
        # Continue with the request
        return await call_next(request)
    
    def _should_skip_validation(self, path: str) -> bool:
        """Check if validation should be skipped for this path."""
        # Skip health checks and static files
        skip_paths = [
            '/health',
            '/healthz',
            '/ready',
            '/alive',
            '/metrics',
            '/favicon.ico',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/static/',
        ]
        return any(path.startswith(skip) for skip in skip_paths)
    
    async def _read_body_with_limit(self, request: Request, request_id: str) -> Optional[bytes]:
        """
        Read request body with size limit enforcement.
        
        Returns:
            Body bytes if within limit, None if limit exceeded
        """
        body_parts = []
        total_size = 0
        
        async for chunk in request.stream():
            chunk_size = len(chunk)
            total_size += chunk_size
            
            if total_size > self.max_request_size:
                logger.warning(
                    f"Request body exceeded size limit: {total_size} bytes (max: {self.max_request_size})",
                    extra={
                        "request_id": request_id,
                        "size_bytes": total_size,
                        "max_size_bytes": self.max_request_size
                    }
                )
                return None
            
            body_parts.append(chunk)
        
        return b''.join(body_parts)
    
    async def _validate_json_body(self, body: bytes, request_id: str) -> None:
        """Validate JSON body structure."""
        if not body:
            return
        
        try:
            validate_json_payload(
                body,
                max_depth=self.max_json_depth,
                max_array_size=self.max_array_size,
                max_object_keys=self.max_object_keys
            )
        except Exception:
            # Re-raise to be handled by dispatch
            raise
    
    async def _validate_compressed_body(self, body: bytes, request_id: str) -> None:
        """Validate compressed (gzip) body for compression bombs."""
        if not self.enable_compression_check or not body:
            return
        
        try:
            check_compression_bomb(
                body,
                threshold_ratio=self.compression_ratio,
                max_uncompressed_size=self.max_request_size * 2
            )
        except Exception:
            # Re-raise to be handled by dispatch
            raise
    
    async def _validate_zip_body(self, body: bytes, request_id: str) -> None:
        """Validate zip archive for compression bombs."""
        if not self.enable_compression_check or not body:
            return
        
        try:
            check_zip_bomb(
                body,
                threshold_ratio=self.compression_ratio,
                max_total_size=self.max_request_size * 2,
                max_files=self.max_multipart_parts
            )
        except Exception:
            # Re-raise to be handled by dispatch
            raise
    
    async def _validate_multipart_body(self, body: bytes, content_type: str, request_id: str) -> None:
        """Validate multipart form data."""
        if not body:
            return
        
        # Extract boundary
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part[9:].strip('"\'')
                break
        
        if not boundary:
            logger.warning(
                "Multipart request without boundary",
                extra={"request_id": request_id}
            )
            return
        
        # Count parts (simple counting of boundary occurrences)
        boundary_bytes = f'--{boundary}'.encode()
        part_count = body.count(boundary_bytes)
        
        if part_count > self.max_multipart_parts:
            logger.warning(
                f"Multipart request has too many parts: {part_count} (max: {self.max_multipart_parts})",
                extra={
                    "request_id": request_id,
                    "parts": part_count,
                    "max_parts": self.max_multipart_parts
                }
            )
            raise MultipartTooManyPartsException(part_count, self.max_multipart_parts)
    
    def _create_error_response(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: Optional[dict] = None
    ) -> JSONResponse:
        """Create a standardized error response."""
        content = {
            "code": code.value,
            "message": message,
        }
        if details:
            content["details"] = details
        
        return JSONResponse(
            status_code=status_code,
            content=content
        )


class StreamingPayloadLimitMiddleware:
    """
    ASGI middleware for streaming payload size limits.
    
    This is an alternative implementation that works at the ASGI level
    for better performance with streaming requests.
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
        self.settings = get_settings_instance()
        self.max_request_size = self.settings.max_request_size_bytes
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check path for exclusions
        path = scope.get("path", "")
        if self._should_skip_validation(path):
            await self.app(scope, receive, send)
            return
        
        # Wrap receive to enforce size limits
        total_size = 0
        
        async def wrapped_receive() -> Message:
            nonlocal total_size
            message = await receive()
            
            if message["type"] == "http.request":
                body = message.get("body", b"")
                total_size += len(body)
                
                if total_size > self.max_request_size:
                    logger.warning(
                        f"Streaming request body exceeded size limit: {total_size} bytes",
                        extra={"path": path, "max_size": self.max_request_size}
                    )
                    # Return error response
                    await send({
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [(b"content-type", b"application/json")]
                    })
                    await send({
                        "type": "http.response.body",
                        "body": json.dumps({
                            "code": ErrorCode.PAYLOAD_TOO_LARGE.value,
                            "message": f"Request body too large (max: {self.max_request_size} bytes)"
                        }).encode()
                    })
                    raise PayloadTooLargeException(total_size, self.max_request_size)
            
            return message
        
        await self.app(scope, wrapped_receive, send)
    
    def _should_skip_validation(self, path: str) -> bool:
        """Check if validation should be skipped for this path."""
        skip_paths = [
            '/health',
            '/healthz',
            '/ready',
            '/alive',
            '/metrics',
            '/favicon.ico',
            '/docs',
            '/redoc',
            '/openapi.json',
        ]
        return any(path.startswith(skip) for skip in skip_paths)
