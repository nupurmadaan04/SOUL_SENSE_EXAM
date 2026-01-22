from fastapi import APIRouter
from ..models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    """Health check endpoint - returns API status"""
    return {"status": "ok"}


@router.get("/")
async def root() -> dict:
    """Root endpoint with API information"""
    return {
        "message": "Soul Sense API",
        "version": "1.0.0",
        "status": "running"
    }
