"""
Knowledge Base Service for retrieving and processing knowledge articles from ServiceNow and local files.
"""
import os
import glob
import re
import logging
import requests
from typing import List, Dict
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
import pysnow
import argparse

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the sentence transformer model globally
# You can change the model name as needed
MODEL_NAME = 'all-MiniLM-L6-v2'
kb_embedding_model = SentenceTransformer(MODEL_NAME)

# 添加命令行参数解析
parser = argparse.ArgumentParser(description='测试知识库RAG系统')
parser.add_argument('--provider', type=str, choices=['openai', 'siliconflow'], 
                    default='openai', help='选择LLM提供商: openai或siliconflow')
parser.add_argument('--force-repopulate', action='store_true', 
                    help='强制重新填充知识库')
args = parser.parse_args()

def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[str]:
    """
    Split a long text into smaller, overlapping chunks suitable for embedding.
    
    Args:
        text: The text to be chunked
        chunk_size: Approximate size of each chunk (in words)
        chunk_overlap: Number of words of overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Simple sentence splitting with regex
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # If the text is shorter than chunk_size, return it as is
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    current_chunk_words = []
    current_size = 0
    
    for sentence in sentences:
        sentence_words = sentence.split()
        sentence_word_count = len(sentence_words)
        
        # If adding this sentence exceeds the chunk size and we already have content,
        # save the current chunk and start a new one with overlap
        if current_size + sentence_word_count > chunk_size and current_size > 0:
            # Save current chunk
            chunks.append(' '.join(current_chunk_words))
            
            # Calculate overlap
            if chunk_overlap > 0:
                # Keep the last chunk_overlap words (or less if the chunk is smaller)
                overlap_size = min(chunk_overlap, current_size)
                current_chunk_words = current_chunk_words[-overlap_size:]
                current_size = overlap_size
            else:
                current_chunk_words = []
                current_size = 0
        
        # Add current sentence to the chunk
        current_chunk_words.extend(sentence_words)
        current_size += sentence_word_count
    
    # Add the last chunk if it's not empty
    if current_chunk_words:
        chunks.append(' '.join(current_chunk_words))
    
    return chunks


def clean_html(html_text):
    # 移除HTML标签
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    # 移除多余空格
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text


def fetch_servicenow_kb_articles() -> List[Dict]:
    """
    从ServiceNow获取知识库文章
    """
    # 从环境变量获取ServiceNow凭据
    instance = os.getenv('SERVICENOW_INSTANCE')
    username = os.getenv('SERVICENOW_USERNAME')
    password = os.getenv('SERVICENOW_PASSWORD')
    
    if not all([instance, username, password]):
        logger.error("ServiceNow凭据缺失")
        return []
    
    try:
        # 使用pysnow连接ServiceNow
        client = pysnow.Client(instance=instance, user=username, password=password)
        kb_resource = client.resource(api_path='/table/kb_knowledge')
        
        # 查询知识库文章，根据需要调整查询条件
        response = kb_resource.get(query={'workflow_state': 'published', 'limit': 10})
        
        articles = []
        for record in response.all():
            articles.append({
                "id": record['number'],
                "title": record['short_description'],
                "text": clean_html(record['text'] if 'text' in record else record.get('description', '')),
                "source": "ServiceNow"
            })
        
        logger.info(f"从ServiceNow检索到{len(articles)}篇知识库文章")
        return articles
        
    except Exception as e:
        logger.error(f"从ServiceNow获取知识库文章时出错: {e}")
        return []


def fetch_local_kb_articles(directory_path: str) -> List[Dict]:
    """
    Read local text or markdown files from the specified directory and return as knowledge articles.
    Args:
        directory_path: Path to the directory containing .txt or .md files.
    Returns:
        List of dictionaries with keys: 'id', 'title', 'text', 'source'
    """
    articles = []
    # Search for .txt and .md files
    file_patterns = [os.path.join(directory_path, '*.txt'), os.path.join(directory_path, '*.md')]
    files = []
    for pattern in file_patterns:
        files.extend(glob.glob(pattern))
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            filename = os.path.basename(file_path)
            title = filename  # Optionally, extract a title from content
            articles.append({
                "id": filename,
                "title": title,
                "text": content,
                "source": "Local"
            })
        except Exception as e:
            # Log or handle file read errors as needed
            logger.error(f"Error reading {file_path}: {e}")
    return articles


class KnowledgeService:
    def __init__(self, local_kb_directory: str, llm_provider="openai"):
        """
        Initialize the Knowledge Service.
        
        Args:
            local_kb_directory: Path to directory containing local knowledge base files
            llm_provider: LLM provider to use, options: "openai" or "siliconflow"
        """
        # Store local KB directory
        self.local_kb_directory = local_kb_directory
        
        # Set LLM provider
        self.llm_provider = llm_provider
        
        # Reference to module-level chunk_text function
        self.chunk_text = chunk_text
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client (persistent local storage)
        self.client = chromadb.PersistentClient(path="./chroma_db_store")
        
        # Get or create knowledge base collection
        self.collection = self.client.get_or_create_collection(
            name="it_knowledge_base",
            embedding_function=None  # We'll provide embeddings manually
        )
        
        # Populate knowledge base
        self.populate_knowledge_base()
    
    def populate_knowledge_base(self, force_repopulate=False):
        """
        Fetch articles from ServiceNow and local files, chunk them,
        generate embeddings, and add to the ChromaDB collection.
        
        Args:
            force_repopulate: If True, repopulate the collection even if it already has documents
        """
        # Get count of existing documents for checking if we need to repopulate
        try:
            existing_count = self.collection.count()
            logger.info(f"Found {existing_count} existing documents in the collection")
        except Exception as e:
            logger.error(f"Error checking collection count: {e}")
            existing_count = 0
        
        # Skip processing if collection already has data and force_repopulate is False
        if existing_count > 0 and not force_repopulate:
            logger.info("Knowledge base already populated, skipping repopulation")
            return
        
        # Clear existing documents if force_repopulate is True and collection has documents
        if existing_count > 0 and force_repopulate:
            logger.info("Force repopulating knowledge base - clearing existing documents")
            try:
                # Get all document IDs
                all_ids = [item['id'] for item in self.collection.get()['metadatas']]
                # Delete all documents
                if all_ids:
                    self.collection.delete(ids=all_ids)
                    logger.info(f"Cleared {len(all_ids)} existing documents")
            except Exception as e:
                logger.error(f"Error clearing existing documents: {e}")
        
        # Fetch articles from different sources
        servicenow_articles = fetch_servicenow_kb_articles()
        local_articles = fetch_local_kb_articles(self.local_kb_directory)
        
        # Combine articles
        all_articles = servicenow_articles + local_articles
        logger.info(f"Processing {len(all_articles)} articles for knowledge base")
        
        # Prepare lists for batch addition to ChromaDB
        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []
        
        # Process each article
        for article in all_articles:
            article_id = article['id']
            article_title = article['title']
            article_source = article['source']
            
            # Split article text into chunks
            chunks = self.chunk_text(article['text'])
            
            # Process each chunk
            for chunk_index, chunk_text in enumerate(chunks):
                # Create unique ID for this chunk
                chunk_id = f"{article_id}_chunk_{chunk_index}"
                
                # Add chunk text to documents list
                documents_to_add.append(chunk_text)
                
                # Create and add metadata for this chunk
                metadata = {
                    'original_article_id': article_id,
                    'title': article_title,
                    'source': article_source,
                    'chunk_index': chunk_index
                }
                metadatas_to_add.append(metadata)
                
                # Add chunk ID to IDs list
                ids_to_add.append(chunk_id)
        
        # If we have documents to add, generate embeddings and add to collection
        if documents_to_add:
            logger.info(f"Generating embeddings for {len(documents_to_add)} text chunks")
            
            # Generate embeddings for all chunks
            # We convert to Python lists as ChromaDB expects lists of lists for embeddings
            chunk_embeddings = self.model.encode(documents_to_add).tolist()
            
            # Add documents, embeddings, metadata, and IDs to collection
            self.collection.add(
                embeddings=chunk_embeddings,
                documents=documents_to_add,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            
            logger.info(f"Added {len(documents_to_add)} chunks from {len(all_articles)} articles to the knowledge base")
        else:
            logger.warning("No documents to add to knowledge base")
    
    def search_kb(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search the knowledge base for articles semantically similar to the query.
        
        Args:
            query: User query string
            top_k: Number of results to return
        
        Returns:
            List of dictionaries containing the text, metadata, and distance for each result
        """
        # Log the search query
        logger.info(f"Searching knowledge base for: {query}")
        
        # Generate embedding for the query
        query_embedding = self.model.encode([query]).tolist()
        
        # Query the ChromaDB collection
        results = self.collection.query(
            query_embeddings=query_embedding, 
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Process results
        processed_results = []
        
        # ChromaDB returns results in nested lists, so we need to process them
        num_results = len(results["documents"][0]) if results["documents"] else 0
        
        for i in range(num_results):
            result = {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            }
            processed_results.append(result)
        
        logger.info(f"Found {len(processed_results)} results for query: {query}")
        return processed_results
        
    def generate_answer_with_llm(self, query: str, context_chunks_data: List[Dict]) -> str:
        """
        Generate an answer to the user query using the selected LLM with retrieved context chunks.
        With strong emphasis on citing sources in the response.
        
        Args:
            query: The user's original query
            context_chunks_data: The list of dictionaries from search_kb containing text, metadata, and distance
            
        Returns:
            Generated answer from the LLM with source citations
        """
        # Extract just the text of the context chunks
        context_texts = [chunk['text'] for chunk in context_chunks_data]
        
        # Construct the enhanced prompt with citation requirements
        system_prompt = "You are an AI assistant for IT support. Your task is to answer the user's question based *exclusively* on the provided context documents. "
        system_prompt += "When you use information from a specific document to answer the question, you **MUST** cite the source of that document at the end of the sentence or paragraph that uses it, like this: (Source: [Source Type] - [Document ID/Title]). "
        system_prompt += "If the answer cannot be found in the provided documents, respond with 'I couldn't find an answer to your question in the provided documents.' Do not use any external knowledge."
        
        # Format each context chunk with clear numbering and source information
        user_prompt = "Provided Context Documents:\n"
        
        # Add each context chunk with its source information and numbering
        for i, chunk in enumerate(context_chunks_data):
            source_type = chunk['metadata']['source']
            doc_id = chunk['metadata']['original_article_id']
            title = chunk['metadata'].get('title', doc_id)
            
            user_prompt += f"---\nDocument {i+1} (Source: {source_type} - {doc_id}):\n{context_texts[i]}\n---\n\n"
        
        # Add the user query
        user_prompt += f"User's Question: {query}\n\n"
        user_prompt += "Answer (remember to cite sources):"
        
        # Choose LLM provider based on configuration
        if self.llm_provider == "siliconflow":
            return self._generate_with_siliconflow(system_prompt, user_prompt, query)
        else:
            return self._generate_with_openai(system_prompt, user_prompt, query)
    
    def _generate_with_openai(self, system_prompt: str, user_prompt: str, query: str) -> str:
        """
        Generate answer using OpenAI API.
        """
        # Get the OpenAI API key from environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found in environment variables")
            return "I'm sorry, I cannot generate an answer at this time due to a configuration issue. Please contact IT support."
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct the API payload for OpenAI with enhanced prompting
        payload = {
            "model": "gpt-3.5-turbo",  # 可以使用其他OpenAI模型如"gpt-4"
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,  # 降低温度以获得更精确的答案
            "max_tokens": 1000
        }
        
        # Make the API request
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",  # OpenAI API端点
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Check for successful response
            response.raise_for_status()
            
            # Parse the response and extract the generated text
            response_data = response.json()
            generated_text = response_data["choices"][0]["message"]["content"]
            
            logger.info(f"Successfully generated answer with OpenAI for query: {query}")
            return generated_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling OpenAI API: {e}")
            if response and hasattr(response, 'text'):
                logger.error(f"Response content: {response.text[:200]}")
            return "I'm sorry, I encountered an issue while generating your answer. Please try again later or contact IT support."
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing OpenAI API response: {e}")
            return "I'm sorry, I encountered an issue while processing the answer. Please try again later or contact IT support."
    
    def _generate_with_siliconflow(self, system_prompt: str, user_prompt: str, query: str) -> str:
        """
        Generate answer using Silicon Flow API.
        """
        # Get the Silicon Flow API key from environment variables
        api_key = os.getenv("SILICON_FLOW_API_KEY")
        if not api_key:
            logger.error("Silicon Flow API key not found in environment variables")
            return "I'm sorry, I cannot generate an answer at this time due to a configuration issue. Please contact IT support."
        
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用完整提示构建消息
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Construct the API payload for Silicon Flow
        payload = {
            "model": "chatglm4",  # 硅基流动的模型
            "messages": [
                {"role": "user", "content": combined_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        # Make the API request
        try:
            response = requests.post(
                "https://api.siliconflow.cn/v1/chat/completions",  # 硅基流动API端点
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Check for successful response
            response.raise_for_status()
            
            # Parse the response and extract the generated text
            response_data = response.json()
            generated_text = response_data["choices"][0]["message"]["content"]
            
            logger.info(f"Successfully generated answer with Silicon Flow for query: {query}")
            return generated_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Silicon Flow API: {e}")
            if response and hasattr(response, 'text'):
                logger.error(f"Response content: {response.text[:200]}")
            return "I'm sorry, I encountered an issue while generating your answer. Please try again later or contact IT support."
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing Silicon Flow API response: {e}")
            return "I'm sorry, I encountered an issue while processing the answer. Please try again later or contact IT support."
    
    def get_answer_from_kb(self, query: str) -> str:
        """
        Main public method to retrieve an answer from the knowledge base for a given query.
        
        Args:
            query: The user's query string
            
        Returns:
            LLM-generated answer based on relevant knowledge chunks
        """
        # Search the knowledge base for relevant chunks
        relevant_chunks_data = self.search_kb(query)
        
        # If no relevant chunks found, return a default message
        if not relevant_chunks_data:
            logger.warning(f"No relevant chunks found for query: {query}")
            return "I couldn't find any relevant information in the knowledge base to answer your question."
        
        # Generate an answer using the LLM with the retrieved context
        answer = self.generate_answer_with_llm(query, relevant_chunks_data)
        
        return answer

# 初始化知识服务时设置提供商
print(f"使用{args.provider}作为LLM提供商")
ks = KnowledgeService(local_kb_directory="./local_kb_docs/", llm_provider=args.provider)

# 如果需要强制重新填充
if args.force_repopulate:
    print("强制重新填充知识库...")
    ks.populate_knowledge_base(force_repopulate=True)