"""
Startup service for initializing all integrations when the application starts.
"""
import logging
import asyncio
from app.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

async def initialize_services():
    """
    Initialize all external services and integrations.
    This function runs when the FastAPI app starts.
    """
    logger.info("Initializing services...")
    
    # Check if Slack integration is configured
    if settings.SLACK_BOT_TOKEN and settings.SLACK_SIGNING_SECRET:
        logger.info("Slack integration is configured")
    else:
        logger.warning("Slack integration is not properly configured. "
                      "Please set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET in .env file.")
    
    logger.info("Services initialization complete")


async def cleanup_services():
    """
    Clean up all external services and integrations.
    This function runs when the FastAPI app shuts down.
    """
    logger.info("Cleaning up services...")
    
    # Add cleanup logic for any services as needed
    await asyncio.sleep(0.1)  # Just to make this an async function
    
    logger.info("Services cleanup complete") 