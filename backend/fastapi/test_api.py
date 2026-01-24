"""
Simple API test script to verify Assessment and Question endpoints.
Run this after starting the FastAPI server to test the endpoints.

Usage:
    python test_api.py
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


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
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/api/v1/health")
    print_response("GET /health", response)
    return response.status_code == 200


def test_questions():
    """Test question endpoints."""
    print("\n" + "="*60)
    print("TESTING QUESTION ENDPOINTS")
    print("="*60)
    
    # Test: Get all questions (limited)
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"limit": 5})
    print_response("GET /api/v1/questions?limit=5", response)
    
    # Test: Get questions by age
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"age": 25, "limit": 10})
    print_response("GET /api/v1/questions?age=25&limit=10", response)
    
    # Test: Get questions by age (alternative endpoint)
    response = requests.get(f"{BASE_URL}/api/v1/questions/by-age/30", params={"limit": 5})
    print_response("GET /api/v1/questions/by-age/30?limit=5", response)
    
    # Test: Get categories
    response = requests.get(f"{BASE_URL}/api/v1/questions/categories")
    print_response("GET /api/v1/questions/categories", response)
    
    # Test: Get specific question (if exists)
    response = requests.get(f"{BASE_URL}/api/v1/questions/1")
    print_response("GET /api/v1/questions/1", response)


def test_assessments():
    """Test assessment endpoints."""
    print("\n" + "="*60)
    print("TESTING ASSESSMENT ENDPOINTS")
    print("="*60)
    
    # Test: Get assessments (paginated)
    response = requests.get(f"{BASE_URL}/api/v1/assessments", params={"page": 1, "page_size": 5})
    print_response("GET /api/v1/assessments?page=1&page_size=5", response)
    
    # Test: Get assessment stats
    response = requests.get(f"{BASE_URL}/api/v1/assessments/stats")
    print_response("GET /api/v1/assessments/stats", response)
    
    # Test: Get specific assessment (if exists)
    response = requests.get(f"{BASE_URL}/api/v1/assessments/1")
    print_response("GET /api/v1/assessments/1", response)


def test_filters():
    """Test filtering capabilities."""
    print("\n" + "="*60)
    print("TESTING FILTERS AND EDGE CASES")
    print("="*60)
    
    # Test: Filter assessments by username
    response = requests.get(f"{BASE_URL}/api/v1/assessments", params={"username": "testuser"})
    print_response("GET /api/v1/assessments?username=testuser", response)
    
    # Test: Filter questions by category
    response = requests.get(f"{BASE_URL}/api/v1/questions", params={"category_id": 1, "limit": 5})
    print_response("GET /api/v1/questions?category_id=1&limit=5", response)
    
    # Test: Invalid age (should return 400)
    response = requests.get(f"{BASE_URL}/api/v1/questions/by-age/5")
    print_response("GET /api/v1/questions/by-age/5 (Invalid age)", response)


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*70)
    print(" "*15 + "SOUL SENSE API TESTING")
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
    
    print("\n✅ Server is running!\n")
    
    # Run tests
    test_questions()
    test_assessments()
    test_filters()
    
    print("\n" + "="*70)
    print("✅ Testing complete!")
    print("\nInteractive documentation available at:")
    print(f"  • Swagger UI: {BASE_URL}/docs")
    print(f"  • ReDoc:      {BASE_URL}/redoc")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
