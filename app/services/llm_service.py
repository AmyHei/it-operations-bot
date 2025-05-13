"""
LLM service for generating responses based on knowledge base content.
"""
import logging
import os
from typing import Dict, Optional
from openai import OpenAI  # You could use different LLM providers

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_kb_response(user_question: str, article_content: str, max_tokens: int = 500) -> Dict:
    """
    Generate a response to a user's question based on KB article content.
    
    Args:
        user_question: The user's original question
        article_content: The content from the KB article(s)
        max_tokens: Maximum tokens for the response
        
    Returns:
        Dict containing the generated response and status
    """
    try:
        # Construct the prompt
        prompt = f"""You are an IT support assistant. Answer the following user question based ONLY on the provided context 
        from the knowledge base articles. If the answer cannot be fully derived from the context, acknowledge what you know
        from the context and indicate what additional information might be needed.
        
        Question: {user_question}
        
        Context:
        ---BEGIN CONTEXT---
        {article_content}
        ---END CONTEXT---
        
        Answer in the same language as the user's question (English or Chinese).
        """
        
        # Call the LLM API
        response = client.chat.completions.create(
            model="gpt-4",  # or your chosen model
            messages=[
                {"role": "system", "content": "You are an IT support assistant helping users with their questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        # Extract and return the generated answer
        answer = response.choices[0].message.content
        return {
            "status": "success",
            "response": answer
        }
        
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def clean_article_content(content: str) -> str:
    """
    Clean and prepare KB article content for LLM processing.
    
    Args:
        content: Raw article content (may contain HTML)
        
    Returns:
        Cleaned text content
    """
    import re
    from bs4 import BeautifulSoup
    
    try:
        # Remove HTML tags if present
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Truncate if too long (adjust limit based on your LLM's context window)
        max_chars = 6000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
            
        return content
        
    except Exception as e:
        logger.error(f"Error cleaning article content: {str(e)}")
        return content  # Return original content if cleaning fails 