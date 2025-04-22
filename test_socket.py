import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

# Initialize the app with the bot token from environment
app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("app_mention")
def handle_mention(event, say):
    say("Hello!")

# Start the app using the app token from environment
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
