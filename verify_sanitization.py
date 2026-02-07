import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend", "fastapi"))

from api.utils.sanitization import sanitize_string, clean_identifier
from api.schemas import UserCreate, UserLogin, PasswordResetRequest

def test_sanitization():
    print("Testing sanitize_string...")
    # XSS attempt
    val = "<script>alert('xss')</script>"
    sanitized = sanitize_string(val)
    print(f"Original: {val} -> Sanitized: {sanitized}")
    assert "&lt;script&gt;" in sanitized
    
    # Null bytes and control characters
    val = "Hello\0World\x01!"
    sanitized = sanitize_string(val)
    print(f"Original: {val!r} -> Sanitized: {sanitized!r}")
    assert "\0" not in sanitized
    assert "\x01" not in sanitized
    
    # Unicode normalization
    val = "User\u200bName" # zero width space
    sanitized = sanitize_string(val)
    print(f"Original: {val!r} -> Sanitized: {sanitized!r}")
    assert "\u200b" not in sanitized

    print("\nTesting clean_identifier...")
    # Email with spaces and mixed case
    email = "  Test.User@Example.Com  "
    cleaned = clean_identifier(email)
    print(f"Original: {email!r} -> Cleaned: {cleaned!r}")
    assert cleaned == "test.user@example.com"
    
    # Username with control chars
    user = "admin\x00_user"
    cleaned = clean_identifier(user)
    print(f"Original: {user!r} -> Cleaned: {cleaned!r}")
    assert cleaned == "admin_user"

def test_pydantic_integration():
    print("\nTesting Pydantic Integration...")
    
    # UserCreate
    data = {
        "username": "  New_User  ",
        "email": "USER@DOMAIN.COM",
        "password": "securepassword123",
        "first_name": "<b>John</b>",
        "last_name": "  Doe  "
    }
    user = UserCreate(**data)
    print(f"UserCreate -> username: {user.username!r}, email: {user.email!r}, first_name: {user.first_name!r}")
    assert user.username == "new_user"
    assert user.email == "user@domain.com"
    assert "&lt;b&gt;John&lt;/b&gt;" in user.first_name
    
    # UserLogin
    login_data = {"username": "  ADMIN  ", "password": "any"}
    login = UserLogin(**login_data)
    print(f"UserLogin -> username: {login.username!r}")
    assert login.username == "admin"

if __name__ == "__main__":
    try:
        test_sanitization()
        test_pydantic_integration()
        print("\n✅ All sanitization tests passed!")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
