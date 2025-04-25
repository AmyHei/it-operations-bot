"""
State management service for conversation context.

This module provides functions to save, retrieve, and delete conversation state
using Redis as a persistent storage backend. The state is stored as JSON and
includes automatic expiration.
"""
import logging
import os
import json
import redis
from typing import Dict, Optional, Union
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# Initialize Redis connection pool
try:
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True  # Auto-decode bytes to strings
    )
    
    # Create Redis client
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    # Test the connection
    redis_client.ping()
    logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    
except redis.RedisError as e:
    logger.error(f"Failed to initialize Redis connection: {str(e)}")
    # Setup a fallback mechanism
    redis_client = None

def _generate_key(user_id: str, channel_id: str) -> str:
    """
    Generate a unique Redis key for storing conversation state.
    
    Args:
        user_id: The user's identifier
        channel_id: The channel or conversation identifier
        
    Returns:
        A unique key string for Redis storage
    """
    return f"state:{user_id}:{channel_id}"

def save_state(user_id: str, channel_id: str, state_data: Dict, ttl_seconds: int = 900) -> bool:
    """
    Save conversation state to Redis with expiration.
    
    Args:
        user_id: The user's identifier
        channel_id: The channel or conversation identifier
        state_data: Dictionary containing the state to save
        ttl_seconds: Time to live in seconds (default: 15 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        logger.warning("Redis client not available, state will not be saved")
        return False
        
    if not user_id or not channel_id:
        logger.error("Invalid user_id or channel_id provided")
        return False
    
    try:
        # Generate key
        key = _generate_key(user_id, channel_id)
        
        # Convert state data to JSON string
        state_json = json.dumps(state_data)
        
        # Store in Redis with expiration
        result = redis_client.set(key, state_json, ex=ttl_seconds)
        
        if result:
            logger.debug(f"State saved for user {user_id} in channel {channel_id}")
            return True
        else:
            logger.warning(f"Failed to save state for user {user_id} in channel {channel_id}")
            return False
            
    except redis.RedisError as e:
        logger.error(f"Redis error while saving state: {str(e)}")
        return False
    except json.JSONEncodeError as e:
        logger.error(f"JSON encoding error while saving state: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving state: {str(e)}")
        return False

def get_state(user_id: str, channel_id: str) -> Optional[Dict]:
    """
    Retrieve conversation state from Redis.
    
    Args:
        user_id: The user's identifier
        channel_id: The channel or conversation identifier
        
    Returns:
        Dictionary containing the state if found, None otherwise
    """
    if not redis_client:
        logger.warning("Redis client not available, cannot retrieve state")
        return None
        
    if not user_id or not channel_id:
        logger.error("Invalid user_id or channel_id provided")
        return None
    
    try:
        # Generate key
        key = _generate_key(user_id, channel_id)
        
        # Retrieve from Redis
        state_json = redis_client.get(key)
        
        # Return None if key doesn't exist
        if not state_json:
            logger.debug(f"No state found for user {user_id} in channel {channel_id}")
            return None
            
        # Parse JSON string back to dictionary
        state_data = json.loads(state_json)
        logger.debug(f"State retrieved for user {user_id} in channel {channel_id}")
        return state_data
        
    except redis.RedisError as e:
        logger.error(f"Redis error while retrieving state: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error while retrieving state: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving state: {str(e)}")
        return None

def delete_state(user_id: str, channel_id: str) -> bool:
    """
    Delete conversation state from Redis.
    
    Args:
        user_id: The user's identifier
        channel_id: The channel or conversation identifier
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        logger.warning("Redis client not available, cannot delete state")
        return False
        
    if not user_id or not channel_id:
        logger.error("Invalid user_id or channel_id provided")
        return False
    
    try:
        # Generate key
        key = _generate_key(user_id, channel_id)
        
        # Delete from Redis
        result = redis_client.delete(key)
        
        # Return True even if key didn't exist
        if result == 0:
            logger.debug(f"No state found to delete for user {user_id} in channel {channel_id}")
        else:
            logger.debug(f"State deleted for user {user_id} in channel {channel_id}")
        return True
        
    except redis.RedisError as e:
        logger.error(f"Redis error while deleting state: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting state: {str(e)}")
        return False

def update_ttl(user_id: str, channel_id: str, ttl_seconds: int = 900) -> bool:
    """
    Update the expiration time of an existing state.
    
    Args:
        user_id: The user's identifier
        channel_id: The channel or conversation identifier
        ttl_seconds: New time to live in seconds (default: 15 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        logger.warning("Redis client not available, cannot update TTL")
        return False
    
    try:
        # Generate key
        key = _generate_key(user_id, channel_id)
        
        # Check if key exists
        if not redis_client.exists(key):
            logger.debug(f"No state found to update TTL for user {user_id} in channel {channel_id}")
            return False
            
        # Update expiration
        result = redis_client.expire(key, ttl_seconds)
        
        if result:
            logger.debug(f"TTL updated for user {user_id} in channel {channel_id}")
            return True
        else:
            logger.warning(f"Failed to update TTL for user {user_id} in channel {channel_id}")
            return False
            
    except redis.RedisError as e:
        logger.error(f"Redis error while updating TTL: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating TTL: {str(e)}")
        return False 