import pytest
import tempfile
import os
from app.auth import create_user, authenticate_user
from app.models import ensure_users_schema, hash_password, verify_password
from app.db import get_connection

def test_password_hashing():
    password = "testpass123"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpass", hashed)

def test_create_user():
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        import sqlite3
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        ensure_users_schema(cursor)
        conn.commit()
        
        # Test user creation
        success, message = create_user("testuser", "testpass", conn)
        print(f"Create user result: {success}, {message}")  # Debug
        assert success
        assert "successfully" in message
        
        # Test duplicate user
        success, message = create_user("testuser", "testpass", conn)
        assert not success
        assert "already exists" in message
        
        # Test authentication
        success, message = authenticate_user("testuser", "testpass", conn)
        assert success
        
        # Test wrong password
        success, message = authenticate_user("testuser", "wrongpass", conn)
        assert not success
        
        # Test non-existent user
        success, message = authenticate_user("nonexistent", "testpass", conn)
        assert not success
        
        conn.close()
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)