import os
import logging
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
from app.services.slack_service import slack_app

# Set up logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
print("Loading environment variables...")
load_dotenv()

# Verify tokens
if "SLACK_BOT_TOKEN" not in os.environ or "SLACK_APP_TOKEN" not in os.environ:
    print("Error: Missing Slack tokens in environment variables")
    print("Please check your .env file contains:")
    print("SLACK_BOT_TOKEN=xoxb-...")
    print("SLACK_APP_TOKEN=xapp-...")
    exit(1)

print(f"SLACK_BOT_TOKEN exists: {'SLACK_BOT_TOKEN' in os.environ}")
print(f"SLACK_APP_TOKEN exists: {'SLACK_APP_TOKEN' in os.environ}")

if __name__ == "__main__":
    try:
        print("Starting bot in Socket Mode...")
        handler = SocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
        print("Handler created, starting the app...")
        handler.start()
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}", exc_info=True)
        raise
