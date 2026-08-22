import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, Dict, Any, List

from fastapi import APIRouter, Depends, status, Request, Response, BackgroundTasks, Form, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..config import get_settings_instance, get_settings
from ..schemas import (
    UserCreate, Token, UserResponse, ErrorResponse,
    PasswordResetRequest, PasswordResetComplete,
    TwoFactorLoginRequest, TwoFactorAuthRequiredResponse, TwoFactorConfirmRequest,
    UsernameAvailabilityResponse, CaptchaResponse, LoginRequest,
    StepUpAuthRequest, StepUpAuthResponse, StepUpAuthVerifyRequest, StepUpAuthVerifyResponse
)
from ..services.db_router import get_db
from ..services.auth_service import AuthService
from ..services.captcha_service import captcha_service
from ..utils.network import get_real_ip
from ..utils.timestamps import normalize_utc_iso
from ..constants.security_constants import REFRESH_TOKEN_EXPIRE_DAYS
from ..models import User, PersonalProfile, TokenRevocation
from ..utils.limiter import limiter
from ..utils.device_fingerprinting import DeviceFingerprinting
try:
    from app.core import (
        AuthenticationError,
        AuthorizationError,
        InvalidCredentialsError,
        TokenExpiredError,
        ValidationError,
        NotFoundError,
        RateLimitError,
        BusinessLogicError
    )
except ImportError:
    from app.core import (
        AuthenticationError,
        AuthorizationError,
        InvalidCredentialsError,
        TokenExpiredError,
        ValidationError,
        NotFoundError,
        RateLimitError,
        BusinessLogicError
    )
from ..utils.race_condition_protection import check_idempotency, complete_idempotency

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings_instance()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from JWT token (Async).
    """
    if not token:
        # Check authorization header manually if oauth2_scheme was skipped
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        secret = getattr(settings, "secret_key", getattr(settings, "SECRET_KEY", "default-secret-key-for-soul-sense-exam-auth"))
        algorithm = getattr(settings, "jwt_algorithm", getattr(settings, "algorithm", "HS256"))
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        
        # Check token revocation
        try:
            rev_stmt = select(TokenRevocation).filter(TokenRevocation.token_str == token)
            rev_res = await db.execute(rev_stmt)
            if rev_res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
        except Exception as e:
            logger.debug(f"Revocation check skipped: {e}")

        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user_stmt = select(User).filter(User.username == username).options(selectinload(User.personal_profile))
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not getattr(user, 'is_active', True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive")

    if getattr(user, 'is_deleted', False) or getattr(user, 'deleted_at', None) is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deleted")

    request.state.user_id = user.id
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check administrative privileges."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return current_user


# Availability limiter cache
availability_limiter_cache: Dict[str, int] = {}


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha(request: Request):
    """Generate a new CAPTCHA."""
    session_id = secrets.token_urlsafe(16)
    code = captcha_service.generate_captcha(session_id)
    return CaptchaResponse(captcha_code=code, session_id=session_id)


@router.get("/server-id")
async def get_server_id(request: Request):
    """Return current server instance ID."""
    return {"server_id": getattr(request.app.state, "server_instance_id", "srv-1")}


@router.get("/check-username", response_model=UsernameAvailabilityResponse)
async def check_username_availability(
    username: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Check if a username is available."""
    available, message = await auth_service.check_username_available(username)
    return UsernameAvailabilityResponse(available=available, message=message)


@router.post("/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    # Check username availability
    avail, msg = await auth_service.check_username_available(user.username)
    if not avail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # Check email uniqueness if provided
    email = getattr(user, "email", None)
    if email:
        profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == email.strip().lower())
        res_email = await auth_service.db.execute(profile_stmt)
        if res_email.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    # Hash password and create user
    hashed_pwd = await auth_service.hash_password(user.password)
    new_user = User(
        username=user.username.strip().lower(),
        email=email.strip().lower() if email else None,
        password_hash=hashed_pwd,
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    auth_service.db.add(new_user)
    await auth_service.db.flush()

    # Create associated profile with personal details if available
    profile = PersonalProfile(
        user_id=new_user.id,
        email=email.strip().lower() if email else None,
        first_name=getattr(user, "first_name", None),
        last_name=getattr(user, "last_name", None),
        age=getattr(user, "age", None),
        gender=getattr(user, "gender", None),
        last_updated=datetime.now(timezone.utc).isoformat()
    )
    auth_service.db.add(profile)
    await auth_service.db.commit()
    await auth_service.db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=profile.email,
        created_at=normalize_utc_iso(new_user.created_at, fallback_now=True),
        onboarding_completed=False,
        is_admin=False
    )


@router.post("/login", response_model=Token)
async def login(
    login_request: LoginRequest,
    response: Response,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login endpoint for username/password authentication."""
    ip = get_real_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")

    user = await auth_service.authenticate_user(
        login_request.identifier,
        login_request.password,
        ip_address=ip,
        user_agent=user_agent
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )

    # 2FA Check if enabled
    if getattr(user, "is_2fa_enabled", False):
        pre_auth_token = await auth_service.initiate_2fa_login(user)
        response.status_code = status.HTTP_202_ACCEPTED
        return TwoFactorAuthRequiredResponse(pre_auth_token=pre_auth_token)

    # Create tokens
    access_token = auth_service.create_access_token(data={
        "sub": user.username,
        "uid": user.id
    })
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    # Fetch user's profile for email
    stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
    res_p = await auth_service.db.execute(stmt)
    profile = res_p.scalar_one_or_none()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=getattr(settings, "cookie_secure", False),
        samesite=getattr(settings, "cookie_samesite", "lax"),
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


@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token cookie or body."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        # Try JSON body if cookie is not present
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            pass

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    try:
        access_token, new_refresh_token = await auth_service.refresh_access_token(refresh_token)

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=getattr(settings, "cookie_secure", False),
            samesite=getattr(settings, "cookie_samesite", "lax"),
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh_token
        )
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        response.delete_cookie("refresh_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token: Optional[str] = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout current user, revoke tokens, and clear cookies safely."""
    # 1. Clear refresh token cookie immediately
    response.delete_cookie(key="refresh_token", path="/")
    
    # 2. Revoke refresh token in database if available
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            await auth_service.revoke_refresh_token(refresh_token)
        except Exception as e:
            logger.debug(f"Error revoking refresh token on logout: {e}")

    # 3. Revoke access token if provided
    if token:
        try:
            await auth_service.revoke_access_token(token)
        except Exception as e:
            logger.debug(f"Error revoking access token on logout: {e}")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get authenticated user profile."""
    stmt = select(PersonalProfile).filter(PersonalProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=profile.email if profile else None,
        created_at=normalize_utc_iso(current_user.created_at, fallback_now=True),
        onboarding_completed=getattr(current_user, "onboarding_completed", False),
        is_admin=getattr(current_user, "is_admin", False)
    )


@router.post("/login/2fa", response_model=Token)
async def verify_2fa(
    login_request: TwoFactorLoginRequest,
    response: Response,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify 2FA code and issue tokens."""
    ip = get_real_ip(request)
    user = await auth_service.verify_2fa_login(login_request.pre_auth_token, login_request.code, ip_address=ip)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA verification code")

    access_token = auth_service.create_access_token(data={"sub": user.username, "uid": user.id})
    refresh_token = await auth_service.create_refresh_token(user.id)
    has_multiple_sessions = await auth_service.has_multiple_active_sessions(user.id)

    stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
    res_p = await auth_service.db.execute(stmt)
    profile = res_p.scalar_one_or_none()

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=getattr(settings, "cookie_secure", False),
        samesite=getattr(settings, "cookie_samesite", "lax"),
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


@router.post("/password-reset/initiate")
async def initiate_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Initiate password reset flow."""
    success, message = await auth_service.initiate_password_reset(reset_data.email, background_tasks)
    return {"message": message or "If an account exists with this email, password reset instructions have been sent."}


@router.post("/password-reset/complete")
async def complete_password_reset(
    request: PasswordResetComplete,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify OTP and set new password."""
    success, message = await auth_service.complete_password_reset(
        request.email,
        request.otp_code,
        request.new_password
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"message": message}


@router.post("/2fa/enable")
async def enable_2fa(
    confirm_request: TwoFactorConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Enable 2FA after verifying OTP."""
    if await auth_service.enable_2fa(current_user.id, confirm_request.code):
        return {"message": "2FA enabled successfully"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")


@router.post("/2fa/disable")
async def disable_2fa(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service)
):
    """Disable 2FA."""
    if await auth_service.disable_2fa(current_user.id):
        return {"message": "2FA disabled successfully"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to disable 2FA")
