"""
Quick Test Script for User and Profile CRUD APIs

This script demonstrates the usage of the newly implemented CRUD APIs.
Run the FastAPI server first: uvicorn app.main:app --reload
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def print_response(response, description):
    """Print formatted response."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Status: {response.status_code}")
    if response.text:
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response: {response.text}")
    print(f"{'='*60}")


def test_crud_apis():
    """Test the complete CRUD API flow."""
    
    # Test credentials
    username = "testuser_crud"
    password = "testpass123"
    
    print("\n" + "="*60)
    print("USER AND PROFILE CRUD API TEST")
    print("="*60)
    
    # 1. Register a new user
    print("\n1. REGISTERING NEW USER...")
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "password": password}
    )
    print_response(response, "Register User")
    
    if response.status_code != 200:
        print("❌ Registration failed. User might already exist.")
        print("Continuing with login...")
    
    # 2. Login to get token
    print("\n2. LOGGING IN...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password}
    )
    print_response(response, "Login")
    
    if response.status_code != 200:
        print("❌ Login failed. Exiting.")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get current user info
    print("\n3. GETTING CURRENT USER INFO...")
    response = requests.get(f"{BASE_URL}/users/me", headers=headers)
    print_response(response, "Get Current User")
    
    # 4. Get user details
    print("\n4. GETTING USER DETAILS...")
    response = requests.get(f"{BASE_URL}/users/me/detail", headers=headers)
    print_response(response, "Get User Details")
    
    # 5. Create user settings
    print("\n5. CREATING USER SETTINGS...")
    settings_data = {
        "theme": "dark",
        "question_count": 15,
        "sound_enabled": True,
        "notifications_enabled": True,
        "language": "en"
    }
    response = requests.post(
        f"{BASE_URL}/profiles/settings",
        headers=headers,
        json=settings_data
    )
    print_response(response, "Create User Settings")
    
    # 6. Create personal profile
    print("\n6. CREATING PERSONAL PROFILE...")
    personal_data = {
        "occupation": "Software Developer",
        "education": "Bachelor's Degree in Computer Science",
        "bio": "Passionate about AI and mental health technology",
        "email": "testuser@example.com",
        "hobbies": "Reading, Hiking, Photography"
    }
    response = requests.post(
        f"{BASE_URL}/profiles/personal",
        headers=headers,
        json=personal_data
    )
    print_response(response, "Create Personal Profile")
    
    # 7. Create user strengths
    print("\n7. CREATING USER STRENGTHS...")
    strengths_data = {
        "top_strengths": '["Problem Solving", "Creativity", "Empathy"]',
        "areas_for_improvement": '["Public Speaking", "Time Management"]',
        "current_challenges": '["Work-life balance"]',
        "learning_style": "Visual",
        "goals": "Complete certification, improve presentation skills"
    }
    response = requests.post(
        f"{BASE_URL}/profiles/strengths",
        headers=headers,
        json=strengths_data
    )
    print_response(response, "Create User Strengths")
    
    # 8. Create emotional patterns
    print("\n8. CREATING EMOTIONAL PATTERNS...")
    patterns_data = {
        "common_emotions": '["Calmness", "Excitement", "Anxiety"]',
        "emotional_triggers": "Tight deadlines, public speaking",
        "coping_strategies": "Deep breathing, taking breaks, exercise",
        "preferred_support": "Problem-solving approach"
    }
    response = requests.post(
        f"{BASE_URL}/profiles/emotional-patterns",
        headers=headers,
        json=patterns_data
    )
    print_response(response, "Create Emotional Patterns")
    
    # 9. Get complete profile
    print("\n9. GETTING COMPLETE PROFILE...")
    response = requests.get(f"{BASE_URL}/users/me/complete", headers=headers)
    print_response(response, "Get Complete Profile")
    
    # 10. Update user settings
    print("\n10. UPDATING USER SETTINGS...")
    update_data = {"theme": "light", "question_count": 20}
    response = requests.put(
        f"{BASE_URL}/profiles/settings",
        headers=headers,
        json=update_data
    )
    print_response(response, "Update User Settings")
    
    # 11. Update personal profile
    print("\n11. UPDATING PERSONAL PROFILE...")
    update_data = {"bio": "Updated bio: Tech enthusiast and mental health advocate"}
    response = requests.put(
        f"{BASE_URL}/profiles/personal",
        headers=headers,
        json=update_data
    )
    print_response(response, "Update Personal Profile")
    
    # 12. Get user details again to see changes
    print("\n12. GETTING UPDATED USER DETAILS...")
    response = requests.get(f"{BASE_URL}/users/me/detail", headers=headers)
    print_response(response, "Get Updated User Details")
    
    # 13. List all users (admin endpoint)
    print("\n13. LISTING ALL USERS...")
    response = requests.get(f"{BASE_URL}/users/?skip=0&limit=5", headers=headers)
    print_response(response, "List Users")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED!")
    print("="*60)
    print("\nNOTE: To clean up, you can delete profiles individually")
    print("or delete the user (which cascades to all profiles).")
    print(f"\nTo delete user: DELETE {BASE_URL}/users/me")
    print("="*60)


if __name__ == "__main__":
    print("\n🚀 Starting CRUD API Tests...")
    print("⚠️  Make sure the FastAPI server is running:")
    print("   cd backend/fastapi")
    print("   uvicorn app.main:app --reload\n")
    
    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running!")
            test_crud_apis()
        else:
            print("❌ Server is not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the FastAPI server first.")
        print("   Run: uvicorn app.main:app --reload")
