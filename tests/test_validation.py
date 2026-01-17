import pytest
from datetime import datetime, timedelta
from app.validation import (
    sanitize_text, validate_required, validate_length,
    validate_email, validate_phone, validate_age,
    validate_range, validate_dob,
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
    assert validate_email("")[0] is True  # Optional


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
