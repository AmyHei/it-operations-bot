"""
Root endpoint.
"""
from fastapi import APIRouter
from app.models.schemas import MessageResponse

router = APIRouter()


@router.get("/", response_model=MessageResponse)
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return {"message": "IT Bot API running"} 