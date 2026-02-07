import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.fastapi.api.schemas import UserCreate, UserLogin, UserUpdate, PersonalProfileUpdate
from pydantic import ValidationError

def test_user_create():
    print("Testing UserCreate...")
    user = UserCreate(
        username="  User123  ",
        email="  Test@Example.COM  ",
        password="Password123!",
        first_name="  John  ",
        last_name="  Doe  ",
        age=25,
        gender="Male"
    )
    print(f"✅ Normalization: {user.username=}, {user.email=}")
    assert user.username == "user123"
    assert user.email == "test@example.com"

def test_user_update():
    print("\nTesting UserUpdate...")
    # Test Normalization
    user = UserUpdate(username="  NewUser  ")
    print(f"✅ Normalization: {user.username=}")
    assert user.username == "newuser"

    # Test Reserved Username
    try:
        UserUpdate(username="support")
        print("❌ Reserved username check failed")
    except ValidationError:
        print("✅ Reserved username blocked")

def test_profile_update():
    print("\nTesting PersonalProfileUpdate...")
    profile = PersonalProfileUpdate(email="  NEW_EMAIL@example.com  ")
    print(f"✅ Normalization: {profile.email=}")
    assert profile.email == "new_email@example.com"

if __name__ == "__main__":
    test_user_create()
    test_user_update()
    test_profile_update()
