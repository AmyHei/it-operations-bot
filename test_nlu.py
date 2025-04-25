#!/usr/bin/env python
"""
Test script for the NLU service with Named Entity Recognition.
"""
import logging
import sys
import json
from app.services.nlu_service import understand_intent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Run an interactive test of the NLU service."""
    print("IT Bot NLU Test - With Named Entity Recognition")
    print("==============================================")
    print("Type 'exit' to quit")
    print("Sample commands to try:")
    print("- What's the status of my ticket INC0010001?")
    print("- I need to reset my password for my account at Microsoft")
    print("- Can you find an article in the knowledge base about VPN access to ServiceNow?")
    print("- Hi, I'm John from Marketing, and I need help with my laptop")
    print("- I'd like to create a new ticket for a network issue at the New York office")
    print("- I need to check on the progress of REQ12345 and INC54321")
    print("==============================================\n")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
        
        result = understand_intent(user_input)
        
        # Display the bot's response based on the intent
        intent = result.get('intent', 'unknown')
        confidence = result.get('confidence_score')
        entities = result.get('entities', {})
        
        # Initialize response variable with default value
        response = "I'm not sure what you're asking for. Can you try rephrasing your request?"
        
        if intent == "check_ticket_status":
            if "TICKET_NUMBER" in entities and entities["TICKET_NUMBER"]:
                ticket_nums = entities["TICKET_NUMBER"]
                if len(ticket_nums) == 1:
                    response = f"I'll check the status of ticket {ticket_nums[0]} for you."
                else:
                    tickets_str = ", ".join(ticket_nums)
                    response = f"I'll check the status of these tickets: {tickets_str}."
            else:
                response = "I'll check the status of your ticket. Which ticket number are you inquiring about?"
        elif intent == "reset_password":
            if "ORG" in entities and entities["ORG"]:
                org = entities["ORG"][0]
                response = f"I can help you reset your password for {org}. Would you like to proceed?"
            else:
                response = "I can help you reset your password. Would you like to proceed?"
        elif intent == "find_kb_article":
            topics = []
            if "MISC" in entities:
                topics.extend(entities["MISC"])
            if "ORG" in entities:
                topics.extend(entities["ORG"])
                
            if topics:
                topics_str = ", ".join(topics)
                response = f"I'll search the knowledge base for articles about {topics_str}."
            else:
                response = "I'll search the knowledge base. What topic are you interested in?"
        elif intent == "create_ticket":
            location = entities.get("LOC", [""])[0]
            issue_type = "network issue"  # Default
            
            if location:
                response = f"I'll help you create a new ticket for a {issue_type} at {location}. What's the specific issue you're experiencing?"
            else:
                response = f"I'll help you create a new ticket for a {issue_type}. What's the specific issue you're experiencing?"
        elif intent == "greeting":
            person_name = ""
            if "PER" in entities and entities["PER"]:
                person_name = entities["PER"][0]
                
            org = ""
            if "ORG" in entities and entities["ORG"]:
                org = f" from {entities['ORG'][0]}"
                
            if person_name:
                response = f"Hello {person_name}{org}! How can I assist you today?"
            else:
                response = "Hello! How can I assist you today?"
        elif intent == "general_question":
            response = "I'll do my best to answer your question."
        
        print(f"\nBot: {response}")
        print(f"\nDEBUG:")
        print(f"  Intent: {intent}")
        if confidence is not None:
            print(f"  Confidence: {confidence:.4f}")
        if entities:
            print(f"  Entities: {json.dumps(entities, indent=2)}")
        print(f"  Result: {result}")
            
if __name__ == "__main__":
    main()