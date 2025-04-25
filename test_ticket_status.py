#!/usr/bin/env python
"""
Test script for the ServiceNow ticket status function.
"""
import logging
import sys
import json
from app.services.servicenow_service import ServiceNowService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Test the ServiceNow ticket status retrieval."""
    print("ServiceNow Ticket Status Test")
    print("==============================")
    print("Enter 'exit' to quit")
    print("")
    
    # Create ServiceNow service instance
    snow_service = ServiceNowService()
    
    while True:
        ticket_number = input("\nEnter a ticket number to check (e.g., INC0010001): ")
        if ticket_number.lower() in ['exit', 'quit', 'q']:
            break
        
        # Skip empty input
        if not ticket_number:
            continue
            
        # Get ticket status
        result = snow_service.get_ticket_status(ticket_number)
        
        # Display the result
        if "error" in result:
            print(f"\n❌ Error: {result.get('error')}")
            print(f"   Details: {result.get('details', 'No additional details')}")
        else:
            print(f"\n✅ Ticket Found: {result.get('ticket_number')}")
            print(f"   Description: {result.get('short_description')}")
            print(f"   Status: {result.get('state')} (code: {result.get('state_code')})")
            print(f"   Priority: {result.get('priority')} (code: {result.get('priority_code')})")
            print(f"   Opened: {result.get('opened_at')}")
            print(f"   Last Updated: {result.get('updated_at')}")
            
        # Print full JSON for debugging
        print("\nFull Response:")
        print(json.dumps(result, indent=2))
            
if __name__ == "__main__":
    main() 