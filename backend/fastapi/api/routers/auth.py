import logging
from datetime import timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, status, Request, Response, BackgroundTasks, Form, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..config import get_settings_instance, get_settings
from ..schemas import UserCreate, Token, UserResponse, ErrorResponse, PasswordResetRequest, PasswordResetComplete, TwoFactorLoginRequest, TwoFactorAuthRequiredResponse, TwoFactorConfirmRequest, UsernameAvailabilityResponse, CaptchaResponse, LoginRequest, OAuthAuthorizeRequest, OAuthTokenRequest, OAuthTokenResponse, OAuthUserInfo, StepUpAuthRequest, StepUpAuthResponse, StepUpAuthVerifyRequest, StepUpAuthVerifyResponse
from ..services.db_router import get_db
from ..services.auth_service import AuthService

async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)

from ..services.captcha_service import captcha_service
from ..utils.network import get_real_ip
from ..utils.timestamps import normalize_utc_iso
from ..constants.security_constants import REFRESH_TOKEN_EXPIRE_DAYS
from ..models import User
from ..utils.limiter import limiter
from ..utils.device_fingerprinting import DeviceFingerprinting
from app.core import (
    AuthenticationError,
    AuthorizationError,
    InvalidCredentialsError,
    TokenExpiredError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ResourceAlreadyExistsError,
    BusinessLogicError
)
from ..utils.race_condition_protection import check_idempotency, complete_idempotency
import secrets

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings_instance()

@router.get("/captcha", response_model=CaptchaResponse)
@limiter.limit("100/minute")
async def get_captcha(request: Request):
    """Generate a new CAPTCHA."""

    session_id = secrets.token_urlsafe(16)
    code = captcha_service.generate_captcha(session_id)
    return CaptchaResponse(captcha_code=code, session_id=session_id)

@router.get("/server-id")
async def get_server_id(request: Request):
    """Return the current server instance ID."""
    return {"server_id": getattr(request.app.state, "server_instance_id", None)}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(request: Request, token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db)):
    """
    Get current user from JWT token (Async).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    """Get current user from JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
        
        # Check if token is revoked
        from ..root_models import TokenRevocation
        from sqlalchemy import select
        stmt = select(TokenRevocation).filter(TokenRevocation.token_str == token)
        result = await db.execute(stmt)
        revoked = result.scalar_one_or_none()
        if revoked:
            raise credentials_exception
        from ..models import TokenRevocation
        rev_stmt = select(TokenRevocation).filter(TokenRevocation.token_str == token)
        rev_res = await db.execute(rev_stmt)
        if rev_res.scalar_one_or_none():
            raise TokenExpiredError("Token has been revoked")

        username: str = payload.get("sub")
        user_id_from_token = payload.get("uid") # New field for GenVersion (#1143)
        if not username:
            raise InvalidCredentialsError()
    except JWTError:
        raise credentials_exception

    stmt = select(User).filter(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise InvalidCredentialsError()

    from ..services.cache_service import cache_service
    cache_key = f"user_rbac:{username}"
    # Use version-based check to catch stale nodes that missed invalidation (#1143)
    user_data = None
    if user_id_from_token:
        user_data = await cache_service.get_with_version_check(cache_key, "user", user_id_from_token)
    else:
        # Fallback for legacy tokens without uid: check normally but don't assume versioning is safe
        user_data = await cache_service.get(cache_key)

    if user_data:
        class CachedUser:
            def __init__(self, **entries):
                self.__dict__.update(entries)
        user = CachedUser(**user_data)
    else:
        user_stmt = select(User).filter(User.username == username).options(selectinload(User.personal_profile))
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        
        if user is None:
            raise InvalidCredentialsError()
            
        user_data = {
            "id": user.id,
            "username": user.username,
            "created_at": normalize_utc_iso(user.created_at, fallback_now=True),
            "last_login": user.last_login,
            "is_active": user.is_active,
            "is_deleted": user.is_deleted,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "is_admin": getattr(user, 'is_admin', False),
            "onboarding_completed": getattr(user, 'onboarding_completed', False),
            "version": getattr(user, 'version', 1) # Include version for generation check
        }
        await cache_service.set(cache_key, user_data, 3600)
        # Ensure authoritative version is also in Redis mapping
        await cache_service.update_version("user", user.id, user_data["version"])
    
    request.state.user_id = user.id
    
    # Check if user is active
    if not getattr(user, 'is_active', True):
        raise BusinessLogicError(message="User account is inactive", code="INACTIVE_ACCOUNT")
    
    if getattr(user, 'is_deleted', False) or getattr(user, 'deleted_at', None) is not None:
        raise AuthorizationError(message="User account is deleted")
    
    # Fetch and set DEK context for Envelope AEAD Encryption (#1105)
    try:
        from ..services.encryption_service import EncryptionService, current_dek, current_user_id
        dek = await EncryptionService.get_or_create_user_dek(user.id, db)
        current_dek.set(dek)
        current_user_id.set(user.id)
    except Exception as e:
        logger.error(f"Failed to load user DEK context: {e}")
        
    return user

async def require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency to check if the current user has administrative privileges.
    
    Args:
        current_user (User): The user object returned by get_current_user.
        
    Returns:
        User: The authenticated administrator.
        
    Raises:
        HTTPException: If the user is not an administrator.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return current_user

async def get_auth_service(db: AsyncSession = Depends(get_db)):
    return AuthService(db)

@router.get("/check-username", response_model=UsernameAvailabilityResponse)
@limiter.limit("20/minute")
async def check_username_availability(
    username: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Check if a username is available.
    Rate limited to 20 requests per minute per IP.
    """
    client_ip = get_real_ip(request)
    count = availability_limiter_cache.get(client_ip, 0)
    if count >= 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many availability checks. Please wait a minute."
        )
    availability_limiter_cache[client_ip] = count + 1
    
    """Check if a username is available."""
    available, message = await auth_service.check_username_available(username)
    return UsernameAvailabilityResponse(available=available, message=message)

@router.post("/register", response_model=None, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
@limiter.limit("5/minute")
async def register(
    request: Request,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user. Rate limited to 5 requests per minute per IP/user."""
    success, new_user, message = await auth_service.register_user(user)

    if not success:
        raise BusinessLogicError(message=message, code="REGISTRATION_FAILED")
    return {"message": message}


@router.post("/login", response_model=Token, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 202: {"model": TwoFactorAuthRequiredResponse}})
@limiter.limit("5/minute")
async def login(
    response: Response,
    login_request: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    db = Depends(get_db)
):
    """Login endpoint. Rate limited to 5 requests per minute per IP/user."""
    ip = get_real_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")

    # 1. Start with CAPTCHA Validation
    if not captcha_service.validate_captcha(login_request.session_id, login_request.captcha_input):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The CAPTCHA validation failed. Please refresh the CAPTCHA and try again."
        )

    # 2. Rate Limit by IP
    is_limited, wait_time = login_limiter.is_rate_limited(ip)
    if is_limited:
         raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {wait_time}s."
        )

    # 3. Rate Limit by Username
    is_limited, wait_time = login_limiter.is_rate_limited(f"login_{login_request.identifier}")
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily restricted. Please try again in {wait_time}s."
        )
    if not captcha_service.validate_captcha(login_request.session_id, login_request.captcha_input):
        raise ValidationError(
            message="The CAPTCHA validation failed. Please refresh the CAPTCHA and try again.",
            details=[{"field": "captcha_input", "error": "Invalid CAPTCHA"}]
        )

    user = await auth_service.authenticate_user(login_request.identifier, login_request.password, ip_address=ip, user_agent=user_agent)

    if user.is_2fa_enabled:
        pre_auth_token = await auth_service.initiate_2fa_login(user)
        response.status_code = status.HTTP_202_ACCEPTED
        return TwoFactorAuthRequiredResponse(pre_auth_token=pre_auth_token)

    # Create device fingerprint from request and login data
    device_fingerprint = DeviceFingerprinting.extract_fingerprint_from_request(request)

    # Override fingerprint with login request data if provided
    if login_request.device_screen_resolution:
        device_fingerprint.screen_resolution = login_request.device_screen_resolution
    if login_request.device_timezone_offset is not None:
        device_fingerprint.timezone_offset = login_request.device_timezone_offset
    if login_request.device_platform:
        device_fingerprint.platform = login_request.device_platform
    if login_request.device_plugins_hash:
        device_fingerprint.plugins = login_request.device_plugins_hash
    if login_request.device_canvas_fingerprint:
        device_fingerprint.canvas_fingerprint = login_request.device_canvas_fingerprint
    if login_request.device_webgl_fingerprint:
        device_fingerprint.webgl_fingerprint = login_request.device_webgl_fingerprint

    # Recalculate fingerprint hash with updated data
    device_fingerprint.fingerprint_hash = DeviceFingerprinting.calculate_fingerprint_hash(device_fingerprint)

    # Create session with device fingerprint
    session_id = await auth_service.create_user_session(
        user.id,
        user.username,
        ip,
        user_agent,
        device_fingerprint,
        db_session=db
    )

    access_token = auth_service.create_access_token(data={
        "sub": user.username,
        "uid": user.id,
        "tid": str(user.tenant_id) if user.tenant_id else None,
        "jti": session_id  # Include session ID in JWT for fingerprint validation
    })
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        username=user.username,
        email=profile.email if profile else None,
        id=user.id,
        created_at=normalize_utc_iso(user.created_at, fallback_now=True),
        warnings=(
            [{
                "code": "MULTIPLE_SESSIONS_ACTIVE",
                "message": "Your account is active on another device or browser."
            }] if has_multiple_sessions else []
        ),
        onboarding_completed=getattr(user, "onboarding_completed", False),
        is_admin=getattr(user, "is_admin", False)
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout and revoke access token."""
    # 1. Revoke the token
    await auth_service.logout(token, auth_service.db)
    
    # 2. Clear cookies
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}

@router.post("/login/2fa", response_model=Token, responses={401: {"model": ErrorResponse}})
@limiter.limit("5/minute")
async def verify_2fa(
    login_request: TwoFactorLoginRequest,
    response: Response,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify 2FA code and issue tokens."""
    ip = get_real_ip(request)
    # Session Fixation Protection
    old_refresh_token = request.cookies.get("refresh_token")
    if old_refresh_token:
        await auth_service.revoke_refresh_token(old_refresh_token)
    
    # Verify 2FA and get user
    user = await auth_service.verify_2fa_login(login_request.pre_auth_token, login_request.code, ip_address=ip)
    
    # Issue Tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    user = await auth_service.verify_2fa_login(login_request.pre_auth_token, login_request.code, ip_address=ip)
    
    refresh_token = await auth_service.create_refresh_token(user.id)
    
    access_token = auth_service.create_access_token(data={"sub": user.username, "tid": str(user.tenant_id) if user.tenant_id else None})
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    from ..models import PersonalProfile
    stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
    res_p = await auth_service.db.execute(stmt)
    profile = res_p.scalar_one_or_none()

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        username=user.username,
        email=profile.email if profile else None,
        id=user.id,
        created_at=normalize_utc_iso(user.created_at, fallback_now=True),
        warnings=(
            [{
                "code": "MULTIPLE_SESSIONS_ACTIVE",
                "message": "Your account is active on another device or browser."
            }] if has_multiple_sessions else []
        ),
        onboarding_completed=getattr(user, "onboarding_completed", False),
        is_admin=getattr(user, "is_admin", False)
    )

@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token with race condition protection."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthenticationError(message="Refresh token missing", code="REFRESH_TOKEN_MISSING")

    # Check for idempotency to prevent concurrent refresh operations
    cached_response = await check_idempotency(request, "token_refresh", ttl_seconds=60)
    if cached_response:
        logger.info(f"Returning cached token refresh response")
        return cached_response

    try:
        access_token, new_refresh_token = await auth_service.refresh_access_token(refresh_token)

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=settings.is_production, 
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        
<<<<<<< HEAD
        token_response = Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token
        )
=======
        token_response = Token(access_token=access_token, token_type="bearer", refresh_token=new_refresh_token)
>>>>>>> 0fb38f167afcb6352c3e8ff1a5ca0488ff3495af

        # Cache the successful response for idempotency
        await complete_idempotency(request, token_response.model_dump_json())

        return token_response

    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """ Logout the current user."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.revoke_refresh_token(refresh_token)
    
    # 2. Revoke Access Token (from header)
    await auth_service.revoke_access_token(token)
    
    # 3. Audit Logout
    await auth_service.revoke_access_token(token)
    
    from .audit_service import AuditService
    await AuditService.log_event(
        current_user.id,
        "LOGOUT",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "Unknown"),
        db_session=auth_service.db
    )
        
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=normalize_utc_iso(current_user.created_at, fallback_now=True),
    )

@router.post("/password-reset/initiate")
async def initiate_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service)
):
    from ..middleware.rate_limiter import password_reset_limiter
    real_ip = get_real_ip(request)
    is_limited, wait_time = await password_reset_limiter.is_rate_limited(real_ip)
    if is_limited:
        raise RateLimitError(message=f"Too many reset requests. Please try again in {wait_time}s.", wait_seconds=wait_time)

    is_limited, wait_time = await password_reset_limiter.is_rate_limited(f"reset_{reset_data.email}")
    if is_limited:
        raise RateLimitError(message=f"Multiple requests for this email. Please try again in {wait_time}s.", wait_seconds=wait_time)

    success, message = await auth_service.initiate_password_reset(reset_data.email, background_tasks)
    if not success:
        raise BusinessLogicError(message=message, code="PASSWORD_RESET_FAILED")
    return {"message": message}

@router.post("/password-reset/complete")
@limiter.limit("3/minute")
async def complete_password_reset(
    request: PasswordResetComplete,
    req_obj: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    from ..middleware.rate_limiter import password_reset_limiter
    """
    Verify OTP and set new password.
    Rate limited to 3 requests per minute per IP/user.
    """
    # Rate limit by IP for OTP attempts
    real_ip = get_real_ip(req_obj)
    is_limited, wait_time = await password_reset_limiter.is_rate_limited(real_ip)
    if is_limited:
        raise RateLimitError(message=f"Too many attempts. Please try again in {wait_time}s.", wait_seconds=wait_time)

    success, message = await auth_service.complete_password_reset(
        request.email, 
        request.otp_code, 
        request.new_password
    )
    success, message = await auth_service.complete_password_reset(request.email, request.otp_code, request.new_password)
    if not success:
        raise ValidationError(message=message, details=[{"field": "otp_code", "error": "Invalid or expired OTP"}])
    return {"message": message}

@router.post("/2fa/setup/initiate")
@limiter.limit("5/minute")
async def initiate_2fa_setup(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Send OTP to verify email before enabling 2FA."""
    if await auth_service.send_2fa_setup_otp(current_user):
        return {"message": "OTP sent to your email"}
    raise BusinessLogicError(message="Could not send OTP. Check email configuration.", code="OTP_SEND_FAILED")

@router.post("/2fa/enable")
@limiter.limit("5/minute")
async def enable_2fa(
    request: Request,
    confirm_request: TwoFactorConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Enable 2FA after verifying OTP."""
    if await auth_service.enable_2fa(current_user.id, confirm_request.code):
        return {"message": "2FA enabled successfully"}
    raise ValidationError(message="Invalid verification code", details=[{"field": "code", "error": "Invalid or expired verification code"}])

@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def disable_2fa(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Disable 2FA."""
    if await auth_service.disable_2fa(current_user.id):
        return {"message": "2FA disabled"}
    raise BusinessLogicError(message="Failed to disable 2FA", code="2FA_DISABLE_FAILED")

@router.post("/oauth/login", response_model=Token, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
@limiter.limit("5/minute")
async def oauth_login(
    response: Response,
    request: Request,
    provider: str = Form(..., description="OAuth provider (google, github, apple)"),
    id_token: Optional[str] = Form(None, description="ID token from OAuth provider"),
    access_token: Optional[str] = Form(None, description="Access token from OAuth provider"),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login with OAuth token (e.g., from Auth0). Rate limited to 5 requests per minute per IP/user."""
    # Verify the token with the OAuth provider
    # For Auth0, verify the JWT
    # This is a placeholder - implement actual verification
    try:
        user_info = None
        
        if provider == "google":
            if not id_token:
                raise ValidationError(message="ID token required for Google login", details=[{"field": "id_token", "error": "Missing token"}])
            
            # Use httpx to verify token with Google's API to avoid extra dependencies
            import httpx
            async with httpx.AsyncClient() as client:
                res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
                if res.status_code != 200:
                    # In development, allow dummy login if token is "mock_google_token"
                    if settings.ENVIRONMENT == "development" and id_token == "mock_google_token":
                        user_info = {"sub": "google_mock_123", "email": "mock_google@example.com", "name": "Mock Google User"}
                    else:
                        raise InvalidCredentialsError(message="Invalid Google ID token")
                else:
                    id_info = res.json()
                    # Verify audience matches our client ID (if configured)
                    if settings.google_client_id and id_info.get("aud") != settings.google_client_id:
                        raise AuthorizationError(message="Token audience mismatch")
                    
                    user_info = {
                        "sub": id_info["sub"],
                        "email": id_info.get("email"),
                        "name": id_info.get("name"),
                        "picture": id_info.get("picture")
                    }

        elif provider == "github":
            if not access_token:
                raise ValidationError(message="Access token required for Github login", details=[{"field": "access_token", "error": "Missing token"}])
            
            import httpx
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {access_token}"}
                )
                if res.status_code != 200:
                    if settings.ENVIRONMENT == "development" and access_token == "mock_github_token":
                        user_info = {"sub": "github_mock_123", "email": "mock_github@example.com", "name": "Mock Github User"}
                    else:
                        raise InvalidCredentialsError(message="Invalid Github access token")
                else:
                    gh_info = res.json()
                    user_info = {
                        "sub": str(gh_info["id"]),
                        "email": gh_info.get("email"),
                        "name": gh_info.get("name") or gh_info.get("login"),
                        "picture": gh_info.get("avatar_url")
                    }
        
        elif provider == "apple":
             # Placeholder for Apple login
             if settings.ENVIRONMENT == "development" and id_token == "mock_apple_token":
                 user_info = {"sub": "apple_mock_123", "email": "mock_apple@example.com", "name": "Mock Apple User"}
             else:
                 raise BusinessLogicError(message="Apple login not fully implemented yet", code="NOT_IMPLEMENTED")
        
        else:
            raise ValidationError(message=f"Unsupported provider: {provider}", details=[{"field": "provider", "error": "Invalid provider"}])

        if not user_info:
            raise InvalidCredentialsError(message="Failed to retrieve user information from provider")

        # Get or create local user
        user = await auth_service.get_or_create_oauth_user(user_info)
        
        # Issue tokens
        new_access_token = auth_service.create_access_token(data={
            "sub": user.username, 
            "uid": user.id
        })
        refresh_token = await auth_service.create_refresh_token(user.id)
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.is_production, 
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        
        # Audit Log
        from .audit_service import AuditService
        await AuditService.log_auth_event(
            'login_oauth',
            user.username,
            details={"provider": provider, "status": "success"},
            ip_address=ip,
            user_agent=user_agent,
            db_session=auth_service.db
        )
        
        return Token(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            username=user.username,
            email=getattr(user.personal_profile, 'email', None) if user.personal_profile else user_info.get("email"),
            id=user.id,
            created_at=normalize_utc_iso(user.created_at, fallback_now=True),
            warnings=[],
            onboarding_completed=getattr(user, "onboarding_completed", False),
            is_admin=getattr(user, "is_admin", False)
        )

    except Exception as e:
        if isinstance(e, (ValidationError, InvalidCredentialsError, AuthorizationError, BusinessLogicError)):
            raise e
        logger.error(f"OAuth login failed: {str(e)}")
        raise BusinessLogicError(message=f"Social login failed: {str(e)}", code="OAUTH_ERROR")


# ============================================================================
# Step-Up Authentication Endpoints (#1245)
# ============================================================================

@router.post("/step-up/initiate", response_model=StepUpAuthResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
async def initiate_step_up_auth(
    request: StepUpAuthRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    req: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Initiate step-up authentication for privileged actions.
    
    Requires the user to have 2FA enabled. Returns a time-bound token
    that must be verified with an OTP code before performing sensitive operations.
    """
    try:
        # Extract session ID from JWT token
        auth_header = req.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
            
        token = auth_header[7:]  # Remove "Bearer " prefix
        session_id = None
        
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            session_id = payload.get("session_id")
        except JWTError:
            # Fallback: try to get from current session
            session_id = getattr(req.state, "session_id", None)
            
        if not session_id:
            raise HTTPException(status_code=401, detail="Session ID required for step-up auth")
            
        ip = get_real_ip(req)
        user_agent = req.headers.get("user-agent", "Unknown")
        
        step_up_token = await auth_service.initiate_step_up_auth(
            user=current_user,
            session_id=session_id,
            purpose=request.purpose,
            ip_address=ip,
            user_agent=user_agent
        )
        
        return StepUpAuthResponse(
            step_up_token=step_up_token,
            expires_in_seconds=600,  # 10 minutes
            purpose=request.purpose
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Step-up auth initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Step-up authentication initiation failed")


@router.post("/step-up/verify", response_model=StepUpAuthVerifyResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
async def verify_step_up_auth(
    request: StepUpAuthVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    req: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Verify step-up authentication with OTP code.
    
    Validates the step-up token and OTP code. On success, marks the token as used
    and allows privileged operations for a limited time window.
    """
    try:
        ip = get_real_ip(req)
        
        success = await auth_service.verify_step_up_auth(
            step_up_token=request.step_up_token,
            otp_code=request.code,
            ip_address=ip
        )
        
        if success:
            # Get token details for response
            from ..models import StepUpToken
            from sqlalchemy import select
            
            stmt = select(StepUpToken).filter(StepUpToken.token == request.step_up_token)
            result = await auth_service.db.execute(stmt)
            token_record = result.scalar_one_or_none()
            
            return StepUpAuthVerifyResponse(
                verified=True,
                expires_at=token_record.expires_at.isoformat() if token_record else None
            )
        else:
            raise HTTPException(status_code=401, detail="Step-up authentication failed")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Step-up auth verification failed: {e}")
        raise HTTPException(status_code=500, detail="Step-up authentication verification failed")


# --- Secrets Compliance Monitoring (#1246) ---

@router.get("/compliance/secrets", response_model=Dict[str, Any], tags=["Security Compliance"])
async def get_secrets_compliance_metrics(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current secrets age and rotation compliance metrics.

    Returns compliance statistics and violation details for dashboard monitoring.
    Requires admin privileges.

    - **total_active_tokens**: Total number of active refresh tokens
    - **compliant_tokens**: Tokens within rotation policy
    - **warning_violations**: Tokens needing attention (30+ days)
    - **critical_violations**: Tokens requiring immediate action (60+ days)
    - **expired_tokens**: Tokens exceeding maximum age (90+ days)
    - **compliance_rate**: Percentage of compliant tokens
    - **violations**: Detailed list of violating tokens
    """
    # Check admin privileges (simplified check - in production use proper RBAC)
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from ..services.secrets_compliance_service import secrets_compliance_service

    try:
        # Get current metrics from cache
        metrics = await secrets_compliance_service.get_compliance_metrics()

        if not metrics:
            # If no cached metrics, run fresh check
            metrics = await secrets_compliance_service.check_compliance(db)
            await secrets_compliance_service.update_metrics(metrics)

        return metrics

    except Exception as e:
        logger.error(f"Failed to retrieve compliance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance metrics")


@router.post("/compliance/secrets/check", response_model=Dict[str, Any], tags=["Security Compliance"])
async def run_secrets_compliance_check(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger secrets compliance check.

    Runs full compliance analysis and returns current status.
    Requires admin privileges.
    """
    # Check admin privileges
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from ..services.secrets_compliance_service import secrets_compliance_service

    try:
        # Run fresh compliance check
        report = await secrets_compliance_service.check_compliance(db)

        # Update metrics cache
        await secrets_compliance_service.update_metrics(report)

        # Trigger Celery task for alerting if violations found
        if report.get('violations'):
            from ..celery_tasks import check_secrets_age_compliance
            # Run asynchronously (don't wait for completion)
            check_secrets_age_compliance.delay()

        return report

    except Exception as e:
        logger.error(f"Failed to run compliance check: {e}")
        raise HTTPException(status_code=500, detail="Failed to run compliance check")


@router.get("/compliance/secrets/thresholds", response_model=Dict[str, int], tags=["Security Compliance"])
async def get_secrets_rotation_thresholds(
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """
    Get current secrets rotation threshold configuration.

    Returns age thresholds in days for compliance monitoring.
    """
    # Check admin privileges
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from ..services.secrets_compliance_service import secrets_compliance_service

    return secrets_compliance_service.get_rotation_thresholds()


@router.get("/compliance/secrets/violations", response_model=List[Dict[str, Any]], tags=["Security Compliance"])
async def get_secrets_violations(
    severity: str = Query("warning", description="Minimum severity level: warning, critical, expired"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of tokens violating rotation policies.

    Returns detailed information about tokens needing rotation.
    Requires admin privileges.
    """
    # Check admin privileges
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from ..services.secrets_compliance_service import secrets_compliance_service

    try:
        return await secrets_compliance_service.get_tokens_needing_rotation(db, severity)

    except Exception as e:
        logger.error(f"Failed to retrieve violations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve violations")
