from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from ..config import get_settings
from ..schemas import UserCreate, Token, UserResponse, ErrorResponse, PasswordResetRequest, PasswordResetComplete, TwoFactorLoginRequest, TwoFactorAuthRequiredResponse, TwoFactorConfirmRequest
from ..services.db_service import get_db
from ..services.auth_service import AuthService
from ..constants.errors import ErrorCode
from ..constants.security_constants import REFRESH_TOKEN_EXPIRE_DAYS
from ..exceptions import AuthException
from api.root_models import User
from sqlalchemy.orm import Session

router = APIRouter()
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
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
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def register(user: UserCreate, auth_service: AuthService = Depends()):
    new_user = auth_service.register_user(user)
    return UserResponse(
        id=new_user.id, 
        username=new_user.username, 
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )


@router.post("/login", response_model=None, responses={401: {"model": ErrorResponse}, 202: {"model": TwoFactorAuthRequiredResponse}, 200: {"model": Token}})
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    request: Request,
    auth_service: AuthService = Depends()
):
    ip = request.client.host
    user = auth_service.authenticate_user(form_data.username, form_data.password, ip_address=ip)
    
    # PR 4: 2FA Check
    if user.is_2fa_enabled:
        pre_auth_token = auth_service.initiate_2fa_login(user)
        response.status_code = status.HTTP_202_ACCEPTED
        return TwoFactorAuthRequiredResponse(
            pre_auth_token=pre_auth_token
        )

    # Standard Login
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    
    refresh_token = auth_service.create_refresh_token(user.id)
    
    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, # Set to True in production with HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)


@router.post("/login/2fa", response_model=Token, responses={401: {"model": ErrorResponse}})
async def verify_2fa(
    login_request: TwoFactorLoginRequest,
    response: Response,
    auth_service: AuthService = Depends()
):
    """
    Verify 2FA code and issue tokens.
    """
    user = auth_service.verify_2fa_login(login_request.pre_auth_token, login_request.code)
    
    # Issue Tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.username}
    )
    
    refresh_token = auth_service.create_refresh_token(user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends()
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthException(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Refresh token missing"
        )
        
    access_token, new_refresh_token = auth_service.refresh_access_token(refresh_token)
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return Token(access_token=access_token, token_type="bearer", refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends()
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token)
        
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse(id=current_user.id, username=current_user.username, created_at=current_user.created_at)


@router.post("/password-reset/initiate")
async def initiate_password_reset(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends()
):
    """
    Initiate the password reset flow.
    ALWAYS returns success message to prevent user enumeration.
    """
    success, message = auth_service.initiate_password_reset(request.email)
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
    auth_service: AuthService = Depends()
):
    """
    Verify OTP and set new password.
    """
    success, message = auth_service.complete_password_reset(
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
    auth_service: AuthService = Depends()
):
    """Send OTP to verify email before enabling 2FA."""
    if auth_service.send_2fa_setup_otp(current_user):
        return {"message": "OTP sent to your email"}
    raise HTTPException(status_code=400, detail="Could not send OTP. Check email configuration.")


@router.post("/2fa/enable")
async def enable_2fa(
    request: TwoFactorConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends()
):
    """Enable 2FA after verifying OTP."""
    if auth_service.enable_2fa(current_user.id, request.code):
        return {"message": "2FA enabled successfully"}
    raise HTTPException(status_code=400, detail="Invalid code")


@router.post("/2fa/disable")
async def disable_2fa(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends()
):
    """Disable 2FA."""
    if auth_service.disable_2fa(current_user.id):
        return {"message": "2FA disabled"}
    raise HTTPException(status_code=400, detail="Action failed")
