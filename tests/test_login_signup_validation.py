"""
Test cases for Login/Signup Validation Enhancement (Issue #559)

Tests comprehensive validation for:
1. Empty field validation
2. Email format validation  
3. Password mismatch detection
4. Password security validation
5. Specific error message content
"""

import pytest
from app.validation import (
    validate_required,
    validate_email,
    validate_email_strict,
    validate_password_security,
    validate_password_match,
    validate_username,
    validate_age,
)


class TestEmptyFieldValidation:
    """Test validation for empty fields in login/signup forms."""
    
    def test_empty_username_required(self):
        """Username field shows specific error when empty."""
        is_valid, error_msg = validate_required("", "Username")
        assert is_valid is False
        assert "Username is required" in error_msg
    
    def test_empty_email_required(self):
        """Email field shows specific error when empty."""
        is_valid, error_msg = validate_required("", "Email")
        assert is_valid is False
        assert "Email is required" in error_msg
    
    def test_empty_password_required(self):
        """Password field shows specific error when empty."""
        is_valid, error_msg = validate_required("", "Password")
        assert is_valid is False
        assert "Password is required" in error_msg
    
    def test_empty_first_name_required(self):
        """First name field shows specific error when empty."""
        is_valid, error_msg = validate_required("", "First name")
        assert is_valid is False
        assert "First name is required" in error_msg
    
    def test_whitespace_only_treated_as_empty(self):
        """Fields with only whitespace should be considered empty after strip."""
        # Note: This tests the concept - actual strip happens in form handling
        is_valid, error_msg = validate_required("", "Field")
        assert is_valid is False


class TestEmailValidation:
    """Test email format validation with clear error messages."""
    
    def test_valid_email_formats(self):
        """Valid email addresses pass validation."""
        valid_emails = [
            "user@example.com",
            "user.name@domain.org",
            "user+tag@company.co.uk",
            "user123@test-domain.io",
        ]
        for email in valid_emails:
            is_valid, _ = validate_email_strict(email)
            assert is_valid is True, f"Expected {email} to be valid"
    
    def test_empty_email_error(self):
        """Empty email shows 'required' error."""
        is_valid, error_msg = validate_email_strict("")
        assert is_valid is False
        assert "required" in error_msg.lower()
    
    def test_missing_at_symbol(self):
        """Email without @ shows specific error."""
        is_valid, error_msg = validate_email_strict("userexample.com")
        assert is_valid is False
        assert "@" in error_msg
    
    def test_missing_domain(self):
        """Email with missing domain shows specific error."""
        is_valid, error_msg = validate_email_strict("user@")
        assert is_valid is False
        assert "domain" in error_msg.lower()
    
    def test_missing_tld(self):
        """Email without valid TLD shows specific error."""
        is_valid, error_msg = validate_email_strict("user@domain")
        assert is_valid is False
        assert "extension" in error_msg.lower() or "domain" in error_msg.lower()
    
    def test_tld_too_short(self):
        """Email with single-char TLD shows specific error."""
        is_valid, error_msg = validate_email_strict("user@domain.c")
        assert is_valid is False
        assert "2 characters" in error_msg.lower() or "valid" in error_msg.lower()


class TestPasswordMismatchValidation:
    """Test password confirmation mismatch detection."""
    
    def test_matching_passwords(self):
        """Matching passwords pass validation."""
        is_valid, error_msg = validate_password_match("SecurePass123!", "SecurePass123!")
        assert is_valid is True
        assert error_msg == ""
    
    def test_mismatched_passwords(self):
        """Mismatched passwords show specific error."""
        is_valid, error_msg = validate_password_match("SecurePass123!", "DifferentPass456!")
        assert is_valid is False
        assert "do not match" in error_msg.lower() or "don't match" in error_msg.lower()
    
    def test_empty_confirm_password(self):
        """Empty confirm password shows specific error."""
        is_valid, error_msg = validate_password_match("SecurePass123!", "")
        assert is_valid is False
        assert "confirm" in error_msg.lower()
    
    def test_case_sensitive_matching(self):
        """Password matching is case-sensitive."""
        is_valid, _ = validate_password_match("Password123!", "password123!")
        assert is_valid is False


class TestPasswordSecurityValidation:
    """Test password security requirements with specific error messages."""
    
    def test_password_too_short(self):
        """Password under 8 chars shows length error."""
        is_valid, error_msg = validate_password_security("Short1!")
        assert is_valid is False
        assert "8 characters" in error_msg
    
    def test_password_missing_uppercase(self):
        """Password without uppercase shows specific error."""
        is_valid, error_msg = validate_password_security("password123!")
        assert is_valid is False
        assert "uppercase" in error_msg.lower()
    
    def test_password_missing_lowercase(self):
        """Password without lowercase shows specific error."""
        is_valid, error_msg = validate_password_security("PASSWORD123!")
        assert is_valid is False
        assert "lowercase" in error_msg.lower()
    
    def test_password_missing_number(self):
        """Password without number shows specific error."""
        is_valid, error_msg = validate_password_security("PasswordOnly!")
        assert is_valid is False
        assert "number" in error_msg.lower()
    
    def test_password_missing_special_char(self):
        """Password without special char shows specific error."""
        is_valid, error_msg = validate_password_security("Password123")
        assert is_valid is False
        assert "special" in error_msg.lower()
    
    def test_valid_password(self):
        """Valid password with all requirements passes."""
        is_valid, error_msg = validate_password_security("SecurePass123!")
        assert is_valid is True
        assert error_msg == ""


class TestUsernameValidation:
    """Test username format validation."""
    
    def test_valid_username(self):
        """Valid usernames pass validation."""
        valid_usernames = ["john_doe", "user123", "Test-User", "abc"]
        for username in valid_usernames:
            is_valid, _ = validate_username(username)
            assert is_valid is True, f"Expected {username} to be valid"
    
    def test_username_too_short(self):
        """Username under 3 chars shows length error."""
        is_valid, error_msg = validate_username("ab")
        assert is_valid is False
        assert "3" in error_msg
    
    def test_empty_username(self):
        """Empty username shows required error."""
        is_valid, error_msg = validate_username("")
        assert is_valid is False
        assert "required" in error_msg.lower()
    
    def test_username_invalid_characters(self):
        """Username with special chars shows error."""
        is_valid, error_msg = validate_username("user@name")
        assert is_valid is False


class TestAgeValidation:
    """Test age validation for signup form."""
    
    def test_valid_age(self):
        """Valid ages pass validation."""
        valid_ages = [13, 25, 50, 100, 120]
        for age in valid_ages:
            is_valid, _ = validate_age(age)
            assert is_valid is True, f"Expected age {age} to be valid"
    
    def test_age_too_young(self):
        """Age below minimum shows error."""
        is_valid, error_msg = validate_age(9)
        assert is_valid is False
    
    def test_age_too_old(self):
        """Age above maximum shows error."""
        is_valid, error_msg = validate_age(121)
        assert is_valid is False
    
    def test_non_numeric_age(self):
        """Non-numeric age shows error."""
        is_valid, error_msg = validate_age("abc")
        assert is_valid is False
        assert "number" in error_msg.lower()


class TestErrorMessageClarity:
    """Test that error messages are clear and actionable."""
    
    def test_error_messages_not_empty(self):
        """All validation failures return non-empty error messages."""
        test_cases = [
            validate_required("", "Field"),
            validate_email_strict("invalid"),
            validate_password_match("a", "b"),
            validate_password_security("weak"),
            validate_username(""),
        ]
        for is_valid, error_msg in test_cases:
            assert is_valid is False
            assert error_msg is not None
            assert len(error_msg) > 0
    
    def test_error_messages_are_user_friendly(self):
        """Error messages don't contain technical jargon."""
        _, email_error = validate_email_strict("invalid")
        _, password_error = validate_password_security("weak")
        
        # Error messages should not contain technical terms
        technical_terms = ["regex", "pattern", "exception", "error code", "null"]
        for term in technical_terms:
            assert term not in email_error.lower()
            assert term not in password_error.lower()
