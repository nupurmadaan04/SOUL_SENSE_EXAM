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
    def __init__(self, code: ErrorCode, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(code=code, message=message, status_code=status_code)
