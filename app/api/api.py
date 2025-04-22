"""
API router that includes all endpoint routers.
"""
from fastapi import APIRouter
from app.api.endpoints import root, health, slack

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(root.router, tags=["general"])
api_router.include_router(health.router, tags=["general"])
api_router.include_router(slack.router, tags=["slack"]) 