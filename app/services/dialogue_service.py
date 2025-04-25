"""
Dialogue management service for handling conversational flow.

This module is responsible for determining the next action to take based on
the user's intent and the current conversation state.
"""
from typing import Dict, Optional, Any
from app.services.servicenow_service import ServiceNowService, create_servicenow_ticket
from app.services.knowledge_service import search_knowledge_base
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize ServiceNow service
servicenow = ServiceNowService()

def get_next_action(intent_data: Dict[str, Any], current_state: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Determines the next action based on the intent from NLU service and current conversation state.
    
    Args:
        intent_data: Output from nlu_service.understand_intent containing intent and entity information
        current_state: Current conversation state retrieved from Redis
        
    Returns:
        Dict containing:
            - action: The type of action to take
            - response: The text response to send to the user
            - next_state: The updated conversation state to be saved in Redis, or None to clear the state
    """
    logger.info(f"Processing intent data: {intent_data}")
    logger.info(f"Current conversation state: {current_state}")
    
    # Initialize empty state if None is provided
    if current_state is None:
        current_state = {}
    
    # Handle specific conversation states first
    if current_state.get("waiting_for") == "ticket_number":
        # User is providing a ticket number
        return handle_ticket_number_input(intent_data, current_state)
    
    elif current_state.get("waiting_for") == "ticket_details":
        # User is providing details for creating a ticket
        return handle_ticket_details_input(intent_data, current_state)
    
    elif current_state.get("waiting_for") == "confirmation":
        # User is confirming or rejecting an action
        return handle_confirmation_input(intent_data, current_state)
    
    elif current_state.get("waiting_for") == "urgency_selection":
        # User has selected an urgency level
        return handle_urgency_selection(intent_data, current_state)
    
    elif current_state.get("waiting_for") == "software_name":
        # User is providing software name
        return handle_software_name_input(intent_data, current_state)
    
    elif current_state.get("waiting_for") == "software_confirmation":
        # User is confirming software request
        return handle_software_confirmation_input(intent_data, current_state)
        
    # If not in a specific state, process based on the detected intent
    intent = intent_data.get("intent", "unknown")
    entities = intent_data.get("entities", {})
    confidence = intent_data.get("confidence_score", 0)
    
    logger.info(f"Processing intent: {intent} with confidence: {confidence}")
    logger.info(f"Entities: {entities}")
    
    # Handle each intent
    if intent == "check_ticket_status":
        return handle_check_ticket_status(intent_data, entities)
        
    elif intent == "reset_password":
        return handle_reset_password(intent_data)
        
    elif intent == "find_kb_article":
        return handle_find_kb_article(intent_data, entities)
        
    elif intent == "create_ticket":
        return handle_create_ticket(intent_data, entities)
    
    elif intent == "request_software":
        return handle_request_software(intent_data, entities)
        
    elif intent == "greeting":
        return {
            "action": "greeting",
            "response": "Hello! I'm your IT support assistant. How can I help you today?",
            "next_state": None
        }
        
    elif intent == "general_question":
        return {
            "action": "respond_general",
            "response": "I can help with IT-related questions. I can check ticket status, help reset passwords, find knowledge base articles, create new support tickets, or request software. What would you like assistance with?",
            "next_state": None
        }
    
    # Default response for unknown intent
    return {
        "action": "clarify",
        "response": "I'm not sure I understand. I can help with checking ticket status, resetting passwords, finding knowledge base articles, creating support tickets, or requesting software. Could you please rephrase your request?",
        "next_state": None
    }

def handle_ticket_number_input(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user providing a ticket number"""
    # Extract ticket number from text or entities
    ticket_number = None
    
    # First check for ticket numbers in entities
    if "entities" in intent_data and "TICKET_NUMBER" in intent_data["entities"]:
        ticket_number = intent_data["entities"]["TICKET_NUMBER"][0]
    
    # Otherwise check the text for INC format
    elif "text" in intent_data:
        text = intent_data["text"]
        import re
        ticket_match = re.search(r'(INC\d+)', text, re.IGNORECASE)
        if ticket_match:
            ticket_number = ticket_match.group(1)
    
    if not ticket_number:
        return {
            "action": "ask_again",
            "response": "I didn't recognize a valid ticket number. Please provide a ticket number in the format INC12345.",
            "next_state": current_state  # Maintain the waiting state
        }
    
    try:
        # Get ticket status from ServiceNow
        ticket_status = servicenow.get_ticket_status(ticket_number)
        
        if "error" in ticket_status:
            return {
                "action": "report_error",
                "response": f"I couldn't find ticket {ticket_number}. Please check the ticket number and try again.",
                "next_state": None  # End the conversation flow
            }
        
        # Format a nice response with the ticket details
        status = ticket_status.get("state", "Unknown")
        description = ticket_status.get("short_description", "No description available")
        priority = ticket_status.get("priority", "Unknown")
        updated = ticket_status.get("updated_at", "Unknown")
        
        response = f"Ticket {ticket_number}:\nStatus: {status}\nPriority: {priority}\nDescription: {description}\nLast Updated: {updated}"
        
        # End the conversation flow
        return {
            "action": "report_status",
            "response": response,
            "next_state": None
        }
    except Exception as e:
        logger.error(f"Error getting ticket status: {str(e)}")
        return {
            "action": "error",
            "response": "I'm sorry, I encountered an error while checking the ticket status. Please try again later.",
            "next_state": None
        }

def handle_ticket_details_input(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user providing details for creating a ticket"""
    # Extract the description from the user's message
    description = intent_data.get("text", "")
    
    if not description or len(description) < 5:
        return {
            "action": "ask_again",
            "response": "Please provide more details about the issue you're experiencing.",
            "next_state": current_state  # Maintain the waiting state
        }
    
    # Get urgency from state or default to medium
    urgency = current_state.get("urgency", "3")
    
    try:
        # Create the ticket in ServiceNow
        result = create_servicenow_ticket(
            short_description=current_state.get("short_description", "IT Support Request"),
            description=description,
            urgency=urgency
        )
        
        if "error" in result:
            return {
                "action": "report_error",
                "response": f"I'm sorry, I couldn't create your ticket. Error: {result.get('details', 'Unknown error')}",
                "next_state": None
            }
        
        # Get the ticket number from the result
        ticket_number = result.get("ticket_number", "Unknown")
        
        # End the conversation flow
        return {
            "action": "ticket_created",
            "response": f"Success! I've created ticket {ticket_number} for you. The IT team will review it shortly.",
            "next_state": None
        }
    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        return {
            "action": "error",
            "response": "I'm sorry, I encountered an error while creating your ticket. Please try again later.",
            "next_state": None
        }

def handle_confirmation_input(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user confirmation response (yes/no)"""
    text = intent_data.get("text", "").lower()
    
    # Check for affirmative responses
    if any(word in text for word in ["yes", "yeah", "sure", "ok", "okay", "yep", "confirm", "是", "确认"]):
        # What were we waiting to confirm?
        action_type = current_state.get("action_type")
        
        if action_type == "password_reset":
            return {
                "action": "password_reset_confirmed",
                "response": "I'll start the password reset process. Please provide your employee ID or username.",
                "next_state": {"waiting_for": "employee_id", "action_type": "password_reset"}
            }
        elif action_type == "create_ticket":
            # Ask for ticket urgency via dropdown
            return {
                "action": "select_ticket_urgency",
                "response": "Please select the urgency for this ticket:",
                "response_type": "blocks",
                "blocks_config": {
                    "type": "select_urgency",
                    "text": "Please select the urgency level for your ticket:"
                },
                "next_state": {
                    "waiting_for": "urgency_selection", 
                    "action_type": "create_ticket",
                    "short_description": current_state.get("short_description", "IT Support Request")
                }
            }
        else:
            # Generic confirmation
            return {
                "action": "confirmed",
                "response": "Confirmed. How else can I help you?",
                "next_state": None
            }
    else:
        # User declined
        return {
            "action": "cancelled",
            "response": "I've cancelled the request. Is there anything else I can help with?",
            "next_state": None
        }

def handle_urgency_selection(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user selection of ticket urgency"""
    # If urgency was provided via dropdown, it will be in intent_data["selected_option"]
    selected_urgency = intent_data.get("selected_option")
    
    if not selected_urgency:
        # If no urgency selected (shouldn't happen with dropdown), default to Medium
        selected_urgency = "3"
        logger.warning(f"No urgency provided, defaulting to Medium (3)")
    
    # Save the selected urgency and move to asking for ticket details
    return {
        "action": "create_ticket_urgency_selected",
        "response": "Thank you. Now please describe the issue you're experiencing in detail.",
        "next_state": {
            "waiting_for": "ticket_details", 
            "action_type": "create_ticket",
            "short_description": current_state.get("short_description", "IT Support Request"),
            "urgency": selected_urgency
        }
    }

def handle_check_ticket_status(intent_data: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle check ticket status intent"""
    # Check if a ticket number was provided in the entities
    if "TICKET_NUMBER" in entities and entities["TICKET_NUMBER"]:
        ticket_number = entities["TICKET_NUMBER"][0]
        
        try:
            # Get ticket status directly
            ticket_status = servicenow.get_ticket_status(ticket_number)
            
            if "error" in ticket_status:
                return {
                    "action": "report_error",
                    "response": f"I couldn't find ticket {ticket_number}. Please check the ticket number and try again.",
                    "next_state": None
                }
            
            # Format a nice response with the ticket details
            status = ticket_status.get("state", "Unknown")
            description = ticket_status.get("short_description", "No description available")
            priority = ticket_status.get("priority", "Unknown")
            
            response = f"Ticket {ticket_number}:\nStatus: {status}\nPriority: {priority}\nDescription: {description}"
            
            return {
                "action": "report_status",
                "response": response,
                "next_state": None
            }
        except Exception as e:
            logger.error(f"Error getting ticket status: {str(e)}")
            return {
                "action": "error",
                "response": "I'm sorry, I encountered an error while checking the ticket status. Please try again later.",
                "next_state": None
            }
    
    # No ticket number provided, ask for it
    return {
        "action": "ask_ticket_number",
        "response": "I can check the status of your ticket. Could you please provide the ticket number (e.g., INC12345)?",
        "next_state": {"waiting_for": "ticket_number", "action_type": "check_ticket"}
    }

def handle_reset_password(intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle password reset intent"""
    return {
        "action": "confirm_reset",
        "response": "I can help you reset your password. This will generate a temporary password. Would you like to proceed?",
        "response_type": "blocks",
        "blocks_config": {
            "type": "confirm_password_reset",
            "text": "I can help you reset your password. This will generate a temporary password that you'll need to change upon first login."
        },
        "next_state": {"waiting_for": "confirmation", "action_type": "password_reset"}
    }

def handle_find_kb_article(intent_data: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle find knowledge base article intent"""
    # Extract topics from entities if available
    topics = []
    
    if "MISC" in entities:
        topics.extend(entities["MISC"])
    if "ORG" in entities:
        topics.extend(entities["ORG"])
    
    if topics:
        topics_str = ", ".join(topics)
        
        # Search for articles using the knowledge service
        query = topics_str
        try:
            articles = search_knowledge_base(query, max_results=3)
            
            if articles:
                return {
                    "action": "display_kb_articles",
                    "response": f"Here are some articles about {topics_str}:",
                    "response_type": "blocks",
                    "blocks_config": {
                        "type": "kb_results",
                        "articles": articles,
                        "query": query
                    },
                    "next_state": None
                }
            else:
                return {
                    "action": "no_kb_results",
                    "response": f"I couldn't find any articles about {topics_str}. Please try a different search term or consider creating a support ticket.",
                    "next_state": None
                }
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return {
                "action": "error",
                "response": "I'm sorry, I encountered an error while searching the knowledge base. Please try again later.",
                "next_state": None
            }
    else:
        return {
            "action": "ask_topic",
            "response": "I can help you find knowledge base articles. What topic are you interested in?",
            "next_state": {"waiting_for": "kb_topic", "action_type": "find_kb"}
        }

def handle_create_ticket(intent_data: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create ticket intent"""
    # Extract issue description if present
    description = ""
    urgency = "3"  # Default to Medium
    
    # Extract location if present
    location = ""
    if "LOC" in entities and entities["LOC"]:
        location = entities["LOC"][0]
    
    # Extract the issue type if present in the text
    issue_type = "IT support request"
    text = intent_data.get("text", "")
    
    if "network" in text.lower():
        issue_type = "Network issue"
    elif "password" in text.lower():
        issue_type = "Password issue"
    elif "software" in text.lower() or "program" in text.lower() or "application" in text.lower():
        issue_type = "Software issue"
    elif "hardware" in text.lower() or "computer" in text.lower() or "laptop" in text.lower():
        issue_type = "Hardware issue"
    
    # Create a short description based on the information we have
    short_description = issue_type
    if location:
        short_description += f" at {location}"
    
    # Ask for confirmation
    return {
        "action": "confirm_create_ticket",
        "response": f"I'll help you create a ticket for: '{short_description}'. Would you like to proceed?",
        "next_state": {
            "waiting_for": "confirmation", 
            "action_type": "create_ticket",
            "short_description": short_description,
            "urgency": urgency,
            "location": location
        }
    }

def handle_software_name_input(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user providing a software name"""
    # Extract the software name from the user's message
    software_name = intent_data.get("text", "").strip()
    
    if not software_name or len(software_name) < 2:
        return {
            "action": "ask_again",
            "response": "I couldn't understand which software you need. Please specify the name of the software you'd like to request.",
            "next_state": current_state  # Maintain the waiting state
        }
    
    # Check if software_name was captured by NER
    software_from_ner = False
    if "entities" in intent_data and "SOFTWARE_NAME" in intent_data["entities"]:
        software_name = intent_data["entities"]["SOFTWARE_NAME"][0]
        software_from_ner = True
    
    # Ask for confirmation
    return {
        "action": "confirm_software_request",
        "response": f"Got it. You want to request {software_name}. Is that correct? (Yes/No)",
        "next_state": {
            "waiting_for": "software_confirmation", 
            "action_type": "request_software",
            "software_name": software_name
        }
    }

def handle_software_confirmation_input(intent_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user confirming software request"""
    text = intent_data.get("text", "").lower()
    software_name = current_state.get("software_name", "the requested software")
    
    # Check for affirmative responses
    if any(word in text for word in ["yes", "yeah", "sure", "ok", "okay", "yep", "confirm", "是", "确认"]):
        # Create a ticket for the software request
        try:
            # Here you would typically create a ticket or call a service
            # For now, we'll just simulate success
            return {
                "action": "execute_software_request",
                "details": {"software_name": software_name},
                "response": f"Great! I've submitted a request for {software_name}. The IT team will review your request and contact you shortly. Your request has been tracked.",
                "next_state": None  # Clear the state
            }
        except Exception as e:
            logger.error(f"Error processing software request: {str(e)}")
            return {
                "action": "error",
                "response": "I'm sorry, I encountered an error while processing your software request. Please try again later.",
                "next_state": None
            }
    else:
        # User declined, ask for correct software
        return {
            "action": "ask_software_name",
            "response": "I see. Please provide the correct name of the software you'd like to request.",
            "next_state": {"waiting_for": "software_name", "action_type": "request_software"}
        }

def handle_request_software(intent_data: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, Any]:
    """Handle software request intent"""
    # Check if a software name was provided in the entities
    if "SOFTWARE_NAME" in entities and entities["SOFTWARE_NAME"]:
        software_name = entities["SOFTWARE_NAME"][0]
        
        # Ask for confirmation
        return {
            "action": "confirm_software_request",
            "response": f"I see you want to request {software_name}. Is that correct? (Yes/No)",
            "next_state": {
                "waiting_for": "software_confirmation", 
                "action_type": "request_software",
                "software_name": software_name
            }
        }
    else:
        # No software name provided, ask for it
        return {
            "action": "ask_software_name",
            "response": "I can help you request software. Which software would you like to request?",
            "next_state": {"waiting_for": "software_name", "action_type": "request_software"}
        }

def handle_message(message_text: str, current_state: Optional[Dict] = None) -> Dict:
    # If waiting for ticket number
    if current_state and current_state.get("waiting_for") == "ticket_number":
        # Directly process ticket number query
        intent_data = {
            "intent": "check_ticket",
            "ticket_number": message_text,
            "text": message_text
        }
        logger.info(f"[DEBUG] Processing ticket number query: {intent_data}")
        dialogue_result = get_next_action(intent_data, current_state)
        return dialogue_result
    
    # If waiting for software name
    elif current_state and current_state.get("waiting_for") == "software_name":
        # Process as software name input
        intent_data = {
            "intent": "request_software",
            "text": message_text,
            "entities": {}
        }
        logger.info(f"[DEBUG] Processing software name input: {intent_data}")
        dialogue_result = get_next_action(intent_data, current_state)
        return dialogue_result
    
    # If no specific state, handle based on intent
    intent = "unknown"
    
    if "INC" in message_text:
        intent = "check_ticket_status"
    elif "reset" in message_text.lower():
        intent = "reset_password"
    elif "knowledge" in message_text.lower():
        intent = "find_kb_article"
    elif "software" in message_text.lower() or "install" in message_text.lower():
        intent = "request_software"
    
    if intent != "unknown":
        return get_next_action({"intent": intent, "text": message_text})
    else:
        return {
            "action": "clarify",
            "response": "Sorry, I didn't understand that. Can you please rephrase?",
            "next_state": None
        } 