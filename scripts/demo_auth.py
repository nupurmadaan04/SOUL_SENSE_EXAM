#!/usr/bin/env python3
"""
Demo script to test authentication functionality
"""

from app.auth import AuthManager

def demo_auth():
    auth = AuthManager()
    
    print("=== Soul Sense Authentication Demo ===\n")
    
    # Test registration
    print("1. Testing user registration...")
    success, message = auth.register_user("demo_user", "demo_password123")
    print(f"Registration: {message}")
    
    # Test duplicate registration
    print("\n2. Testing duplicate registration...")
    success, message = auth.register_user("demo_user", "another_password")
    print(f"Duplicate registration: {message}")
    
    # Test login with correct credentials
    print("\n3. Testing login with correct credentials...")
    success, message = auth.authenticate_user("demo_user", "demo_password123")
    print(f"Login (correct): {message}")
    
    # Test login with wrong credentials
    print("\n4. Testing login with wrong credentials...")
    success, message = auth.authenticate_user("demo_user", "wrong_password")
    print(f"Login (wrong): {message}")
    
    # Test validation
    print("\n5. Testing validation...")
    success, message = auth.register_user("ab", "123")
    print(f"Short username/password: {message}")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demo_auth()