"""
Knowledge Base Service for searching and retrieving knowledge articles.

This module provides functionality to search for and retrieve knowledge articles
from IT knowledge repositories.
"""
import logging
import random
from typing import Dict, List, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Simulated knowledge base articles for development
SAMPLE_KB_ARTICLES = [
    {
        "id": "KB00001",
        "title": "VPN Setup Guide for Remote Employees",
        "url": "https://example.com/kb/vpn-setup",
        "summary": "Step-by-step guide for setting up VPN access for remote work",
        "category": "Network"
    },
    {
        "id": "KB00002",
        "title": "Password Reset Procedure",
        "url": "https://example.com/kb/password-reset",
        "summary": "Instructions for resetting your corporate account password",
        "category": "Security"
    },
    {
        "id": "KB00003",
        "title": "Microsoft Office Installation Guide",
        "url": "https://example.com/kb/office-installation",
        "summary": "How to install and activate Microsoft Office on your computer",
        "category": "Software"
    },
    {
        "id": "KB00004",
        "title": "Troubleshooting Network Connectivity Issues",
        "url": "https://example.com/kb/network-troubleshooting",
        "summary": "Common solutions for resolving network connectivity problems",
        "category": "Network"
    },
    {
        "id": "KB00005",
        "title": "Email Configuration on Mobile Devices",
        "url": "https://example.com/kb/email-mobile-setup",
        "summary": "How to set up corporate email on iOS and Android devices",
        "category": "Mobile"
    }
]

def search_knowledge_base(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for articles matching the query.
    
    In a production environment, this would connect to a real knowledge base system.
    For development, it returns simulated results based on the query.
    
    Args:
        query: The search query or topic
        max_results: Maximum number of results to return
        
    Returns:
        A list of article dictionaries with fields:
        - id: Unique identifier for the article
        - title: Article title
        - url: URL to access the full article
        - summary: Brief summary of the article
        - category: Category of the article
    """
    logger.info(f"Searching knowledge base for: {query}")
    
    # In a real implementation, this would search an actual knowledge base
    # For now, we'll simulate results by filtering the sample data
    
    # Convert query to lowercase for case-insensitive matching
    query_lower = query.lower()
    
    # Find articles where the query appears in title, summary, or category
    results = []
    for article in SAMPLE_KB_ARTICLES:
        match_score = 0
        if query_lower in article["title"].lower():
            match_score += 3  # Title matches are more important
        if query_lower in article["summary"].lower():
            match_score += 2  # Summary matches are somewhat important
        if query_lower in article["category"].lower():
            match_score += 1  # Category matches are less important
            
        if match_score > 0:
            # Make a copy of the article and add the match score
            article_with_score = article.copy()
            article_with_score["match_score"] = match_score
            results.append(article_with_score)
    
    # If no results, return some generic articles
    if not results:
        logger.info(f"No direct matches for '{query}', returning generic results")
        # Return a random subset of articles
        results = random.sample(SAMPLE_KB_ARTICLES, min(max_results, len(SAMPLE_KB_ARTICLES)))
        for article in results:
            article_copy = article.copy()
            article_copy["match_score"] = 0
            results.append(article_copy)
    
    # Sort by match score (highest first) and limit to max_results
    results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    results = results[:max_results]
    
    # Remove the match_score field from the results
    for article in results:
        if "match_score" in article:
            del article["match_score"]
    
    logger.info(f"Found {len(results)} articles for query: {query}")
    return results

def log_article_feedback(article_id: str, feedback: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Log user feedback about an article.
    
    Args:
        article_id: The ID of the article
        feedback: The feedback type ('helpful' or 'unhelpful')
        user_id: Optional user ID for tracking
        
    Returns:
        Dict with status indicating success or failure
    """
    logger.info(f"Received {feedback} feedback for article {article_id} from user {user_id or 'anonymous'}")
    
    # In a real implementation, this would store the feedback in a database
    # For now, we'll just log it
    
    return {
        "status": "success",
        "message": f"Feedback logged for article {article_id}",
        "article_id": article_id,
        "feedback": feedback,
        "user_id": user_id
    } 