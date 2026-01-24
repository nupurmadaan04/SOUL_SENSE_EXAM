# Security Configuration
import os

# Password Security
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
PASSWORD_HASH_ROUNDS = 12

# Session Security
SESSION_TIMEOUT_HOURS = 24
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 5

# Database Security
DB_CONNECTION_TIMEOUT = 20
DB_POOL_SIZE = 5

# Input Validation
MAX_INPUT_LENGTH = 1000
ALLOWED_FILE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
MAX_FILE_SIZE_MB = 5

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = 60

# Security Headers (for future web interface)
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}