"""
Simple API test script to verify Assessment and Question endpoints.
Run this after starting the FastAPI server to test the endpoints.

Usage:
    python test_api.py
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"


def print_response(endpoint: str, response: requests.Response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"Endpoint: {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"{'='*60}")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")


def test_health():
    """Test health endpoint - checks system dependencies."""
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print_response("GET /health", response)
    
    # Health endpoint returns 200 when healthy, 503 when critical dependencies fail
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data



def test_questions():
    """Test question endpoints."""
    print("\n" + "="*60)
    print("TESTING QUESTION ENDPOINTS")
    print("="*60)
    
    # Test: Get all questions (limited)
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"limit": 5})
    print_response("GET /api/v1/questions?limit=5", response)
    assert response.status_code == 200
    
    # Test: Get questions by age
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"age": 25, "limit": 10})
    print_response("GET /api/v1/questions?age=25&limit=10", response)
    assert response.status_code == 200
    
    # Test: Get questions by age (alternative endpoint)
    response = requests.get(f"{BASE_URL}/api/v1/questions/by-age/30", params={"limit": 5})
    print_response("GET /api/v1/questions/by-age/30?limit=5", response)
    assert response.status_code == 200
    
    # Test: Get categories
    response = requests.get(f"{BASE_URL}/api/v1/questions/categories")
    print_response("GET /api/v1/questions/categories", response)
    assert response.status_code == 200
    
    # Test: Get specific question (if exists)
    response = requests.get(f"{BASE_URL}/api/v1/questions/1")
    print_response("GET /api/v1/questions/1", response)
    # Note: validation depends on DB state, so we just check it doesn't crash (500)
    assert response.status_code in [200, 404]


def test_assessments():
    """Test assessment endpoints."""
    print("\n" + "="*60)
    print("TESTING ASSESSMENT ENDPOINTS")
    print("="*60)
    
    # Test: Get assessments (paginated)
    response = requests.get(f"{BASE_URL}/api/v1/assessments", params={"page": 1, "page_size": 5})
    print_response("GET /api/v1/assessments?page=1&page_size=5", response)
    assert response.status_code == 200
    
    # Test: Get assessment stats
    response = requests.get(f"{BASE_URL}/api/v1/assessments/stats")
    print_response("GET /api/v1/assessments/stats", response)
    assert response.status_code == 200
    
    # Test: Get specific assessment (if exists)
    response = requests.get(f"{BASE_URL}/api/v1/assessments/1")
    print_response("GET /api/v1/assessments/1", response)
    assert response.status_code in [200, 404]


def test_filters():
    """Test filtering capabilities."""
    print("\n" + "="*60)
    print("TESTING FILTERS AND EDGE CASES")
    print("="*60)
    
    # Test: Filter assessments by username
    response = requests.get(f"{BASE_URL}/api/v1/assessments", params={"username": "testuser"})
    print_response("GET /api/v1/assessments?username=testuser", response)
    assert response.status_code == 200
    
    # Test: Filter questions by category
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"category_id": 1, "limit": 5})
    print_response("GET /api/v1/questions?category_id=1&limit=5", response)
    assert response.status_code == 200
    
    # Test: Invalid age (should return 400)
    response = requests.get(f"{BASE_URL}/api/v1/questions/by-age/5")
    print_response("GET /api/v1/questions/by-age/5 (Invalid age)", response)
    assert response.status_code == 400
