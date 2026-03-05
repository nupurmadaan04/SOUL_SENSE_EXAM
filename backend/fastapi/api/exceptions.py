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
