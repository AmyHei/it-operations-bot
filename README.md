# IT Operations Slack Bot

A Slack bot for IT operations that helps with:
- Checking ticket status
- Password reset requests
- Knowledge base article searches

## Features

- Real-time ticket status checking
- Natural language understanding
- Conversation state management
- Automatic response handling

## Setup

1. Clone the repository
2. Create a `.env` file with your Slack credentials:
```
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-token
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the bot:
```bash
python run_slack_bot.py
```

## Development

The bot uses:
- FastAPI for the web server
- Slack Bolt for Python
- Custom NLU and dialogue management

## Project Structure

```
.
├── app/
│   ├── config/
│   │   └── settings.py
│   ├── services/
│   │   ├── dialogue_service.py
│   │   ├── nlu_service.py
│   │   ├── servicenow_service.py
│   │   └── slack_service.py
│   └── main.py
├── .env
├── .gitignore
├── README.md
├── requirements.txt
└── run_slack_bot.py
```

## API Endpoints

- `GET /`: Root endpoint
- `GET /health`: Health check
- `POST /slack/events`: Slack events endpoint
- `POST /slack/interactive`: Slack interactive endpoint
- `GET /slack/test`: Test Slack connection

## Slack Event Handling

The application listens for mentions (`@botname`) in Slack channels through the `/slack/events` endpoint. Configure your Slack app to send events to this endpoint.

In Slack app settings:
1. Go to "Event Subscriptions"
2. Enable events
3. Set the Request URL to `https://your-domain.com/slack/events`
4. Subscribe to bot events: `app_mention`
5. Save your changes

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| API_HOST | API host | 0.0.0.0 |
| API_PORT | API port | 8000 |
| DEBUG | Enable debug mode | False |
| LOG_LEVEL | Logging level | INFO |
| SLACK_BOT_TOKEN | Slack Bot User OAuth Token | - |
| SLACK_SIGNING_SECRET | Slack Signing Secret | - |
| SLACK_APP_TOKEN | Slack App User OAuth Token | - | 