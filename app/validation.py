import re
from typing import Tuple, Union, Optional
from datetime import datetime
from app.constants import (
    MAX_TEXT_LENGTH, MAX_ENTRY_LENGTH, MAX_USERNAME_LENGTH,
    MAX_AGE_LENGTH, AGE_MIN, AGE_MAX
)

# Constants
EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
PHONE_REGEX = r"^\+?[\d\s-]{10,}$"

# Standard Ranges
RANGES = {
    'stress': (1, 10),
    'sleep': (0.0, 24.0),
    'energy': (1, 10),
    'quality': (1, 10),
    'work': (0.0, 24.0),
    'screen': (0, 1440)  # Minutes in a day
}


def sanitize_text(text: Optional[str]) -> str:
    """Strip whitespace and handle None."""
    if text is None:
        return ""
    return str(text).strip()


def validate_required(text: str, label: str) -> Tuple[bool, str]:
    """Check if text is not empty."""
    if not text:
        return False, f"{label} is required."
    return True, ""


def validate_length(text: str, max_len: int, label: str, min_len: int = 0) -> Tuple[bool, str]:
    """Check string length constraints."""
    if len(text) > max_len:
        return False, f"{label} cannot exceed {max_len} characters."
    if len(text) < min_len:
        return False, f"{label} must be at least {min_len} characters."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    if not email:
        return True, ""  # Empty is valid (optional), use validate_required if mandatory
    if not re.match(EMAIL_REGEX, email):
        return False, "Invalid email format."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate phone format."""
    if not phone:
        return True, ""
    if not re.match(PHONE_REGEX, phone):
        return False, "Invalid phone number format (min 10 digits)."
    return True, ""


def validate_age(age: Union[str, int]) -> Tuple[bool, str]:
    """Validate age is a number within valid range."""
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        return False, "Age must be a valid number."

    if age_int < AGE_MIN or age_int > AGE_MAX:
        return False, f"Age must be between {AGE_MIN} and {AGE_MAX}."
    return True, ""


def validate_range(value: Union[int, float], min_val: float, max_val: float, label: str) -> Tuple[bool, str]:
    """Validate numeric value is within range."""
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return False, f"{label} must be a valid number."

    if val_float < min_val or val_float > max_val:
        return False, f"{label} must be between {min_val} and {max_val}."
    return True, ""


def validate_dob(date_str: str) -> Tuple[bool, str]:
    """Ensure date is valid, in the past, and age is within limits."""
    if not date_str:
        return True, ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        
        if dt > now:
            return False, "Date cannot be in the future."
            
        # Optional: Check minimum age (e.g. 10) and max age (e.g. 120)
        # Calculate age
        age = now.year - dt.year - ((now.month, now.day) < (dt.month, dt.day))
        
        if age < AGE_MIN:
            return False, f"You must be at least {AGE_MIN} years old."
        if age > AGE_MAX:
             return False, f"Age cannot exceed {AGE_MAX} years."
             
    except ValueError:
        return False, "Invalid date format (expected YYYY-MM-DD)."
    return True, ""
