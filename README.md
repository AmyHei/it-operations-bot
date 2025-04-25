# IT Operations Chatbot

An intelligent Slack bot that helps with IT support tasks like checking ticket status, creating tickets, finding knowledge base articles, and resetting passwords.

## Features

- **Natural Language Processing**: Understands user intent through NLU service
- **Multi-channel Support**: Works in public channels and direct messages
- **Thread-based Conversations**: Maintains context within conversation threads
- **ServiceNow Integration**: Retrieve ticket status and create new tickets
- **State Management**: Redis-based conversation state tracking for persistence
- **Scalable Architecture**: Modular service-based design

## Architecture

The application follows a modular service-based architecture:

```
app/
├── services/
│   ├── slack_service.py     # Handles Slack events and message routing
│   ├── nlu_service.py       # Natural language understanding
│   ├── dialogue_service.py  # Manages conversation flow and actions
│   ├── servicenow_service.py # Integration with ServiceNow
│   └── state_service.py     # Redis-based conversation state management
├── utils/
│   └── logger.py            # Logging configuration
├── config.py                # Application configuration
└── main.py                  # Application entry point
```

## Setup

### Prerequisites

- Python 3.8+
- Redis server
- Slack App with Bot and Socket Mode enabled
- ServiceNow instance credentials

### Environment Variables

Create a `.env` file with the following variables:

```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SERVICENOW_INSTANCE=your-instance
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start the bot:
   ```
   python app/main.py
   ```

## Testing

The project includes several test scripts:

- `test_socket.py`: Test Slack Socket Mode connection
- `test_servicenow.py`: Test ServiceNow API connection
- `test_state_service.py`: Test Redis state management
- `test_conversation_flow.py`: Interactive test of the entire conversation flow

## Usage

### In Public Channels

1. Mention the bot with your request:
   ```
   @IT operations what's the status of ticket INC12345?
   ```
2. Continue the conversation in the same thread without mentioning the bot again.

### In Direct Messages

Just send your request directly to the bot:
```
what's the status of ticket INC12345?
```

## Example Intents

- Check ticket status: "What's the status of INC12345?"
- Create a ticket: "I need to create a ticket for my broken monitor"
- Reset password: "I need to reset my password"
- Find KB article: "How do I connect to the VPN?"

## Development

To run the bot in development mode with hot reloading:

```
python -m app.main
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request 