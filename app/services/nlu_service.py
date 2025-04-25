"""
Natural Language Understanding service.

This module provides intent detection capabilities using Hugging Face's transformers
library for zero-shot text classification. The model classifies user input into
predefined intents and returns the most likely intent along with a confidence score.
It also extracts named entities using a pre-trained NER model.
"""
import logging
import os
import re
from typing import Dict, Any, List, Tuple
import torch
from transformers import pipeline

# Set up logging
logger = logging.getLogger(__name__)

# Define candidate labels for intent classification
INTENT_LABELS = [
    "check ticket status", 
    "reset password", 
    "find knowledge base article", 
    "create ticket", 
    "greeting", 
    "general question"
]

# Map from model labels to internal intent names
INTENT_MAPPING = {
    "check ticket status": "check_ticket_status",
    "reset password": "reset_password",
    "find knowledge base article": "find_kb_article",
    "create ticket": "create_ticket",
    "greeting": "greeting",
    "general question": "general_question"
}

# Confidence threshold for intent classification
CONFIDENCE_THRESHOLD = 0.7

# Load models at module level so they're only loaded once when the service starts
try:
    logger.info("Loading NLU models...")
    # Use CUDA if available for faster inference
    device = 0 if torch.cuda.is_available() else -1
    
    # Load zero-shot classification model
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=device
    )
    
    # Load Named Entity Recognition model
    # The "simple" aggregation strategy helps group word pieces into meaningful entities
    ner_pipeline = pipeline(
        "ner", 
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        aggregation_strategy="simple",
        device=device
    )
    
    logger.info("Models loaded successfully")
except Exception as e:
    logger.error(f"Error loading NLU models: {str(e)}")
    classifier = None
    ner_pipeline = None

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from text using the NER pipeline.
    
    This function processes the text through a pre-trained NER model and
    organizes the results by entity type.
    
    Args:
        text: The user's message text
        
    Returns:
        A dictionary where keys are entity types (e.g., "ORG", "PER") and 
        values are lists of extracted entities of that type.
    """
    if ner_pipeline is None:
        logger.error("NER model not available")
        return {}
    
    try:
        # Run the NER pipeline on the input text
        ner_results = ner_pipeline(text)
        
        # Process and organize results by entity type
        entities_by_type = {}
        for item in ner_results:
            entity_type = item["entity_group"]  # e.g., "ORG", "PER", "LOC", "MISC"
            entity_text = item["word"]
            entity_score = item["score"]
            
            # Only include entities with confidence above threshold
            if entity_score >= 0.8:
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                
                # Avoid duplicates
                if entity_text not in entities_by_type[entity_type]:
                    entities_by_type[entity_type].append(entity_text)
                    logger.debug(f"Extracted entity: {entity_text} ({entity_type}) with score {entity_score:.2f}")
        
        return entities_by_type
        
    except Exception as e:
        logger.error(f"Error during entity extraction: {str(e)}")
        return {}

def understand_intent(text: str) -> Dict[str, Any]:
    """
    Extract the intent and entities from user text using zero-shot classification
    and named entity recognition.
    
    This function uses the Hugging Face transformers library to:
    1. Classify the user's input into one of the predefined intent categories
    2. Extract named entities from the text
    
    NOTE: Standard NER models like the one used here recognize common entity types:
    - PER: Person names
    - ORG: Organization names
    - LOC: Locations
    - MISC: Miscellaneous entities
    
    They may not specifically recognize IT-specific entities like ticket numbers
    (which might be classified as MISC or missed entirely). Custom fine-tuning
    would be needed for domain-specific entity recognition.
    
    Args:
        text: The user's message text
        
    Returns:
        A dictionary containing the detected intent, entities, and confidence score
        Format: {"intent": str, "entities": Dict[str, List[str]], "confidence_score": float}
    """
    # Log the text being processed
    logger.debug(f"Processing text for intent detection: {text}")
    
    # Check if models were successfully loaded
    if classifier is None:
        logger.error("Classification model not available, returning unknown intent")
        return {"intent": "unknown", "entities": {}, "confidence_score": None}
    
    try:
        # Perform zero-shot classification for intent
        intent_result = classifier(text, INTENT_LABELS, multi_label=False)
        
        # Get the top label and its score
        top_label = intent_result["labels"][0]
        top_score = intent_result["scores"][0]
        
        logger.debug(f"Top predicted intent: {top_label} with score: {top_score}")
        
        # Extract entities using NER
        entities = extract_entities(text)
        
        # Special handling for certain intents
        intent = "unknown"
        if top_score >= CONFIDENCE_THRESHOLD:
            # Map the model's label to our internal intent name
            intent = INTENT_MAPPING.get(top_label, "unknown")
        
        # Ticket pattern recognition for ServiceNow ticket numbers
        # This augments the NER model which might not specifically detect ticket numbers
        ticket_pattern = re.compile(r'\b(INC|REQ|TASK|RITM)\d{5,}\b', re.IGNORECASE)
        ticket_matches = ticket_pattern.findall(text)
        
        if ticket_matches:
            # Check if these ticket numbers are already captured in any entity category
            existing_tickets = []
            for entity_list in entities.values():
                existing_tickets.extend([e for e in entity_list if ticket_pattern.search(e)])
            
            # Add non-duplicate tickets to the entities dictionary under TICKET_NUMBER key
            new_tickets = [t for t in ticket_matches if t not in existing_tickets]
            if new_tickets:
                entities["TICKET_NUMBER"] = new_tickets
                logger.debug(f"Found ticket references via pattern matching: {new_tickets}")
            
        # Log the final result
        if intent != "unknown":
            logger.info(f"Detected '{intent}' intent from: '{text}' with confidence: {top_score:.2f}")
        else:
            logger.info(f"Intent below confidence threshold ({top_score:.2f}): '{text}'")
        
        if entities:
            logger.info(f"Extracted entities: {entities}")
            
        return {
            "intent": intent, 
            "entities": entities, 
            "confidence_score": float(top_score)
        }
            
    except Exception as e:
        logger.error(f"Error during intent classification: {str(e)}")
        return {"intent": "unknown", "entities": {}, "confidence_score": None} 