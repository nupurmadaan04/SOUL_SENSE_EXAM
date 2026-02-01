""" 
Security constants for the Soul Sense API.
Centralizing these ensures consistency across services and simplifies security audits.
"""

# Password Hashing
# 12 is recommended as a balance between security and performance in 2024+
BCRYPT_ROUNDS = 12

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Longer-lived refresh tokens
