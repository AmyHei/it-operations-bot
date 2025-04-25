from fastapi import FastAPI, Request
from app.services.slack_service import slack_handler
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="IT Operations Bot")

@app.get("/")
async def root():
    return {"message": "IT Operations Bot is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/slack/events")
async def endpoint(req: Request):
    return await slack_handler.handle(req)

# Optional: Add more endpoints as needed
@app.get("/slack/test")
async def test_slack():
    return {"message": "Slack connection test endpoint"} 