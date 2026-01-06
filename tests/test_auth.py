import pytest
import tempfile
import os
from app.auth import AuthManager
from app.db import get_connection

class TestAuth:
    def setup_method(self):
        """Setup test with temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.auth_manager = AuthManager()
        # Override the database path for testing
        self.original_get_connection = get_connection
        
    def teardown_method(self):
        """Cleanup temporary database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_user_registration(self):
        """Test user registration"""
        success, message = self.auth_manager.register_user("testuser", "password123")
        assert success == True
        assert "successful" in message
    
    def test_duplicate_username(self):
        """Test duplicate username registration"""
        self.auth_manager.register_user("testuser", "password123")
        success, message = self.auth_manager.register_user("testuser", "password456")
        assert success == False
        assert "already exists" in message
    
    def test_short_username(self):
        """Test short username validation"""
        success, message = self.auth_manager.register_user("ab", "password123")
        assert success == False
        assert "at least 3 characters" in message
    
    def test_short_password(self):
        """Test short password validation"""
        success, message = self.auth_manager.register_user("testuser", "12345")
        assert success == False
        assert "at least 6 characters" in message
    
    def test_user_authentication(self):
        """Test user login"""
        self.auth_manager.register_user("testuser", "password123")
        success, message = self.auth_manager.authenticate_user("testuser", "password123")
        assert success == True
        assert "successful" in message
    
    def test_wrong_password(self):
        """Test wrong password"""
        self.auth_manager.register_user("testuser", "password123")
        success, message = self.auth_manager.authenticate_user("testuser", "wrongpassword")
        assert success == False
        assert "Invalid" in message
    
    def test_nonexistent_user(self):
        """Test login with nonexistent user"""
        success, message = self.auth_manager.authenticate_user("nonexistent", "password123")
        assert success == False
        assert "Invalid" in message