from fastapi import Request
from ..config import get_settings_instance

def get_real_ip(request: Request) -> str:
    """
    Extract the real client IP address from the request headers.
    Accounts for reverse proxies by checking the X-Forwarded-For header,
    but only if the request comes from a trusted proxy.
    """
    settings = get_settings_instance()
    client_ip = request.client.host if request.client else "Unknown"
    
    # Only trust X-Forwarded-For if the direct requester is a trusted proxy
    if client_ip in settings.TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain a list of IPs: "client, proxy1, proxy2"
            # The first one is the original client IP.
            return forwarded.split(",")[0].strip()
    
    # Fallback to direct client host
    return client_ip
