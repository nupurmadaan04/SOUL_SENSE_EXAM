import secrets
from datetime import timedelta
from typing import Annotated
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import get_settings
from ..schemas import UserCreate, Token, UserResponse, ErrorResponse, PasswordResetRequest, PasswordResetComplete, TwoFactorLoginRequest, TwoFactorAuthRequiredResponse, TwoFactorConfirmRequest, UsernameAvailabilityResponse, CaptchaResponse, LoginRequest
from ..services.db_service import get_db
from ..services.auth_service import AuthService
from ..services.captcha_service import captcha_service
from ..constants.errors import ErrorCode
from ..constants.security_constants import REFRESH_TOKEN_EXPIRE_DAYS
from ..exceptions import AuthException, APIException, RateLimitException
from ..root_models import User

router = APIRouter()
settings = get_settings()

@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """Generate a new CAPTCHA."""
    session_id = secrets.token_urlsafe(16)
    code = captcha_service.generate_captcha(session_id)
    return CaptchaResponse(captcha_code=code, session_id=session_id)

@router.get("/server-id")
async def get_server_id(request: Request):
    """Return the current server instance ID. Changes on every server restart."""
    return {"server_id": getattr(request.app.state, "server_instance_id", None)}

async def get_auth_service(db: Annotated[AsyncSession, Depends(get_db)]):
    """Dependency to get AuthService with database session."""
    return AuthService(db)

# oauth2_scheme is still needed for other endpoints but login now uses custom JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Get current user from JWT token.
    This remains in the router/dependency layer as it couples HTTP security with logic.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Pydantic schema validation for TokenData could be used here
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not getattr(user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Check if user is deleted
    if getattr(user, 'is_deleted', False) or getattr(user, 'deleted_at', None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deleted"
        )
    
    return user


# Rate limiter cache for username checks (20 per minute per IP)
availability_limiter_cache = TTLCache(maxsize=1000, ttl=60)

@router.get("/check-username", response_model=UsernameAvailabilityResponse)
async def check_username_availability(
    username: str,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Check if a username is available.
    Rate limited to 20 requests per minute per IP.
    """
    client_ip = request.client.host
    count = availability_limiter_cache.get(client_ip, 0)
    if count >= 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many availability checks. Please wait a minute."
        )
    availability_limiter_cache[client_ip] = count + 1
    
    available, message = await auth_service.check_username_available(username)
    return UsernameAvailabilityResponse(available=available, message=message)


@router.post("/register", response_model=None, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def register(
    request: Request,
    user: UserCreate, 
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    from ..middleware.rate_limiter import registration_limiter
    # Rate limit by IP
    is_limited, wait_time = registration_limiter.is_rate_limited(request.client.host)
    if is_limited:
        raise RateLimitException(
            message=f"Too many registration attempts. Please try again in {wait_time}s.",
            wait_seconds=wait_time
        )

    success, new_user, message = await auth_service.register_user(user)
    
    if not success:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
         
    # Always return a generic success message to prevent enumeration
    return {"message": message}


@router.post("/login", response_model=None, responses={401: {"model": ErrorResponse}, 202: {"model": TwoFactorAuthRequiredResponse}, 200: {"model": Token}})
async def login(
    response: Response,
    login_request: LoginRequest, 
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    from ..middleware.rate_limiter import login_limiter
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    # 1. Start with CAPTCHA Validation (Before Rate Limiting to prevent spam cheapness)
    if not captcha_service.validate_captcha(login_request.session_id, login_request.captcha_input):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH003", "message": "Invalid CAPTCHA"}
        )

    # 2. Rate Limit by IP
    is_limited, wait_time = login_limiter.is_rate_limited(ip)
    if is_limited:
         raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {wait_time}s."
        )

    # 3. Rate Limit by Username (Identifier)
    is_limited, wait_time = login_limiter.is_rate_limited(f"login_{login_request.identifier}")
    if is_limited:
         raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily restricted due to multiple login attempts. Please try again in {wait_time}s."
        )

    user = await auth_service.authenticate_user(login_request.identifier, login_request.password, ip_address=ip, user_agent=user_agent)
    
    # PR 4: 2FA Check
    if user.is_2fa_enabled:
        pre_auth_token = await auth_service.initiate_2fa_login(user)
        response.status_code = status.HTTP_202_ACCEPTED
        return TwoFactorAuthRequiredResponse(
            pre_auth_token=pre_auth_token
        )

    # Standard Login
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    
    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production, 
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)
    return {
    "access_token": access_token,
    "token_type": "bearer",
    "refresh_token": refresh_token,
    "username": user.username,
    "email": user.personal_profile.email if user.personal_profile else None,
    "id": user.id,
    "created_at": user.created_at,
    "warnings": (
        [{
            "code": "MULTIPLE_SESSIONS_ACTIVE",
            "message": "Your account is active on another device or browser."
        }] if has_multiple_sessions else []
    )
}



@router.post("/login/2fa", response_model=Token, responses={401: {"model": ErrorResponse}})
async def verify_2fa(
    login_request: TwoFactorLoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Verify 2FA code and issue tokens.
    """
    user = await auth_service.verify_2fa_login(login_request.pre_auth_token, login_request.code)
    
    # Issue Tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)
    return {
    "access_token": access_token,
    "token_type": "bearer",
    "refresh_token": refresh_token,
    "username": user.username,
    "email": user.personal_profile.email if user.personal_profile else None,
    "id": user.id,
    "created_at": user.created_at.isoformat() if user.created_at else None,
    "warnings": (
        [{
            "code": "MULTIPLE_SESSIONS_ACTIVE",
            "message": "Your account is active on another device or browser."
        }] if has_multiple_sessions else []
    )
}



@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthException(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Refresh token missing"
        )
        
    access_token, new_refresh_token = await auth_service.refresh_access_token(refresh_token)
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return Token(access_token=access_token, token_type="bearer", refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.revoke_refresh_token(refresh_token)
        
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse(id=current_user.id, username=current_user.username, created_at=current_user.created_at)


@router.post("/password-reset/initiate")
async def initiate_password_reset(
    request: Request,
    reset_data: PasswordResetRequest, # Renamed to avoid name conflict with Request
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    from ..middleware.rate_limiter import password_reset_limiter
    """
    Initiate the password reset flow.
    ALWAYS returns success message to prevent user enumeration.
    """
    # Rate limit by IP
    is_limited, wait_time = password_reset_limiter.is_rate_limited(request.client.host)
    if is_limited:
        raise RateLimitException(
            message=f"Too many reset requests. Please try again in {wait_time}s.",
            wait_seconds=wait_time
        )

    # Rate limit by Email
    is_limited, wait_time = password_reset_limiter.is_rate_limited(f"reset_{reset_data.email}")
    if is_limited:
        raise RateLimitException(
            message=f"Multiple requests for this email. Please try again in {wait_time}s.",
            wait_seconds=wait_time
        )

    success, message = await auth_service.initiate_password_reset(reset_data.email)
    if not success:
        # Rate limit or server error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return {"message": message}


@router.post("/password-reset/complete")
async def complete_password_reset(
    request: PasswordResetComplete,
    req_obj: Request, # Need Request object for IP
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    from ..middleware.rate_limiter import password_reset_limiter
    """
    Verify OTP and set new password.
    """
    # Rate limit by IP for OTP attempts
    is_limited, wait_time = password_reset_limiter.is_rate_limited(req_obj.client.host)
    if is_limited:
         raise RateLimitException(
            message=f"Too many attempts. Please try again in {wait_time}s.",
            wait_seconds=wait_time
        )

    success, message = await auth_service.complete_password_reset(
        request.email, 
        request.otp_code, 
        request.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return {"message": message}


@router.post("/2fa/setup/initiate")
async def initiate_2fa_setup(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Send OTP to verify email before enabling 2FA."""
    if await auth_service.send_2fa_setup_otp(current_user):
        return {"message": "OTP sent to your email"}
    raise HTTPException(status_code=400, detail="Could not send OTP. Check email configuration.")


@router.post("/2fa/enable")
async def enable_2fa(
    request: TwoFactorConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Enable 2FA after verifying OTP."""
    if await auth_service.enable_2fa(current_user.id, request.code):
        return {"message": "2FA enabled successfully"}
    raise HTTPException(status_code=400, detail="Invalid code")


@router.post("/2fa/disable")
async def disable_2fa(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Disable 2FA."""
    if await auth_service.disable_2fa(current_user.id):
        return {"message": "2FA disabled"}
    raise HTTPException(status_code=400, detail="Action failed")
