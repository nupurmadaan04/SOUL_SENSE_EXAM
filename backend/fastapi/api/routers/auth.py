from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from ..config import get_settings
from ..schemas import UserCreate, Token, UserResponse
from ..services.db_service import get_db
from ..services.auth_service import AuthService
from api.root_models import User, PersonalProfile
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


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, auth_service: AuthService = Depends()):
    # 1. Normalize identifiers
    username_lower = user.username.lower()
    email_lower = user.email.lower()

    # 2. Check if username already exists
    if auth_service.db.query(User).filter(User.username == username_lower).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier already in use")

    # 3. Check if email already exists in PersonalProfile
    if auth_service.db.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier already in use")

    # 4. Create new user and profile in a transaction
    try:
        hashed_pw = auth_service.hash_password(user.password)
        new_user = User(
            username=username_lower,
            password_hash=hashed_pw
        )
        auth_service.db.add(new_user)
        auth_service.db.flush()  # Flush to get new_user.id for profile

        new_profile = PersonalProfile(
            user_id=new_user.id,
            email=email_lower,
            first_name=user.first_name,
            last_name=user.last_name,
            age=user.age,
            gender=user.gender
        )
        auth_service.db.add(new_profile)
        
        auth_service.db.commit()
        auth_service.db.refresh(new_user)
        
        return UserResponse(
            id=new_user.id, 
            username=new_user.username, 
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )
    except Exception as e:
        auth_service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    request: Request,
    auth_service: AuthService = Depends()
):
    ip = request.client.host
    user = auth_service.authenticate_user(form_data.username, form_data.password, ip_address=ip)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(hours=settings.jwt_expiration_hours)
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse(id=current_user.id, username=current_user.username, created_at=current_user.created_at)
