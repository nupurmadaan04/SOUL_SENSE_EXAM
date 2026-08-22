#!/usr/bin/env python3
"""
Test user creation script for SoulSense Tkinter app.
Creates sample user accounts for testing the login/signup functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth import AuthManager

def create_test_users():
    """Create test user accounts"""
    auth = AuthManager()

    test_users = [
        {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 25,
            "gender": "F",
            "password": "TestPass123!"
        },
        {
            "name": "Bob Smith",
            "email": "bob@example.com",
            "age": 30,
            "gender": "M",
            "password": "TestPass123!"
        },
        {
            "name": "Charlie Brown",
            "email": "charlie@example.com",
            "age": 22,
            "gender": "M",
            "password": "TestPass123!"
        },
        {
            "name": "Diana Prince",
            "email": "diana@example.com",
            "age": 28,
            "gender": "F",
            "password": "TestPass123!"
        }
    ]

    print("Creating test user accounts...")
    print("=" * 50)

    for user in test_users:
        success, message = auth.register_user(
            user["name"],
            user["email"],
            user["age"],
            user["gender"],
            user["password"]
        )

        if success:
            print(f"✅ Created: {user['name']} ({user['email']})")
        else:
            print(f"❌ Failed: {user['name']} - {message}")

    print("=" * 50)
    print("Test users created successfully!")
    print("\nYou can now login with these credentials:")
    print("Username: [user's name] | Password: TestPass123!")

if __name__ == "__main__":
    create_test_users()