"""
ServiceNow integration service for ticket management.
"""
import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import requests
import json
from urllib.parse import quote

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ServiceNow configuration - environment variables
SERVICENOW_INSTANCE = os.getenv('SERVICENOW_INSTANCE')
SERVICENOW_USERNAME = os.getenv('SERVICENOW_USER')  # Using existing env var name
SERVICENOW_PASSWORD = os.getenv('SERVICENOW_PASSWORD')

# State mapping for human-readable status
INCIDENT_STATE_MAP = {
    '1': 'New',
    '2': 'In Progress',
    '3': 'On Hold',
    '4': 'Resolved',
    '5': 'Closed',
    '6': 'Canceled',
    '7': 'Closed'
}

# Priority mapping
PRIORITY_MAP = {
    '1': 'Critical',
    '2': 'High',
    '3': 'Moderate',
    '4': 'Low',
    '5': 'Planning'
}

# Standalone function to create a ServiceNow ticket
def create_servicenow_ticket(short_description: str, urgency: str = "3", caller_id: str = None, 
                             description: str = None, assignment_group: str = None) -> Dict:
    """
    Create a new incident ticket in ServiceNow.
    
    Args:
        short_description: Brief summary of the incident
        urgency: Urgency level (1=High, 2=Medium, 3=Low)
        caller_id: ServiceNow sys_id of the user reporting the incident
        description: Detailed description of the incident
        assignment_group: ServiceNow sys_id of the group to assign the incident to
        
    Returns:
        Dictionary containing status of the operation and ticket details if successful
    """
    logger.info(f"Creating new ServiceNow ticket: {short_description}")
    
    # Validate configuration
    if not all([SERVICENOW_INSTANCE, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
        logger.error("ServiceNow credentials not configured")
        return {"error": "Configuration error", "details": "ServiceNow credentials not properly configured"}
    
    # Build the API URL
    url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"
    
    # Set headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Create payload
    payload = {
        "short_description": short_description,
        "urgency": urgency
    }
    
    # Add optional fields if provided
    if description:
        payload["description"] = description
    if caller_id:
        payload["caller_id"] = caller_id
    if assignment_group:
        payload["assignment_group"] = assignment_group
    
    try:
        # Make the API request
        response = requests.post(
            url,
            auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
            headers=headers,
            json=payload,
            timeout=15  # Slightly longer timeout for creation
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Parse response JSON
        data = response.json()
        
        # Extract ticket info
        if 'result' in data:
            new_ticket = data['result']
            new_ticket_number = new_ticket.get('number', 'Unknown')
            sys_id = new_ticket.get('sys_id', '')
            
            logger.info(f"Successfully created ticket {new_ticket_number}")
            
            # Return success response
            return {
                "status": "success",
                "ticket_number": new_ticket_number,
                "sys_id": sys_id,
                "short_description": new_ticket.get('short_description'),
                "created_at": new_ticket.get('sys_created_on')
            }
        else:
            logger.error("Unexpected response format from ServiceNow API")
            return {
                "error": "Invalid response",
                "details": "Response did not contain expected 'result' field"
            }
            
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout connecting to ServiceNow API: {str(e)}")
        return {
            "error": "Connection timeout",
            "details": "The request to ServiceNow API timed out"
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to ServiceNow API: {str(e)}")
        return {
            "error": "Connection failed",
            "details": "Failed to connect to ServiceNow API"
        }
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "unknown"
        logger.error(f"HTTP error from ServiceNow API: {status_code} - {str(e)}")
        return {
            "error": "API error",
            "details": f"ServiceNow API returned error: {str(e)}",
            "status_code": status_code
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ServiceNow API response: {str(e)}")
        return {
            "error": "Invalid response",
            "details": "ServiceNow API returned an invalid JSON response"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error creating ticket: {str(e)}")
        return {
            "error": "Unknown error",
            "details": str(e)
        }

class ServiceNowService:
    def __init__(self):
        self.instance = SERVICENOW_INSTANCE
        self.user = SERVICENOW_USERNAME
        self.pwd = SERVICENOW_PASSWORD
        self.base_url = f'https://{self.instance}.service-now.com/api/now'
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to ServiceNow API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=(self.user, self.pwd),
                headers=headers,
                json=data,
                timeout=10  # Add timeout parameter
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to ServiceNow: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def get_incident(self, incident_number: str) -> Dict:
        """Get incident details by number"""
        query = f"number={incident_number}"
        return self._make_request('GET', f'table/incident?sysparm_query={query}')
    
    def get_ticket_status(self, ticket_number: str) -> Dict:
        """
        Get the status of a ServiceNow ticket/incident.
        
        This function fetches the details of a ticket from ServiceNow,
        including its status, priority, description, and other key fields.
        
        Args:
            ticket_number: The ServiceNow incident number (e.g., 'INC0010001')
            
        Returns:
            A dictionary containing the ticket details or error information
        """
        logger.info(f"Getting status for ticket: {ticket_number}")
        
        # Validate inputs
        if not ticket_number:
            logger.error("Empty ticket number provided")
            return {"error": "Invalid input", "details": "Ticket number cannot be empty"}
        
        if not all([SERVICENOW_INSTANCE, SERVICENOW_USERNAME, SERVICENOW_PASSWORD]):
            logger.error("ServiceNow credentials not configured")
            return {"error": "Configuration error", "details": "ServiceNow credentials not properly configured"}
        
        # Construct API URL with query parameters and field selection
        fields = "number,sys_id,short_description,description,state,urgency,priority,caller_id,assignment_group,opened_at,sys_updated_on"
        url = f"{self.base_url}/table/incident"
        params = {
            "sysparm_query": f"number={ticket_number}",
            "sysparm_fields": fields,
            "sysparm_limit": "1"
        }
        
        try:
            # Make the API request
            response = requests.get(
                url,
                auth=(self.user, self.pwd),
                headers={"Accept": "application/json"},
                params=params,
                timeout=10  # 10 second timeout
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response JSON
            data = response.json()
            
            # Check if ticket was found
            if not data.get('result') or len(data['result']) == 0:
                logger.warning(f"Ticket not found: {ticket_number}")
                return {
                    "error": "Ticket not found", 
                    "ticket_number": ticket_number
                }
            
            # Extract ticket data
            ticket = data['result'][0]
            
            # Map state code to human-readable label
            state_code = ticket.get('state')
            state_label = INCIDENT_STATE_MAP.get(state_code, f"Unknown ({state_code})")
            
            # Map priority code to human-readable label
            priority_code = ticket.get('priority')
            priority_label = PRIORITY_MAP.get(priority_code, f"Unknown ({priority_code})")
            
            # Build response
            return {
                "status": "success",
                "ticket_number": ticket.get('number'),
                "sys_id": ticket.get('sys_id'),
                "short_description": ticket.get('short_description'),
                "description": ticket.get('description'),
                "state_code": state_code,
                "state": state_label,
                "priority_code": priority_code,
                "priority": priority_label,
                "opened_at": ticket.get('opened_at'),
                "updated_at": ticket.get('sys_updated_on'),
                "caller_id": ticket.get('caller_id', {}).get('value') if isinstance(ticket.get('caller_id'), dict) else None,
                "assignment_group": ticket.get('assignment_group', {}).get('value') if isinstance(ticket.get('assignment_group'), dict) else None
            }
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to ServiceNow API: {str(e)}")
            return {
                "error": "Connection timeout",
                "details": "The request to ServiceNow API timed out",
                "ticket_number": ticket_number
            }
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to ServiceNow API: {str(e)}")
            return {
                "error": "Connection failed",
                "details": "Failed to connect to ServiceNow API",
                "ticket_number": ticket_number
            }
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            logger.error(f"HTTP error from ServiceNow API: {status_code} - {str(e)}")
            return {
                "error": "API error",
                "details": f"ServiceNow API returned error: {str(e)}",
                "status_code": status_code,
                "ticket_number": ticket_number
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ServiceNow API response: {str(e)}")
            return {
                "error": "Invalid response",
                "details": "ServiceNow API returned an invalid JSON response",
                "ticket_number": ticket_number
            }
            
        except Exception as e:
            logger.error(f"Unexpected error getting ticket status: {str(e)}")
            return {
                "error": "Unknown error",
                "details": str(e),
                "ticket_number": ticket_number
            }

    def create_incident(self, short_description: str, description: str, 
                       urgency: str = '2', impact: str = '2') -> Dict:
        """Create a new incident"""
        data = {
            'short_description': short_description,
            'description': description,
            'urgency': urgency,
            'impact': impact,
            'caller_id': self.user
        }
        return self._make_request('POST', 'table/incident', data)

    def update_incident(self, sys_id: str, updates: Dict) -> Dict:
        """Update an existing incident"""
        return self._make_request('PUT', f'table/incident/{sys_id}', updates)

    def get_incidents(self, limit: int = 10, query: str = '') -> List[Dict]:
        """Get multiple incidents"""
        endpoint = f'table/incident?sysparm_limit={limit}'
        if query:
            endpoint += f'&sysparm_query={query}'
        return self._make_request('GET', endpoint)

# Test the service if run directly
if __name__ == "__main__":
    print("Testing ServiceNow Service...")
    snow = ServiceNowService()
    
    try:
        # Test getting a specific ticket status
        test_ticket = "INC0010001"  # Use an existing ticket number
        print(f"\nGetting status for ticket {test_ticket}...")
        ticket_status = snow.get_ticket_status(test_ticket)
        print(json.dumps(ticket_status, indent=2))
        
        # Test getting recent incidents
        print("\nFetching recent incidents...")
        incidents = snow.get_incidents(limit=2)
        print(json.dumps(incidents, indent=2))
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")