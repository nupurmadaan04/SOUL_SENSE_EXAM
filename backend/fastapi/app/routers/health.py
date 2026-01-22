from fastapi import APIRouter, Depends
from ..models.schemas import HealthResponse
from ..routers.auth import get_current_user
from app.models import User
from typing import Annotated

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    return {"status": "ok"}


@router.get("/welcome")
async def welcome(current_user: Annotated[User, Depends(get_current_user)]) -> dict:
    return {"message": f"Welcome {current_user.username}!", "user_id": current_user.id}
