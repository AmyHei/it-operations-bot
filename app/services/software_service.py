"""
Software request service.

This module provides functionality for handling software request workflows.
It simulates or creates ServiceNow tickets for software requests.
"""
import logging
import random
from typing import Dict, Optional

# Import ServiceNow ticket creation function
from app.services.servicenow_service import create_servicenow_ticket

# Set up logging
logger = logging.getLogger(__name__)

def submit_software_request(user_id: str, software_name: str, 
                          urgency: str = "3", 
                          description: Optional[str] = None) -> Dict:
    """
    Submit a request for software installation or access.
    
    This function either simulates the software request process
    or creates an actual ServiceNow ticket for the request.
    
    Args:
        user_id: The Slack user ID or employee ID of the requester
        software_name: The name of the software being requested
        urgency: The urgency level (1=High, 2=Medium, 3=Low)
        description: Additional details about the software request
        
    Returns:
        Dictionary containing the status of the operation and details
    """
    # Log the request
    logger.info(f"Simulating software request for {software_name} by user {user_id}")
    
    # Prepare software request details
    if not description:
        description = f"User {user_id} has requested access to {software_name}. Please review and process this request."
    
    short_description = f"Software Request: {software_name}"
    
    # Create a ServiceNow ticket for the request
    try:
        # Call the existing ServiceNow ticket creation function
        ticket_result = create_servicenow_ticket(
            short_description=short_description,
            description=description,
            urgency=urgency,
            caller_id=user_id,
            # You might want to set a specific assignment group for software requests
            assignment_group=None  # Default assignment
        )
        
        # Check if the ticket was created successfully
        if "error" in ticket_result:
            logger.error(f"Failed to create ServiceNow ticket: {ticket_result.get('details')}")
            return {
                "status": "error",
                "message": f"Failed to submit request: {ticket_result.get('details', 'Unknown error')}"
            }
        
        # Return success with ticket details
        ticket_number = ticket_result.get("ticket_number", "Unknown")
        return {
            "status": "success",
            "message": f"Software request submitted. Ticket {ticket_number} created.",
            "ticket_number": ticket_number,
            "software_name": software_name
        }
        
    except Exception as e:
        logger.error(f"Error submitting software request: {str(e)}")
        
        # Simulate success for development/testing (remove in production)
        simulated_ticket = f"RITM{random.randint(100000, 999999)}"
        logger.info(f"Simulating successful request with ticket {simulated_ticket}")
        
        return {
            "status": "success",
            "message": "Software request submitted (simulated).",
            "ticket_number": simulated_ticket,
            "software_name": software_name,
            "simulated": True
        }

# Additional helper functions could be added below as needed 