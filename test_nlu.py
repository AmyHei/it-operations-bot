"""
Test script for the NLU service.
This allows testing the intent detection without needing to set up Slack.
"""
import sys
import logging
from app.services.nlu_service import understand_intent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    print("IT Bot NLU Test")
    print("====================")
    print("Type 'exit' to quit")
    print("Sample commands to try:")
    print("- What's the status of my ticket?")
    print("- I need to reset my password")
    print("- Can you find an article in the knowledge base?")
    print("====================")
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        # Check for exit command
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
            
        # Process with NLU
        result = understand_intent(user_input)
        intent = result["intent"]
        
        # Generate response based on intent
        if intent == "check_ticket_status":
            response = "I'll check the status of your ticket. This functionality will be implemented soon."
        elif intent == "reset_password":
            response = "I can help you reset your password. This functionality will be implemented soon."
        elif intent == "find_kb_article":
            response = "I'll search the knowledge base for articles. This functionality will be implemented soon."
        else:
            response = f"I'm not sure what you're asking for. Can you try rephrasing your request?"
        
        # Print response and debug info
        print(f"\nBot: {response}")
        print(f"\nDEBUG:")
        print(f"  Intent: {intent}")
        print(f"  Result: {result}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to user interrupt...")
        sys.exit(0) 