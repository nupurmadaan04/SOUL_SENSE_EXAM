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
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"


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


def get_auth_token(username: str = "sync_test_user", password: str = "testpass123") -> Optional[str]:
    """Register and login to get auth token."""
    # Try to register first
    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "password": password}
    )
    
    # Login to get token
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password}
    )
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        return token_data.get("access_token")
    else:
        print(f"Failed to get auth token: {login_response.text}")
        return None


def test_health():
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print_response("GET /health", response)
    return response.status_code == 200


def test_create_setting(token: str):
    """Test creating a new setting."""
    print("\n" + "="*60)
    print("TEST: Create Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.put(
        f"{BASE_URL}/api/sync/settings/theme",
        json={"value": "dark"},
        headers=headers
    )
    print_response("PUT /api/sync/settings/theme", response)
    
    return response.status_code == 200


def test_get_setting(token: str):
    """Test getting a single setting."""
    print("\n" + "="*60)
    print("TEST: Get Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/sync/settings/theme",
        headers=headers
    )
    print_response("GET /api/sync/settings/theme", response)
    
    return response.status_code == 200


def test_get_all_settings(token: str):
    """Test getting all settings."""
    print("\n" + "="*60)
    print("TEST: Get All Settings")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a few more settings
    requests.put(f"{BASE_URL}/api/sync/settings/language", json={"value": "en"}, headers=headers)
    requests.put(f"{BASE_URL}/api/sync/settings/fontSize", json={"value": 16}, headers=headers)
    requests.put(f"{BASE_URL}/api/sync/settings/notifications", json={"value": {"email": True, "push": False}}, headers=headers)
    
    response = requests.get(
        f"{BASE_URL}/api/sync/settings",
        headers=headers
    )
    print_response("GET /api/sync/settings", response)
    
    return response.status_code == 200


def test_update_setting_with_version(token: str):
    """Test updating a setting with version check."""
    print("\n" + "="*60)
    print("TEST: Update Setting with Version")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, get current version
    get_response = requests.get(
        f"{BASE_URL}/api/sync/settings/theme",
        headers=headers
    )
    
    if get_response.status_code == 200:
        current = get_response.json()
        current_version = current.get("version", 1)
        print(f"Current version: {current_version}")
        
        # Update with correct version
        response = requests.put(
            f"{BASE_URL}/api/sync/settings/theme",
            json={"value": "light", "expected_version": current_version},
            headers=headers
        )
        print_response("PUT /api/sync/settings/theme (with correct version)", response)
        return response.status_code == 200
    
    return False


def test_conflict_detection(token: str):
    """Test conflict detection with wrong version."""
    print("\n" + "="*60)
    print("TEST: Conflict Detection (Wrong Version)")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to update with wrong version
    response = requests.put(
        f"{BASE_URL}/api/sync/settings/theme",
        json={"value": "another_theme", "expected_version": 999},
        headers=headers
    )
    print_response("PUT /api/sync/settings/theme (with wrong version)", response)
    
    # Should return 409 Conflict
    return response.status_code == 409


def test_delete_setting(token: str):
    """Test deleting a setting."""
    print("\n" + "="*60)
    print("TEST: Delete Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a setting to delete
    requests.put(
        f"{BASE_URL}/api/sync/settings/to_delete",
        json={"value": "temporary"},
        headers=headers
    )
    
    # Delete it
    response = requests.delete(
        f"{BASE_URL}/api/sync/settings/to_delete",
        headers=headers
    )
    print_response("DELETE /api/sync/settings/to_delete", response)
    
    return response.status_code == 204


def test_batch_upsert(token: str):
    """Test batch upsert settings."""
    print("\n" + "="*60)
    print("TEST: Batch Upsert Settings")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{BASE_URL}/api/sync/settings/batch",
        json={
            "settings": [
                {"key": "batch_setting1", "value": "value1"},
                {"key": "batch_setting2", "value": {"nested": "object"}},
                {"key": "batch_setting3", "value": [1, 2, 3]}
            ]
        },
        headers=headers
    )
    print_response("POST /api/sync/settings/batch", response)
    
    return response.status_code == 200


def test_unauthenticated_access():
    """Test that unauthenticated requests are rejected."""
    print("\n" + "="*60)
    print("TEST: Unauthenticated Access (should fail)")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/sync/settings")
    print_response("GET /api/sync/settings (no auth)", response)
    
    # Should return 401 Unauthorized
    return response.status_code == 401


def test_not_found(token: str):
    """Test 404 for non-existent setting."""
    print("\n" + "="*60)
    print("TEST: Get Non-Existent Setting")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/sync/settings/nonexistent_key_12345",
        headers=headers
    )
    print_response("GET /api/sync/settings/nonexistent_key_12345", response)
    
    return response.status_code == 404


def run_all_tests():
    """Run all Settings Sync API tests."""
    print("\n" + "="*70)
    print(" "*10 + "SETTINGS SYNCHRONIZATION API TESTING")
    print(" "*10 + "Issue #396: Create Settings Synchronization API")
    print("="*70)
    
    # Check if server is running
    try:
        if not test_health():
            print("\n❌ Server is not responding. Please start the FastAPI server:")
            print("   cd backend/fastapi")
            print("   uvicorn app.main:app --reload")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server. Please start the FastAPI server:")
        print("   cd backend/fastapi")
        print("   uvicorn app.main:app --reload")
        return
    
    print("\n✅ Server is running!")
    
    # Get auth token
    print("\n" + "-"*60)
    print("Getting authentication token...")
    token = get_auth_token()
    
    if not token:
        print("❌ Failed to get auth token. Cannot proceed with tests.")
        return
    
    print("✅ Got auth token!")
    
    # Run tests
    results = []
    
    results.append(("Unauthenticated Access", test_unauthenticated_access()))
    results.append(("Create Setting", test_create_setting(token)))
    results.append(("Get Setting", test_get_setting(token)))
    results.append(("Get All Settings", test_get_all_settings(token)))
    results.append(("Update with Version", test_update_setting_with_version(token)))
    results.append(("Conflict Detection", test_conflict_detection(token)))
    results.append(("Delete Setting", test_delete_setting(token)))
    results.append(("Batch Upsert", test_batch_upsert(token)))
    results.append(("Not Found", test_not_found(token)))
    
    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-"*60)
    print(f"Total: {passed} passed, {failed} failed")
    print("="*70)
    
    print("\n📖 Interactive documentation available at:")
    print(f"  • Swagger UI: {BASE_URL}/docs")
    print(f"  • ReDoc:      {BASE_URL}/redoc")


if __name__ == "__main__":
    run_all_tests()
