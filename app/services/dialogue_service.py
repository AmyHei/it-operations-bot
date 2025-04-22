from typing import Dict, Optional
from app.services.servicenow_service import get_ticket_status
import logging

logger = logging.getLogger(__name__)

def get_next_action(intent_data: Dict, current_state: Optional[Dict] = None) -> Dict:
    """
    Determines the next action based on the intent from NLU service and current conversation state.
    
    Args:
        intent_data (Dict): Output from nlu_service.understand_intent containing intent information
        current_state (Dict, optional): Current conversation state
        
    Returns:
        Dict: Next action, response, and next state to be taken
    """
    # If we have a current state, handle it first
    if current_state and current_state.get("waiting_for") == "ticket_number":
        # Extract ticket number (simple implementation - in production, use regex or more robust parsing)
        ticket_number = intent_data.get("text", "").strip()
        
        # Get ticket status from ServiceNow
        status_data = get_ticket_status(ticket_number)
        
        # Return status and clear the state
        return {
            "action": "report_status",
            "response": f"Ticket {ticket_number} status is: {status_data['status']} - {status_data['short_description']}",
            "next_state": None  # Clear the state
        }
    
    # If no state or not waiting for ticket number, handle based on intent
    intent = intent_data.get("intent", "unknown")
    
    if intent == "check_ticket_status":
        return {
            "action": "ask_ticket_number",
            "response": "Okay, I can check a ticket status. What is the ticket number (e.g., INC12345)?",
            "next_state": {"waiting_for": "ticket_number"}
        }
    elif intent == "reset_password":
        return {
            "action": "confirm_password_reset",
            "response": "I can help with password resets. Are you sure you want to proceed?",
            "next_state": None
        }
    elif intent == "find_kb_article":
        return {
            "action": "ask_kb_query",
            "response": "What topic are you looking for in the knowledge base?",
            "next_state": None
        }
    else:  # unknown intent
        return {
            "action": "clarify",
            "response": "Sorry, I didn't understand that. Can you please rephrase?",
            "next_state": None
        }

def handle_message(message_text: str, current_state: Optional[Dict] = None) -> Dict:
    # 如果正在等待工单号
    if current_state and current_state.get("waiting_for") == "ticket_number":
        # 直接处理工单号查询，确保包含完整信息
        intent_data = {
            "intent": "check_ticket",
            "ticket_number": message_text,
            "text": message_text
        }
        logger.info(f"[DEBUG] 处理工单号查询: {intent_data}")
        dialogue_result = get_next_action(intent_data, current_state)
        return dialogue_result
    
    # If no state or not waiting for ticket number, handle based on intent
    intent = "unknown"
    
    if "INC" in message_text:
        intent = "check_ticket_status"
    elif "reset" in message_text.lower():
        intent = "reset_password"
    elif "knowledge" in message_text.lower():
        intent = "find_kb_article"
    
    if intent != "unknown":
        return get_next_action({"intent": intent})
    else:
        return {
            "action": "clarify",
            "response": "Sorry, I didn't understand that. Can you please rephrase?",
            "next_state": None
        } 