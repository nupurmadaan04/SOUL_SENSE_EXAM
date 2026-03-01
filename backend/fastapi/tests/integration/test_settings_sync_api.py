"""
Settings Synchronization API Test Script

Tests the Settings Sync API endpoints for Issue #396.
Run this after starting the FastAPI server to test the endpoints.

Usage:
    cd backend/fastapi
    python test_settings_sync_api.py
"""
import requests
import json
import pytest
from typing import Dict, Any, Optional

BASE_URL = "http://127.0.0.1:8000"


def print_response(endpoint: str, response: requests.Response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"Endpoint: {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"{'='*60}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(f"Response: {response.text}")


@pytest.fixture(scope="module")
def token():
    """Register and login to get auth token."""
    username = "sync_test_user"
    password = "testpass123"
    
    # Try to register first
    requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={"username": username, "password": password}
    )
    
    # Login to get token
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        return token_data.get("access_token")
    else:
        pytest.fail(f"Failed to get auth token: {login_response.text}")


def test_health():
    """Test health endpoint - checks system dependencies."""
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print_response("GET /api/v1/health", response)
    
    # Health endpoint returns 200 when healthy, 503 when critical dependencies fail
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data
    
    # Check services structure
    services = data["services"]
    assert "database" in services
    assert "redis" in services
    
    # Each service should have status and may have latency/message
    for service_name, service_info in services.items():
        assert "status" in service_info
        assert service_info["status"] in ["healthy", "unhealthy"]


def test_create_setting(token: str):
    """Test creating a new setting."""
    print("\n" + "="*60)
    print("TEST: Create Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.put(
        f"{BASE_URL}/api/v1/sync/theme",
        json={"value": "dark"},
        headers=headers
    )
    print_response("PUT /api/v1/sync/theme", response)
    
    assert response.status_code == 200


def test_get_setting(token: str):
    """Test getting a single setting."""
    print("\n" + "="*60)
    print("TEST: Get Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/sync/theme",
        headers=headers
    )
    print_response("GET /api/v1/sync/theme", response)
    
    assert response.status_code == 200


def test_get_all_settings(token: str):
    """Test getting all settings."""
    print("\n" + "="*60)
    print("TEST: Get All Settings")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a few more settings
    requests.put(f"{BASE_URL}/api/v1/sync/language", json={"value": "en"}, headers=headers)
    requests.put(f"{BASE_URL}/api/v1/sync/fontSize", json={"value": 16}, headers=headers)
    requests.put(f"{BASE_URL}/api/v1/sync/notifications", json={"value": {"email": True, "push": False}}, headers=headers)
    
    response = requests.get(
        f"{BASE_URL}/api/v1/sync",
        headers=headers
    )
    print_response("GET /api/v1/sync", response)
    
    assert response.status_code == 200


def test_update_setting_with_version(token: str):
    """Test updating a setting with version check."""
    print("\n" + "="*60)
    print("TEST: Update Setting with Version")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, get current version
    get_response = requests.get(
        f"{BASE_URL}/api/v1/sync/theme",
        headers=headers
    )
    
    assert get_response.status_code == 200
    current = get_response.json()
    current_version = current.get("version", 1)
    print(f"Current version: {current_version}")
    
    # Update with correct version
    response = requests.put(
        f"{BASE_URL}/api/v1/sync/theme",
        json={"value": "light", "expected_version": current_version},
        headers=headers
    )
    print_response("PUT /api/v1/sync/theme (with correct version)", response)
    assert response.status_code == 200


def test_conflict_detection(token: str):
    """Test conflict detection with wrong version."""
    print("\n" + "="*60)
    print("TEST: Conflict Detection (Wrong Version)")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to update with wrong version
    response = requests.put(
        f"{BASE_URL}/api/v1/sync/theme",
        json={"value": "another_theme", "expected_version": 999},
        headers=headers
    )
    print_response("PUT /api/v1/sync/theme (with wrong version)", response)
    
    # Should return 409 Conflict
    assert response.status_code == 409


def test_delete_setting(token: str):
    """Test deleting a setting."""
    print("\n" + "="*60)
    print("TEST: Delete Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a setting to delete
    requests.put(
        f"{BASE_URL}/api/v1/sync/to_delete",
        json={"value": "temporary"},
        headers=headers
    )
    
    # Delete it
    response = requests.delete(
        f"{BASE_URL}/api/v1/sync/to_delete",
        headers=headers
    )
    print_response("DELETE /api/v1/sync/to_delete", response)
    
    assert response.status_code == 204


def test_batch_upsert(token: str):
    """Test batch upsert settings."""
    print("\n" + "="*60)
    print("TEST: Batch Upsert Settings")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/v1/sync/batch",
        json={
            "settings": [
                {"key": "batch_setting1", "value": "value1"},
                {"key": "batch_setting2", "value": {"nested": "object"}},
                {"key": "batch_setting3", "value": [1, 2, 3]}
            ]
        },
        headers=headers
    )
    print_response("POST /api/v1/sync/batch", response)
    
    assert response.status_code == 200


def test_unauthenticated_access():
    """Test that unauthenticated requests are rejected."""
    print("\n" + "="*60)
    print("TEST: Unauthenticated Access (should fail)")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/v1/sync")
    print_response("GET /api/v1/sync (no auth)", response)
    
    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_not_found(token: str):
    """Test 404 for non-existent setting."""
    print("\n" + "="*60)
    print("TEST: Get Non-Existent Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/sync/nonexistent_key_12345",
        headers=headers
    )
    print_response("GET /api/v1/sync/nonexistent_key_12345", response)
    
    assert response.status_code == 404
