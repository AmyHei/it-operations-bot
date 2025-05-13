import logging
from botbuilder.core import ActivityHandler, TurnContext

class MyTeamsBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        message = turn_context.activity.text
        logging.info(f"Received Teams message: {message}")
        await turn_context.send_activity(f"Teams Bot: Received your message: {message}")
