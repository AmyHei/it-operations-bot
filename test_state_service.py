#!/usr/bin/env python
"""
Test script for the Redis-based state management service.
"""
import logging
import sys
import time
import json
from app.services.state_service import save_state, get_state, delete_state, update_ttl

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Test the Redis-based state management service."""
    print("Redis State Management Test")
    print("==========================")
    print("This script demonstrates saving, retrieving, and deleting state in Redis.")
    print("")
    
    # Test user and channel IDs
    user_id = "U12345678"
    channel_id = "C87654321"
    print(f"Using test User ID: {user_id}, Channel ID: {channel_id}")
    
    # Test state data
    test_state = {
        "context": "User asked about ticket status",
        "last_message_timestamp": time.time(),
        "current_intent": "check_ticket_status",
        "entities": {
            "ticket_number": "INC0010001"
        },
        "pending_action": "fetch_ticket_details",
        "conversation_turns": 3
    }
    
    # Step 1: Save state
    print("\nStep 1: Saving state to Redis...")
    success = save_state(user_id, channel_id, test_state, ttl_seconds=120)
    if success:
        print("✅ State saved successfully!")
    else:
        print("❌ Failed to save state!")
        return
    
    # Step 2: Retrieve state
    print("\nStep 2: Retrieving state from Redis...")
    retrieved_state = get_state(user_id, channel_id)
    if retrieved_state:
        print("✅ State retrieved successfully!")
        print("\nRetrieved state:")
        print(json.dumps(retrieved_state, indent=2))
        
        # Verify data integrity
        if retrieved_state == test_state:
            print("✅ Data integrity verified!")
        else:
            print("❌ Data integrity check failed!")
    else:
        print("❌ Failed to retrieve state!")
        return
    
    # Step 3: Update TTL
    print("\nStep 3: Updating TTL for state...")
    ttl_success = update_ttl(user_id, channel_id, ttl_seconds=180)
    if ttl_success:
        print("✅ TTL updated successfully!")
    else:
        print("❌ Failed to update TTL!")
    
    # Step 4: Delete state
    print("\nStep 4: Deleting state from Redis...")
    delete_success = delete_state(user_id, channel_id)
    if delete_success:
        print("✅ State deleted successfully!")
    else:
        print("❌ Failed to delete state!")
    
    # Step 5: Verify deletion
    print("\nStep 5: Verifying state was deleted...")
    deleted_state = get_state(user_id, channel_id)
    if deleted_state is None:
        print("✅ State verified as deleted!")
    else:
        print("❌ State still exists in Redis!")
        
    print("\nTest completed.")
    
if __name__ == "__main__":
    main() 