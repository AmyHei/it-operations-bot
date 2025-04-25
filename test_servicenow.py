import os
from dotenv import load_dotenv
import requests
import json
import base64
import sys

# Load environment variables
load_dotenv()

# ServiceNow connection details
instance = os.getenv('SERVICENOW_INSTANCE')
user = os.getenv('SERVICENOW_USER')
pwd = os.getenv('SERVICENOW_PASSWORD')

# Check if credentials are properly set
if not instance or not user or not pwd:
    print("❌ Error: Missing ServiceNow credentials in .env file")
    print(f"  Instance: {'✓' if instance else '✗'}")
    print(f"  User: {'✓' if user else '✗'}")
    print(f"  Password: {'✓' if pwd else '✗'}")
    sys.exit(1)

# ServiceNow API endpoint
base_url = f'https://{instance}.service-now.com'

print("Testing ServiceNow connection...")
print(f"Instance: {instance}")
print(f"User: {user}")
print(f"Password length: {len(pwd)}")

def test_basic_auth():
    try:
        # Test table API access using basic auth
        print("\n1. Testing table API with Basic Authentication...")
        table_url = f"{base_url}/api/now/table/incident?sysparm_limit=1"
        print(f"Request URL: {table_url}")
        
        # Create Basic Auth header manually to validate it's correct
        auth_str = f"{user}:{pwd}"
        auth_bytes = auth_str.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_auth = base64_bytes.decode('ascii')
        
        print(f"Authorization: Basic {base64_auth[:10]}...")
        
        response = requests.get(
            table_url,
            auth=(user, pwd),
            headers={
                'Accept': 'application/json'
            }
        )
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Successfully connected to ServiceNow with Basic Auth!")
            data = response.json()
            print("\nSample response data:", json.dumps(data, indent=2)[:500], "...")
            return True
        else:
            print("❌ Failed to connect with Basic Auth")
            print("Error response:", response.text)
            
            # Additional troubleshooting info
            if response.status_code == 401:
                print("\nTroubleshooting tips for 401 Unauthorized:")
                print("1. Verify your username and password are correct")
                print("2. Ensure the user has sufficient permissions")
                print("3. Check if the instance name is correct")
                print("4. Verify the user isn't locked out")
                print("5. Try resetting the password in ServiceNow")
            return False
            
    except Exception as e:
        print("❌ Error:", str(e))
        return False

def test_oauth_token():
    # For future implementation if needed
    print("\n2. OAuth token authentication is not implemented in this test")
    print("   This would normally use client_id and client_secret to get an OAuth token")
    return None

if __name__ == "__main__":
    basic_auth_success = test_basic_auth()
    
    print("\n=== Test Summary ===")
    print(f"Basic Auth: {'✅ Success' if basic_auth_success else '❌ Failed'}")
    
    if not basic_auth_success:
        print("\nPossible solutions:")
        print("1. Double-check the SERVICENOW_USER and SERVICENOW_PASSWORD in your .env file")
        print("2. Verify your ServiceNow instance name is correct (SERVICENOW_INSTANCE)")
        print("3. Ensure the user has API access permissions")
        print("4. Try logging into ServiceNow web interface with the same credentials")
        print("5. If using a developer instance, make sure it's not hibernating")
        sys.exit(1) 