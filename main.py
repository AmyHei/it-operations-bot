"""
Main entry point for the application.
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Run the application with uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=reload
    ) 