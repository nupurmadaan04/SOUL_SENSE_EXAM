"""
Test script for standardized API error responses.

This script verifies that all error responses conform to the standardized format:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": [...],  // Optional
        "request_id": "req-uuid"  // Added by handlers
    }
}

Usage:
    python -m pytest backend/fastapi/tests/test_standardized_exceptions.py -v
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.core import (
    register_exception_handlers,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    BusinessLogicError,
    InternalServerError,
)


# Create a test app
app = FastAPI()
register_exception_handlers(app)


# Test endpoints
@app.get("/test/not-found")
async def test_not_found():
    raise NotFoundError(resource="User", resource_id="999")


@app.get("/test/validation")
async def test_validation():
    raise ValidationError(
        message="Invalid input data",
        details=[{"field": "email", "error": "Invalid email format"}]
    )


@app.get("/test/auth")
async def test_auth():
    raise AuthenticationError(message="Invalid credentials")


@app.get("/test/forbidden")
async def test_forbidden():
    raise AuthorizationError(message="Access denied to this resource")


@app.get("/test/conflict")
async def test_conflict():
    raise ConflictError(message="Resource already exists")


@app.get("/test/rate-limit")
async def test_rate_limit():
    raise RateLimitError(message="Too many requests", wait_seconds=60)


@app.get("/test/business-logic")
async def test_business_logic():
    raise BusinessLogicError(message="Invalid state transition", code="INVALID_STATE")


@app.get("/test/internal-error")
async def test_internal_error():
    raise InternalServerError(message="Something went wrong")


@app.get("/test/raw-http-exception")
async def test_raw_http_exception():
    raise StarletteHTTPException(status_code=404, detail="Raw HTTP exception")


client = TestClient(app)


class TestStandardizedErrorResponses:
    """Test suite for standardized error responses."""
    
    def test_not_found_error(self):
        """Test NotFoundError returns standardized format."""
        response = client.get("/test/not-found")
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "User" in data["error"]["message"]
        assert "999" in data["error"]["message"]
        assert "request_id" in data["error"]
    
    def test_validation_error(self):
        """Test ValidationError returns standardized format."""
        response = client.get("/test/validation")
        assert response.status_code == 422
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Invalid input data"
        assert "details" in data["error"]
        assert len(data["error"]["details"]) == 1
        assert "request_id" in data["error"]
    
    def test_authentication_error(self):
        """Test AuthenticationError returns standardized format."""
        response = client.get("/test/auth")
        assert response.status_code == 401
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"
        assert "Invalid credentials" in data["error"]["message"]
        assert "request_id" in data["error"]
    
    def test_authorization_error(self):
        """Test AuthorizationError returns standardized format."""
        response = client.get("/test/forbidden")
        assert response.status_code == 403
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"
        assert "Access denied" in data["error"]["message"]
        assert "request_id" in data["error"]
    
    def test_conflict_error(self):
        """Test ConflictError returns standardized format."""
        response = client.get("/test/conflict")
        assert response.status_code == 409
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "CONFLICT_ERROR"
        assert "request_id" in data["error"]
    
    def test_rate_limit_error(self):
        """Test RateLimitError returns standardized format."""
        response = client.get("/test/rate-limit")
        assert response.status_code == 429
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "details" in data["error"]
        assert "request_id" in data["error"]
    
    def test_business_logic_error(self):
        """Test BusinessLogicError returns standardized format."""
        response = client.get("/test/business-logic")
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "INVALID_STATE"
        assert "Invalid state transition" in data["error"]["message"]
        assert "request_id" in data["error"]
    
    def test_internal_server_error(self):
        """Test InternalServerError returns standardized format."""
        response = client.get("/test/internal-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "request_id" in data["error"]
    
    def test_raw_http_exception(self):
        """Test that raw HTTPExceptions are also standardized."""
        response = client.get("/test/raw-http-exception")
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "request_id" in data["error"]


class TestPydanticValidationErrors:
    """Test Pydantic validation error handling."""
    
    def test_pydantic_validation_error(self):
        """Test that Pydantic validation errors are standardized."""
        from pydantic import BaseModel, Field
        
        test_app = FastAPI()
        register_exception_handlers(test_app)
        
        class TestModel(BaseModel):
            name: str = Field(..., min_length=3)
            age: int = Field(..., ge=0, le=120)
        
        @test_app.post("/test/pydantic")
        async def pydantic_endpoint(data: TestModel):
            return data
        
        test_client = TestClient(test_app)
        
        # Send invalid data
        response = test_client.post("/test/pydantic", json={"name": "ab", "age": -1})
        assert response.status_code == 422
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
        assert isinstance(data["error"]["details"], list)
        assert "request_id" in data["error"]


if __name__ == "__main__":
    # Run tests with pytest if available
    pytest.main([__file__, "-v"])
