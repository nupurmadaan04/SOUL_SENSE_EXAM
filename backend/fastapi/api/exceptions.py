from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from .constants.errors import ErrorCode

class APIException(HTTPException):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
        fields: Optional[List[Dict[str, Any]]] = None
    ):
        detail = {
            "code": code.value,
            "message": message,
        }
        if details:
            detail["details"] = details
        if fields:
            detail["fields"] = fields
            
        super().__init__(status_code=status_code, detail=detail)

class AuthException(APIException):
    def __init__(self, code: ErrorCode, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, status_code=status_code, details=details)

class RateLimitException(APIException):
    def __init__(self, message: str = "Too many requests", wait_seconds: int = 60):
        super().__init__(
            code=ErrorCode.GLB_RATE_LIMIT,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"wait_seconds": wait_seconds}
        )


class PayloadSizeException(APIException):
    """Exception for payload size limit violations (DoS protection)."""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details
        )


class PayloadTooLargeException(PayloadSizeException):
    """Exception for request body exceeding size limits."""
    def __init__(self, size_bytes: int, max_size_bytes: int):
        super().__init__(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message=f"Request body too large: {size_bytes} bytes (max: {max_size_bytes} bytes)",
            details={
                "size_bytes": size_bytes,
                "max_size_bytes": max_size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "max_size_mb": round(max_size_bytes / (1024 * 1024), 2)
            }
        )


class PayloadDepthExceededException(PayloadSizeException):
    """Exception for JSON payload exceeding nesting depth."""
    def __init__(self, depth: int, max_depth: int):
        super().__init__(
            code=ErrorCode.PAYLOAD_DEPTH_EXCEEDED,
            message=f"JSON nesting depth exceeded: {depth} (max: {max_depth})",
            details={
                "depth": depth,
                "max_depth": max_depth
            }
        )


class PayloadMalformedException(PayloadSizeException):
    """Exception for malformed payload that could indicate an attack."""
    def __init__(self, reason: str):
        super().__init__(
            code=ErrorCode.PAYLOAD_MALFORMED,
            message=f"Malformed payload: {reason}",
            details={"reason": reason}
        )


class CompressionBombException(PayloadSizeException):
    """Exception for compression bomb detection."""
    def __init__(self, ratio: float, threshold: float):
        super().__init__(
            code=ErrorCode.PAYLOAD_COMPRESSION_BOMB,
            message=f"Compression bomb detected: ratio {ratio:.1f}:1 (threshold: {threshold}:1)",
            details={
                "compression_ratio": ratio,
                "threshold": threshold
            }
        )


class MultipartTooManyPartsException(PayloadSizeException):
    """Exception for multipart requests with too many parts."""
    def __init__(self, parts: int, max_parts: int):
        super().__init__(
            code=ErrorCode.MULTIPART_TOO_MANY_PARTS,
            message=f"Too many multipart parts: {parts} (max: {max_parts})",
            details={
                "parts": parts,
                "max_parts": max_parts
            }
        )
