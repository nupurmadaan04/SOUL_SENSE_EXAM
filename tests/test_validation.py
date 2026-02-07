import pytest
from datetime import datetime, timedelta
from app.validation import (
    sanitize_text, validate_required, validate_length,
    validate_email, validate_email_strict, validate_phone, validate_age,
    validate_range, validate_dob, suggest_email_domain,
    AGE_MIN, AGE_MAX
)


def test_sanitize_text():
    assert sanitize_text("  hello  ") == "hello"
    assert sanitize_text(None) == ""
    assert sanitize_text("") == ""
    assert sanitize_text(123) == "123"


def test_validate_required():
    assert validate_required("test", "Field")[0] is True
    assert validate_required("", "Field")[0] is False
    # Check error message
    assert validate_required("", "Name")[1] == "Name is required."


def test_validate_length():
    assert validate_length("abc", 5, "Field")[0] is True
    assert validate_length("abcdef", 5, "Field")[0] is False
    assert validate_length("ab", 5, "Field", min_len=3)[0] is False
    # Error checks
    assert "exceed" in validate_length("abcdef", 5, "Field")[1]
    assert "at least" in validate_length("ab", 5, "Field", min_len=3)[1]


def test_validate_email():
    assert validate_email("test@example.com")[0] is True
    assert validate_email("user.name+tag@example.co.uk")[0] is True
    assert validate_email("invalid-email")[0] is False
    assert validate_email("@example.com")[0] is False
    assert validate_email("abc@gmail")[0] is False  # Missing TLD
    assert validate_email("")[0] is True  # Optional


def test_validate_email_strict():
    # Valid emails
    assert validate_email_strict("test@example.com")[0] is True
    assert validate_email_strict("user.name+tag@example.co.uk")[0] is True
    assert validate_email_strict("user123@domain.org")[0] is True
    
    # Empty email
    is_valid, msg = validate_email_strict("")
    assert is_valid is False
    assert "required" in msg.lower()
    
    # Missing @ symbol
    is_valid, msg = validate_email_strict("invalidemail")
    assert is_valid is False
    assert "@" in msg
    
    # Missing domain
    is_valid, msg = validate_email_strict("user@")
    assert is_valid is False
    assert "domain" in msg.lower()
    
    # Missing TLD (no dot in domain)
    is_valid, msg = validate_email_strict("user@domain")
    assert is_valid is False
    assert "extension" in msg.lower()
    
    # TLD too short
    is_valid, msg = validate_email_strict("user@domain.c")
    assert is_valid is False
    assert "2 characters" in msg.lower()
    
    # Multiple @ symbols
    is_valid, msg = validate_email_strict("user@@domain.com")
    assert is_valid is False


def test_validate_phone():
    assert validate_phone("+1234567890")[0] is True
    assert validate_phone("1234567890")[0] is True
    assert validate_phone("123-456-7890")[0] is True
    assert validate_phone("123")[0] is False  # Too short
    assert validate_phone("")[0] is True  # Optional


def test_validate_age():
    assert validate_age(25)[0] is True
    assert validate_age("30")[0] is True
    assert validate_age(AGE_MIN)[0] is True
    assert validate_age(AGE_MAX)[0] is True
    assert validate_age(AGE_MIN - 1)[0] is False
    assert validate_age(AGE_MAX + 1)[0] is False
    assert validate_age("abc")[0] is False
    assert validate_age(None)[0] is False


def test_validate_range():
    assert validate_range(5, 1, 10, "Score")[0] is True
    assert validate_range(1, 1, 10, "Score")[0] is True
    assert validate_range(10, 1, 10, "Score")[0] is True
    assert validate_range(0, 1, 10, "Score")[0] is False
    assert validate_range(11, 1, 10, "Score")[0] is False
    assert validate_range("5.5", 1, 10, "Score")[0] is True


def test_validate_dob():
    today = datetime.now().strftime("%Y-%m-%d")
    year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    valid_age_date = (datetime.now() - timedelta(days=365*20)).strftime("%Y-%m-%d") # 20 years old
    too_young_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d") # 5 years old
    
    assert validate_dob(valid_age_date)[0] is True
    assert validate_dob(year_ago)[0] is False # Too young
    assert validate_dob(today)[0] is False # Too young/Future
    assert validate_dob("invalid")[0] is False
    assert validate_dob("")[0] is True


def test_suggest_email_domain():
    """Test email domain suggestion for common typos (Issue #617)."""
    
    # Gmail typos
    assert suggest_email_domain("user@gmial.com") == "user@gmail.com"
    assert suggest_email_domain("user@gmal.com") == "user@gmail.com"
    assert suggest_email_domain("user@gmali.com") == "user@gmail.com"
    assert suggest_email_domain("user@gnail.com") == "user@gmail.com"
    
    # Yahoo typos
    assert suggest_email_domain("user@yaho.com") == "user@yahoo.com"
    assert suggest_email_domain("user@yahooo.com") == "user@yahoo.com"
    assert suggest_email_domain("user@tahoo.com") == "user@yahoo.com"
    
    # Hotmail typos
    assert suggest_email_domain("user@hotmal.com") == "user@hotmail.com"
    assert suggest_email_domain("user@hotmai.com") == "user@hotmail.com"
    assert suggest_email_domain("user@hotmial.com") == "user@hotmail.com"
    
    # Outlook typos
    assert suggest_email_domain("user@outlok.com") == "user@outlook.com"
    assert suggest_email_domain("user@outloo.com") == "user@outlook.com"
    
    # Valid domains should return None (no suggestion needed)
    assert suggest_email_domain("user@gmail.com") is None
    assert suggest_email_domain("user@yahoo.com") is None
    assert suggest_email_domain("user@hotmail.com") is None
    assert suggest_email_domain("user@outlook.com") is None
    assert suggest_email_domain("user@icloud.com") is None
    
    # Unknown/custom domains should return None
    assert suggest_email_domain("user@company.com") is None
    assert suggest_email_domain("user@mydomain.org") is None
    
    # Edge cases
    assert suggest_email_domain("") is None
    assert suggest_email_domain("invalid") is None
    assert suggest_email_domain("user@") is None
    assert suggest_email_domain("@domain.com") is None
    assert suggest_email_domain("user@@gmail.com") is None

