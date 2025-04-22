"""
Health check endpoint.
"""
from fastapi import APIRouter
from app.models.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "healthy"} 