from fastapi import APIRouter
from ..models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    """Health check endpoint - returns API status"""
    return {"status": "ok"}



