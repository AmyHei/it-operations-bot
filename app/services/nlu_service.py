"""
Natural Language Understanding service.

This module provides basic intent detection capabilities.
It's designed as a placeholder that can be easily replaced with a more sophisticated 
ML-based model in the future.
"""
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)


def understand_intent(text: str) -> Dict[str, Any]:
    """
    Extract the intent and entities from user text.
    
    This is a simple rule-based function that detects basic intents.
    It's designed to be easily replaceable with a more sophisticated ML-based model.
    
    Args:
        text: The user's message text
        
    Returns:
        A dictionary containing the detected intent and entities
        Format: {"intent": str, "entities": Dict[str, Any]}
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Log the text being processed
    logger.debug(f"Processing text for intent detection: {text}")
    
    # Check for ticket status intent
    if "ticket status" in text_lower or "status of ticket" in text_lower or "check ticket" in text_lower:
        logger.info(f"Detected 'check_ticket_status' intent from: {text}")
        return {"intent": "check_ticket_status", "entities": {}}
    
    # Check for password reset intent
    if "password reset" in text_lower or "reset password" in text_lower or "change password" in text_lower:
        logger.info(f"Detected 'reset_password' intent from: {text}")
        return {"intent": "reset_password", "entities": {}}
    
    # Check for knowledge base intent
    if "knowledge base" in text_lower or "find article" in text_lower or "kb article" in text_lower:
        logger.info(f"Detected 'find_kb_article' intent from: {text}")
        return {"intent": "find_kb_article", "entities": {}}
    
    # Default to unknown intent
    logger.info(f"No specific intent detected from: {text}")
    return {"intent": "unknown", "entities": {}} 