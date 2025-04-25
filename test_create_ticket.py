#!/usr/bin/env python
"""
Test script for creating a ServiceNow ticket.
"""
import logging
import sys
import json
from app.services.servicenow_service import create_servicenow_ticket

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Test the ServiceNow ticket creation function."""
    print("ServiceNow Ticket Creation Test")
    print("===============================")
    print("This script will create a real ticket in ServiceNow.")
    print("Press Ctrl+C to exit at any time.\n")
    
    try:
        # Get ticket information from user
        short_description = input("Enter ticket summary/title: ")
        if not short_description:
            print("❌ Error: Summary cannot be empty. Exiting.")
            return
        
        description = input("Enter detailed description (optional): ")
        
        # Urgency selection
        print("\nSelect urgency level:")
        print("1 - High")
        print("2 - Medium")
        print("3 - Low (default)")
        urgency = input("Enter your choice (1-3) or press Enter for default: ")
        
        # Set default urgency
        if not urgency or urgency not in ["1", "2", "3"]:
            urgency = "3"
            
        print("\nCreating ServiceNow ticket. Please wait...")
        
        # Call the function to create the ticket
        result = create_servicenow_ticket(
            short_description=short_description,
            description=description,
            urgency=urgency
        )
        
        # Display the result
        if "error" in result:
            print(f"\n❌ Error: {result.get('error')}")
            print(f"   Details: {result.get('details', 'No additional details')}")
        else:
            print("\n✅ Success! Ticket created:")
            print(f"   Ticket Number: {result.get('ticket_number')}")
            print(f"   Title: {result.get('short_description')}")
            print(f"   Created At: {result.get('created_at')}")
            
        # Print full JSON for debugging
        print("\nFull Response:")
        print(json.dumps(result, indent=2))
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main() 