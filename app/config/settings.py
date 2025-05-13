"""
Application settings and configuration.
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "IT Bot API"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Slack settings
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")
    
    # Microsoft Teams Bot credentials
    MICROSOFT_APP_ID: str = os.getenv("MICROSOFT_APP_ID", "")
    MICROSOFT_APP_PASSWORD: str = os.getenv("MICROSOFT_APP_PASSWORD", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in settings

# Create global settings object
settings = Settings() 