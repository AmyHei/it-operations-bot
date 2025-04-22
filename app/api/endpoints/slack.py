"""
Slack event handling endpoints.
"""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, Response, status
from app.services.slack_service import slack_handler, slack_app
from app.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/slack")

@router.post("/events")
async def slack_events(request: Request):
    """
    Endpoint for handling Slack events.
    This endpoint receives events from Slack and passes them to the Slack Bolt handler.
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.error("Slack signing secret not configured")
        raise HTTPException(status_code=500, detail="Slack integration not properly configured")
    
    # Let the SlackRequestHandler handle the request
    return await slack_handler.handle(request)

@router.post("/interactive")
async def slack_interactive(request: Request):
    """
    Endpoint for handling Slack interactive components (buttons, menus, etc.).
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.error("Slack signing secret not configured")
        raise HTTPException(status_code=500, detail="Slack integration not properly configured")
    
    # Let the SlackRequestHandler handle the request
    return await slack_handler.handle(request)

@router.get("/test")
async def test_slack_connection(response: Response):
    """
    Test the Slack connection by sending a test message to a channel.
    """
    if not settings.SLACK_BOT_TOKEN or not settings.SLACK_SIGNING_SECRET:
        logger.error("Slack credentials not properly configured")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Slack credentials not configured"}
    
    try:
        # Try to get the bot's own info as a simple API test
        result = slack_app.client.auth_test()
        if result["ok"]:
            bot_id = result["user_id"]
            bot_name = result["user"]
            return {
                "status": "success",
                "message": f"Successfully connected to Slack as {bot_name} (ID: {bot_id})",
                "bot_info": {
                    "id": bot_id,
                    "name": bot_name,
                    "team": result["team"]
                }
            }
        else:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"status": "error", "message": "Failed to authenticate with Slack API"}
    except Exception as e:
        logger.exception("Error testing Slack connection")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": f"Error connecting to Slack: {str(e)}"} 