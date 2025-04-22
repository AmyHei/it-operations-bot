"""
Main FastAPI application.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.api import api_router
from app.services.startup_service import initialize_services, cleanup_services

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="IT Bot API - A FastAPI-based IT support chatbot backend",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Register startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run initialization logic on application startup."""
    logger.info("Application starting up...")
    await initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """Run cleanup logic on application shutdown."""
    logger.info("Application shutting down...")
    await cleanup_services() 