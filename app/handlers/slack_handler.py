# ... existing code ...

def _process_and_respond(event_data, say, context=None):
    """
    Process the user message and respond accordingly.
    """
    logger.info(f"Processing message: {event_data}")
    
    user_id = event_data.get("user")
    channel_id = event_data.get("channel")
    text = event_data.get("text", "")
    thread_ts = event_data.get("thread_ts", event_data.get("ts"))
    
    # Get current conversation state, if any
    current_state = get_conversation_state(user_id, channel_id)
    
    # Process the message through our dialogue service
    result = dialogue_service.handle_message(text, current_state)
    
    # Get the dialogue action
    action = result.get("action", "clarify")
    response = result.get("response", "I'm not sure I understand.")
    next_state = result.get("next_state")
    
    # Set the conversation state for future interactions
    if next_state is not None:
        logger.info(f"Setting conversation state: {next_state}")
        set_conversation_state(user_id, channel_id, next_state)
    else:
        # Clear state if next_state is None
        logger.info("Clearing conversation state")
        clear_conversation_state(user_id, channel_id)
    
    # Perform specific actions based on the dialogue result
    if action == "ticket_info":
        # Includes details about a ticket
        ticket_details = result.get("details", {})
        _format_and_send_ticket_info(say, response, ticket_details, thread_ts)
    
    elif action == "create_ticket_result":
        # Ticket creation result
        _format_and_send_ticket_creation(say, response, result.get("details", {}), thread_ts)
    
    elif action == "kb_article":
        # Knowledge base article
        _format_and_send_kb_article(say, response, result.get("details", {}), thread_ts)
    
    elif action == "execute_software_request":
        # Software request confirmation
        software_details = result.get("details", {})
        _format_and_send_software_request(say, response, software_details, thread_ts)
    
    else:
        # Simple text response for other actions
        try:
            say(text=response, thread_ts=thread_ts)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            say(text="I'm having trouble responding right now. Please try again later.", thread_ts=thread_ts)

# ... existing code ...

def _format_and_send_software_request(say, message, details, thread_ts=None):
    """
    Format and send a software request confirmation message
    """
    try:
        # Extract software details
        software_name = details.get("software_name", "the requested software")
        
        # Create blocks for structured message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Software Request Confirmation*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Software:*\n{software_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\nPending Approval"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "IT Support will review your request and contact you if additional information is needed."
                    }
                ]
            }
        ]
        
        # Send the message with blocks
        say(text=message, blocks=blocks, thread_ts=thread_ts)
    except Exception as e:
        logger.error(f"Error formatting software request message: {str(e)}")
        # Fallback to simple message if formatting fails
        say(text=message, thread_ts=thread_ts)

# ... existing code ...