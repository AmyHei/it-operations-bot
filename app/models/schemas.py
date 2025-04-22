"""
Pydantic schemas for request and response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class MessageResponse(BaseModel):
    """Basic message response schema."""
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    details: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str = "1.0.0"
    service: str = "itbot" 