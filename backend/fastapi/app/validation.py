import re
import html
from typing import Tuple, Union, Optional
from datetime import datetime
from app.constants import (
    MAX_TEXT_LENGTH, MAX_ENTRY_LENGTH, MAX_USERNAME_LENGTH,
    MAX_AGE_LENGTH, AGE_MIN, AGE_MAX
)
from app.security_config import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

# Security patterns
SQL_INJECTION_PATTERNS = [
    r"('|(\-\-)|(;)|(\||\|)|(\*|\*))",
    r"(union|select|insert|delete|update|drop|create|alter)",
    r"(script|javascript|vbscript|onload|onerror)"
]
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe[^>]*>.*?</iframe>"
]

# Constants
# Stricter email regex matching frontend validation (requires valid TLD)
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
EMAIL_REGEX_STRICT = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PHONE_REGEX = r"^\+?[\d\s-]{10,}$"
USERNAME_REGEX = r"^[a-zA-Z][a-zA-Z0-9_]{2,19}$"
RESERVED_USERNAMES = {'admin', 'root', 'support', 'soulsense', 'system', 'official'}

# Common weak passwords list (lowercase for case-insensitive matching)
WEAK_PASSWORDS = {
    # Top most common passwords
    'password', 'password1', 'password123', 'password1234', 'password12345',
    '12345678', '123456789', '1234567890', '12345678910',
    'qwerty123', 'qwertyuiop', 'qwerty1234',
    'abc12345', 'abcdefgh', 'abc123456', 'abcd1234',
    'letmein1', 'welcome1', 'welcome123', 'monkey123',
    'dragon123', 'master123', 'login123', 'princess1',
    'football1', 'baseball1', 'soccer123', 'hockey123',
    'shadow123', 'sunshine1', 'trustno1', 'iloveyou1',
    'batman123', 'superman1', 'michael1', 'jennifer1',
    'charlie1', 'thomas123', 'jordan123', 'hunter123',
    'ranger123', 'buster123', 'killer123', 'george123',
    'robert123', 'andrea123', 'andrew123', 'joshua123',
    'matthew1', 'daniel123', 'hannah123', 'jessica1',
    'asdfghjk', 'asdf1234', 'zxcvbnm1', '1q2w3e4r',
    'qazwsx123', '1qaz2wsx', 'pass1234', 'test1234',
    'admin123', 'root1234', 'user1234', 'guest1234',
    'changeme1', 'default1', 'temp1234', 'nothing1',
    'whatever1', 'blahblah1', 'fuckyou1',
    'p@ssword1', 'p@ssw0rd', 'pa$$word1', 'passw0rd1',
    'summer123', 'winter123', 'spring123', 'autumn123',
    'january1', 'monday123', 'friday123',
    'computer1', 'internet1', 'samsung1', 'google123',
    'youtube1', 'facebook1', 'twitter1',
    'soulsense', 'soulsense1', 'soulsense123',
    'iloveyou', 'trustno1', 'access14',
    '!@#$%^&*', 'Aa123456', 'Aa12345678',
}


def is_weak_password(password: str) -> bool:
    """Check if a password is in the common weak passwords list."""
    return password.lower() in WEAK_PASSWORDS

# Common email domains for typo detection (Issue #617)
COMMON_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com',
    'protonmail.com', 'aol.com', 'live.com', 'msn.com', 'mail.com',
    'ymail.com', 'googlemail.com', 'zoho.com', 'gmx.com', 'fastmail.com'
]


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def suggest_email_domain(email: str) -> Optional[str]:
    """
    Suggest a corrected email domain for common typos.
    
    Args:
        email: The email address to check
        
    Returns:
        Suggested corrected email if a typo is detected, None otherwise
    """
    if not email or '@' not in email:
        return None
    
    parts = email.split('@')
    if len(parts) != 2:
        return None
    
    local_part, domain = parts
    if not local_part or not domain:
        return None
    
    domain_lower = domain.lower()
    
    # If domain exactly matches a known domain, no suggestion needed
    if domain_lower in COMMON_EMAIL_DOMAINS:
        return None
    
    # Find the closest matching domain
    best_match = None
    min_distance = float('inf')
    
    for known_domain in COMMON_EMAIL_DOMAINS:
        distance = _levenshtein_distance(domain_lower, known_domain)
        # Only suggest if distance is 1 or 2 (small typo)
        if distance <= 2 and distance < min_distance:
            min_distance = distance
            best_match = known_domain
    
    if best_match:
        return f"{local_part}@{best_match}"
    
    return None

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
    """Strip whitespace, handle None, and sanitize for security."""
    if text is None:
        return ""
    
    text = str(text).strip()
    
    # Check for malicious patterns
    if detect_malicious_input(text):
        return ""  # Return empty string for malicious input
    
    # HTML escape to prevent XSS
    text = html.escape(text)
    
    return text


def detect_malicious_input(text: str) -> bool:
    """Detect potential SQL injection or XSS attempts."""
    text_lower = text.lower()
    
    # Check SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    # Check XSS patterns
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format and security."""
    if not username:
        return False, "Username is required."
    
    if len(username) < 3 or len(username) > MAX_USERNAME_LENGTH:
        return False, f"Username must be 3-{MAX_USERNAME_LENGTH} characters."
    
    if not re.match(USERNAME_REGEX, username):
        return False, "Username must start with a letter and contain 3-20 letters, numbers, or underscores."
    
    if username.strip().lower() in RESERVED_USERNAMES:
        return False, "This username is reserved."

    if detect_malicious_input(username):
        return False, "Invalid username format."
    
    return True, ""


def validate_password_security(password: str) -> Tuple[bool, str]:
    """Enhanced password security validation."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password too long (max {MAX_PASSWORD_LENGTH} characters)."
    
    # Check against weak/common passwords list
    if is_weak_password(password):
        return False, "This password is too common. Please choose a stronger password."
    
    # Check character requirements
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter."
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter."
    
    if not re.search(r'\d', password):
        return False, "Password must contain number."
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain special character."
    
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


def validate_email_strict(email: str) -> Tuple[bool, str]:
    """
    Strict email validation with detailed error messages.
    Matches frontend validation behavior for real-time feedback.
    """
    if not email:
        return False, "Email is required"
    
    # Check for @ symbol
    if '@' not in email:
        return False, "Email must contain '@' symbol"
    
    parts = email.split('@')
    if len(parts) != 2:
        return False, "Email must contain exactly one '@' symbol"
    
    local_part, domain = parts
    
    # Check local part
    if not local_part:
        return False, "Email must have a local part before '@'"
    
    # Check domain
    if not domain:
        return False, "Email must have a domain after '@'"
    
    # Check for valid TLD (domain must have a dot)
    if '.' not in domain:
        return False, "Domain must include a valid extension (e.g., .com)"
    
    # Split domain to check TLD
    domain_parts = domain.rsplit('.', 1)
    if len(domain_parts) < 2 or len(domain_parts[1]) < 2:
        return False, "Domain extension must be at least 2 characters"
    
    # Final regex check for valid characters
    if not re.match(EMAIL_REGEX_STRICT, email):
        return False, "Please enter a valid email address (e.g., name@example.com)"
    
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

def validate_required(text: str, label: str) -> Tuple[bool, str]:
    """Check if text is not empty and secure."""
    if not text:
        return False, f"{label} is required."
    
    if detect_malicious_input(text):
        return False, f"{label} contains invalid characters."
    
    return True, ""


def validate_password_match(password: str, confirm_password: str) -> Tuple[bool, str]:
    """Validate that password and confirm password match."""
    if not confirm_password:
        return False, "Please confirm your password."
    
    if password != confirm_password:
        return False, "Passwords do not match."
    
    return True, ""