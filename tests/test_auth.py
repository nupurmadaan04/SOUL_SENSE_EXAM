import pytest
import bcrypt
from app.auth import AuthManager

class TestAuth:
    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        """
        Auto-use fixture that ensures temp_db is set up for every test method.
        The temp_db fixture in conftest.py already patches app.db, so AuthManager 
        will use the temp DB.
        """
        self.auth_manager = AuthManager()
    
    def test_password_hashing_with_bcrypt(self):
        """Test that passwords are properly hashed with bcrypt."""
        password = "test_password_123"
        hashed = self.auth_manager.hash_password(password)
        
        # Hash should not be the plaintext password
        assert hashed != password
        # Hash should be a valid bcrypt hash
        assert hashed.startswith('$2')  # bcrypt hashes start with $2
    
    def test_password_verification(self):
        """Test password verification against bcrypt hash."""
        password = "test_password_123"
        hashed = self.auth_manager.hash_password(password)
        
        # Correct password should verify
        assert self.auth_manager.verify_password(password, hashed) == True
        
        # Wrong password should not verify
        assert self.auth_manager.verify_password("wrong_password", hashed) == False
    
    def test_user_registration(self):
        # Test successful registration
        success, message = self.auth_manager.register_user("testuser", "TestPass123!")
        assert success == True
        assert "successful" in message
        
        # Test duplicate username
        success, message = self.auth_manager.register_user("testuser", "TestPass456!")
        assert success == False
        assert "already exists" in message
        
        # Test short username
        success, message = self.auth_manager.register_user("ab", "TestPass123!")
        assert success == False
        assert "at least 3 characters" in message
        
        # Test short password
        success, message = self.auth_manager.register_user("newuser", "123")
        assert success == False
        assert "at least 8 characters" in message
    
    def test_user_login(self):
        # Register a user first
        self.auth_manager.register_user("testuser", "TestPass123!")
        
        # Test successful login
        success, message = self.auth_manager.login_user("testuser", "TestPass123!")
        assert success == True
        assert "successful" in message
        assert self.auth_manager.current_user == "testuser"
        
        # Test wrong password
        success, message = self.auth_manager.login_user("testuser", "wrongpassword")
        assert success == False
        assert "Invalid" in message
        
        # Test non-existent user
        success, message = self.auth_manager.login_user("nonexistent", "TestPass123!")
        assert success == False
        assert "Invalid" in message
    
    def test_user_logout(self):
        # Register and login
        self.auth_manager.register_user("testuser", "TestPass123!")
        self.auth_manager.login_user("testuser", "TestPass123!")
        
        # Verify logged in
        assert self.auth_manager.is_logged_in() == True
        
        # Logout
        self.auth_manager.logout_user()
        
        # Verify logged out
        assert self.auth_manager.is_logged_in() == False
        assert self.auth_manager.current_user is None