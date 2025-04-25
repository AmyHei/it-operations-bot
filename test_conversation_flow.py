#!/usr/bin/env python3
import os
import json
import logging
import sys
from dotenv import load_dotenv

# Import services
sys.path.append('.')
from app.services.nlu_service import analyze_intent
from app.services.dialogue_service import get_response
from app.services.state_service import get_state, save_state, delete_state

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("conversation_test")

# Load environment variables
load_dotenv()

def simulate_conversation():
    """
    Simulate a conversation with the bot and display how state is managed
    """
    # Test user and channel IDs
    user_id = "U_TEST_USER"
    channel_id = "C_TEST_CHANNEL"
    thread_ts = "T_TEST_THREAD"
    
    # Check if state already exists for this user
    current_state = get_state(user_id, channel_id, thread_ts)
    
    if current_state:
        logger.info(f"Found existing state for user {user_id}:")
        logger.info(json.dumps(current_state, indent=2))
        
        choice = input("Do you want to (C)ontinue with this state or (R)eset it? [C/R]: ").upper()
        if choice == 'R':
            delete_state(user_id, channel_id, thread_ts)
            logger.info("State reset. Starting fresh conversation.")
            current_state = {
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "intent": None,
                "context": {},
                "history": []
            }
    else:
        logger.info(f"No existing state found for user {user_id}. Starting fresh conversation.")
        current_state = {
            "user_id": user_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "intent": None,
            "context": {},
            "history": []
        }

    print("\n" + "="*50)
    print("CONVERSATION SIMULATOR")
    print("="*50)
    print("Type your messages to the bot. Type 'exit' to end the conversation.")
    print("="*50 + "\n")
    
    # Start conversation loop
    while True:
        # Get user input
        user_input = input("\n🧑 User: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            break
        
        try:
            # Add message to history
            if "history" not in current_state:
                current_state["history"] = []
            
            current_state["history"].append({
                "role": "user",
                "content": user_input
            })
            
            # Analyze intent
            intent_data = analyze_intent(user_input)
            
            # Update state with new intent if confidence is high enough
            if intent_data["confidence"] > 0.6:
                current_state["intent"] = intent_data["intent"]
                current_state["context"].update(intent_data["entities"])
            
            logger.info(f"Detected intent: {intent_data['intent']} (confidence: {intent_data['confidence']})")
            
            # Get response from dialogue manager
            response = get_response(intent_data, current_state)
            
            # Add bot response to history
            current_state["history"].append({
                "role": "assistant",
                "content": response
            })
            
            # Save updated state to Redis
            save_state(user_id, channel_id, thread_ts, current_state)
            
            # Display bot response
            print(f"\n🤖 Bot: {response}")
            
            # Display current state (for demonstration purposes)
            print("\n" + "-"*30)
            print("CURRENT STATE:")
            state_display = {
                "intent": current_state.get("intent"),
                "context": current_state.get("context", {}),
                "history_length": len(current_state.get("history", []))
            }
            print(json.dumps(state_display, indent=2))
            print("-"*30)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            print(f"\n🤖 Bot: Sorry, I encountered an error processing your message.")
    
    # Check final state
    final_state = get_state(user_id, channel_id, thread_ts)
    if final_state:
        print("\nFinal state in Redis:")
        print(json.dumps(final_state, indent=2))
        
        choice = input("\nDo you want to clear this conversation state? [Y/N]: ").upper()
        if choice == 'Y':
            delete_state(user_id, channel_id, thread_ts)
            print("State cleared.")

if __name__ == "__main__":
    simulate_conversation()