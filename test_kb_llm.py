"""
Test script for knowledge base search functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.knowledge_service import search_knowledge_base
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_kb_search():
    # Test cases with different queries
    test_cases = [
        {
            "query": "VPN access",
            "language": "English",
            "expected_keywords": ["VPN", "remote", "access"]
        },
        {
            "query": "VPN连接",
            "language": "Chinese",
            "expected_keywords": ["VPN", "连接"]
        },
        {
            "query": "password reset",
            "language": "English",
            "expected_keywords": ["password", "reset"]
        }
    ]
    
    for test_case in test_cases:
        try:
            print(f"\nTesting {test_case['language']} query: {test_case['query']}")
            
            # Search knowledge base
            results = search_knowledge_base(test_case['query'])
            
            if not results:
                print("❌ No articles found")
                continue
                
            print(f"✅ Found {len(results)} articles")
            
            # Print article details
            for article in results:
                print("\nArticle details:")
                print(f"Title: {article['title']}")
                print(f"Summary: {article['summary']}")
                print(f"URL: {article['url']}")
                
                # Check if expected keywords are in title or summary
                content = (article['title'] + ' ' + article['summary']).lower()
                found_keywords = [k for k in test_case['expected_keywords'] 
                                if k.lower() in content]
                
                if found_keywords:
                    print(f"✅ Found relevant keywords: {', '.join(found_keywords)}")
                else:
                    print("⚠️ No relevant keywords found in article")
                    
        except Exception as e:
            logger.error(f"Error processing test case {test_case['query']}: {str(e)}")
            continue

if __name__ == "__main__":
    print("Starting knowledge base search tests...")
    test_kb_search()
    print("\nTests completed!")