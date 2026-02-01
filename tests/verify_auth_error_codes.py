import os
import sys

# CRITICAL: Set environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "development"

from fastapi.testclient import TestClient
from api.main import app
from api.constants.errors import ErrorCode
from api.root_models import Base, User, PersonalProfile
from api.services.db_service import engine, SessionLocal

# Force table creation
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_registration_duplicate_codes():
    # Attempt to register twice
    user_data = {
        "username": "test_error_codes",
        "email": "error@example.com",
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "Error",
        "age": 25,
        "gender": "Other"
    }
    
    # First time: Success
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Second time: Should fail with REG001 or REG002
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert data["code"] in [ErrorCode.REG_USERNAME_EXISTS.value, ErrorCode.REG_EMAIL_EXISTS.value]
    assert "message" in data

def test_login_invalid_code():
    # OAuth2PasswordRequestForm uses form data
    response = client.post("/api/v1/auth/login", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS.value
    assert "message" in data

if __name__ == "__main__":
    try:
        # We need to use Lifespan/Events if we want app to use the same memory DB
        # But for simple verification, this should be enough if engine is shared
        test_registration_duplicate_codes()
        print("✅ Registration error codes verified")
        test_login_invalid_code()
        print("✅ Login error codes verified")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
