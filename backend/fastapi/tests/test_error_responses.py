"""
Quick test script for standardized error responses.
Run with: python -m pytest backend/fastapi/tests/test_error_responses.py -v
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from api.main import app

client = TestClient(app)


def test_validation_error_structure():
    """Test that validation errors return standardized format."""
    response = client.post(
        "/api/v1/auth/register",
        json={},  # Empty body triggers validation error
        headers={"Host": "localhost"}
    )
    
    assert response.status_code == 422
    data = response.json()
    
    # Check standardized structure
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "request_id" in data["error"]
    assert data["error"]["code"] == "VALIDATION_ERROR"
    print(f"[OK] Validation error: {data['error']['code']}")


def test_not_found_error_structure():
    """Test that 404 errors return standardized format."""
    response = client.get(
        "/api/v1/users/99999999",  # Non-existent user
        headers={"Host": "localhost"}
    )
    
    # Should get 401 (not authenticated) or 404 (if authenticated)
    assert response.status_code in [401, 404, 403]
    data = response.json()
    
    # Check standardized structure
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    assert "request_id" in data["error"]
    print(f"[OK] Auth/Not Found error: {data['error']['code']}")


def test_age_validation_error():
    """Test age validation returns standardized format."""
    response = client.get(
        "/api/v1/questions/by-age/5",  # Invalid age
        headers={"Host": "localhost"}
    )
    
    assert response.status_code == 422
    data = response.json()
    
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    print(f"[OK] Age validation error: {data['error']['code']}")


def test_invalid_category_error():
    """Test category not found returns standardized format."""
    response = client.get(
        "/api/v1/questions/categories/99999",
        headers={"Host": "localhost"}
    )
    
    assert response.status_code == 404
    data = response.json()
    
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]
    print(f"[OK] Category not found error: {data['error']['code']}")


def test_all_errors_have_request_id():
    """Verify all error responses include request_id for debugging."""
    test_cases = [
        ("/api/v1/auth/register", "POST", {}),
        ("/api/v1/questions/categories/99999", "GET", None),
        ("/api/v1/questions/by-age/5", "GET", None),
    ]
    
    for path, method, body in test_cases:
        if method == "POST":
            response = client.post(path, json=body, headers={"Host": "localhost"})
        else:
            response = client.get(path, headers={"Host": "localhost"})
        
        data = response.json()
        assert "request_id" in data.get("error", {}), f"Missing request_id for {path}"
        print(f"[OK] {path} has request_id: {data['error']['request_id'][:20]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
