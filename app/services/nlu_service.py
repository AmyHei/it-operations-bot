"""
Natural Language Understanding service.

This module provides intent detection capabilities using Hugging Face's transformers
library for zero-shot text classification. The model classifies user input into
predefined intents and returns the most likely intent along with a confidence score.
It also extracts named entities using a pre-trained NER model.
"""
import logging
import os
import re
from typing import Dict, Any, List, Tuple
import torch
from transformers import pipeline

# Set up logging
logger = logging.getLogger(__name__)

# Define candidate labels for intent classification
INTENT_LABELS = [
    "check ticket status", 
    "reset password", 
    "find knowledge base article", 
    "create ticket", 
    "greeting", 
    "general question",
    "request software"  # New intent for software requests
]

# Map from model labels to internal intent names
INTENT_MAPPING = {
    "check ticket status": "check_ticket_status",
    "reset password": "reset_password",
    "find knowledge base article": "find_kb_article",
    "create ticket": "create_ticket",
    "greeting": "greeting",
    "general question": "general_question",
    "request software": "request_software"  # New mapping for software requests
}

# Confidence threshold for intent classification
CONFIDENCE_THRESHOLD = 0.7

# Load models at module level so they're only loaded once when the service starts
try:
    logger.info("Loading NLU models...")
    # Use CUDA if available for faster inference
    device = 0 if torch.cuda.is_available() else -1
    
    # Load zero-shot classification model
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=device
    )
    
    # Load Named Entity Recognition model
    # The "simple" aggregation strategy helps group word pieces into meaningful entities
    ner_pipeline = pipeline(
        "ner", 
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        aggregation_strategy="simple",
        device=device
    )
    
    logger.info("Models loaded successfully")
except Exception as e:
    logger.error(f"Error loading NLU models: {str(e)}")
    classifier = None
    ner_pipeline = None

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from text using the NER pipeline.
    
    This function processes the text through a pre-trained NER model and
    organizes the results by entity type.
    
    Args:
        text: The user's message text
        
    Returns:
        A dictionary where keys are entity types (e.g., "ORG", "PER") and 
        values are lists of extracted entities of that type.
    """
    if ner_pipeline is None:
        logger.error("NER model not available")
        return {}
    
    try:
        # Run the NER pipeline on the input text
        ner_results = ner_pipeline(text)
        
        # Process and organize results by entity type
        entities_by_type = {}
        for item in ner_results:
            entity_type = item["entity_group"]  # e.g., "ORG", "PER", "LOC", "MISC"
            entity_text = item["word"]
            entity_score = item["score"]
            
            # Only include entities with confidence above threshold
            if entity_score >= 0.8:
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                
                # Avoid duplicates
                if entity_text not in entities_by_type[entity_type]:
                    entities_by_type[entity_type].append(entity_text)
                    logger.debug(f"Extracted entity: {entity_text} ({entity_type}) with score {entity_score:.2f}")
        
        return entities_by_type
        
    except Exception as e:
        logger.error(f"Error during entity extraction: {str(e)}")
        return {}

def understand_intent(text: str) -> Dict[str, Any]:
    """
    理解用户意图并提取相关实体。结合零样本分类和命名实体识别。
    
    Args:
        text: 用户输入的文本
        
    Returns:
        包含意图和实体的字典
    """
    # 如果消息太短，不进行深度分析
    if len(text.strip()) < 3:
        return {"intent": "unknown", "entities": {}, "confidence_score": 0.0}
    
    # 直接处理工单号查询，即使意图不明确
    ticket_pattern = re.compile(r'\b(?:INC|REQ|TASK|RITM)\d{5,}\b', re.IGNORECASE)
    ticket_matches = []
    for match in ticket_pattern.finditer(text):
        ticket_matches.append(match.group(0))  # 获取完整匹配
    
    # 如果文本中有明显的工单号，直接认为是工单查询意图
    if ticket_matches and ("查" in text or "status" in text.lower() or "check" in text.lower() or "ticket" in text.lower()):
        logger.info(f"直接识别为工单查询意图，工单号: {ticket_matches}")
        entities = {"TICKET_NUMBER": ticket_matches}
        return {
            "intent": "check_ticket_status", 
            "entities": entities, 
            "confidence_score": 0.95  # 给予高置信度
        }
    
    # 检查是否是知识库查询
    kb_related = False
    # 英文关键词
    if "knowledge" in text.lower() or "article" in text.lower() or "guide" in text.lower() or "how to" in text.lower():
        kb_related = True
    # 中文关键词
    if "知识" in text or "文章" in text or "指南" in text or "怎么" in text or "如何" in text:
        kb_related = True
    
    # VPN是特殊关键词，直接视为知识库查询
    if "vpn" in text.lower():
        kb_related = True
        
    if kb_related:
        # 提取知识库主题
        kb_terms_pattern = re.compile(r'\b(vpn|servicenow|password|network|security|software|hardware|email|office|access|reset|setup|install|configure|troubleshoot|密码|网络|安全|软件|硬件|邮件|访问|重置|设置|安装|配置|故障)\b', re.IGNORECASE)
        kb_matches = kb_terms_pattern.findall(text)
        
        entities = {}
        if kb_matches:
            entities["KB_TERMS"] = kb_matches
            logger.info(f"检测到知识库查询意图，主题: {kb_matches}")
            
        return {
            "intent": "find_kb_article", 
            "entities": entities, 
            "confidence_score": 0.9
        }
    
    try:
        # Perform zero-shot classification for intent
        intent_result = classifier(text, INTENT_LABELS, multi_label=False)
        
        # Get the top label and its score
        top_label = intent_result["labels"][0]
        top_score = intent_result["scores"][0]
        
        logger.debug(f"Top predicted intent: {top_label} with score: {top_score}")
        
        # Extract entities using NER
        entities = extract_entities(text)
        
        # Special handling for certain intents
        intent = "unknown"
        if top_score >= CONFIDENCE_THRESHOLD:
            # Map the model's label to our internal intent name
            intent = INTENT_MAPPING.get(top_label, "unknown")
        
        # Ticket pattern recognition for ServiceNow ticket numbers
        # This augments the NER model which might not specifically detect ticket numbers
        if ticket_matches:
            # Check if these ticket numbers are already captured in any entity category
            existing_tickets = []
            for entity_list in entities.values():
                existing_tickets.extend([e for e in entity_list if ticket_pattern.search(e)])
            
            # Add non-duplicate tickets to the entities dictionary under TICKET_NUMBER key
            new_tickets = [t for t in ticket_matches if t not in existing_tickets]
            if new_tickets:
                entities["TICKET_NUMBER"] = new_tickets
                logger.debug(f"Found ticket references via pattern matching: {new_tickets}")
            
            # 在ticket_pattern相关代码后添加：
            logger.info(f"原始文本: '{text}'")
            logger.info(f"正则表达式: {ticket_pattern.pattern}")
            logger.info(f"提取的工单号: {ticket_matches}")
            
            # 如果检测到工单号但意图置信度低，强制设为工单查询意图
            if intent == "unknown" and ticket_matches:
                intent = "check_ticket_status"
                logger.info(f"基于工单号强制设置意图为工单查询")
        
        # Knowledge base topic detection
        # This helps identify IT-related topics for knowledge base searches
        if intent == "find_kb_article" or "knowledge" in text.lower() or "article" in text.lower() or "guide" in text.lower() or "how to" in text.lower():
            kb_terms_pattern = re.compile(r'\b(vpn|servicenow|password|network|security|software|hardware|email|office|access|reset|setup|install|configure|troubleshoot)\b(?:\s+\w+)?', re.IGNORECASE)
            kb_matches = kb_terms_pattern.findall(text)
            
            if kb_matches:
                kb_terms = []
                for match in kb_matches:
                    match = match.strip().title()
                    if match and match not in kb_terms:
                        kb_terms.append(match)
                
                if kb_terms:
                    entities["KB_TERMS"] = kb_terms
                    logger.debug(f"Found KB search terms: {kb_terms}")
                    
            # Log knowledge base search terms
            logger.info(f"Knowledge base search text: '{text}'")
            logger.info(f"Extracted KB terms: {kb_matches}")
            
            # Force intent to find_kb_article if knowledge terms are found but intent is low confidence
            if kb_terms and intent == "unknown":
                intent = "find_kb_article"
                logger.info(f"Forcing intent to find_kb_article based on KB terms")
        
        # 中文关键词检测
        if intent == "unknown":
            # 检查中文关键词
            if "查" in text or "票" in text or "工单" in text or "状态" in text:
                intent = "check_ticket_status"
                logger.info(f"基于中文关键词设置意图为工单查询")
            elif "重置" in text or "密码" in text:
                intent = "reset_password"
                logger.info(f"基于中文关键词设置意图为密码重置")
            elif "知识" in text or "文章" in text or "帮助" in text or "怎么" in text:
                intent = "find_kb_article"
                logger.info(f"基于中文关键词设置意图为知识库查询")
            elif "申请" in text or "软件" in text or "安装" in text:
                intent = "request_software"
                logger.info(f"基于中文关键词设置意图为软件申请")
            elif "创建" in text or "提交" in text or "报告" in text or "问题" in text:
                intent = "create_ticket"
                logger.info(f"基于中文关键词设置意图为创建工单")
        
        # Software name detection for software requests
        # This is a simple pattern to catch common software mentions
        if intent == "request_software" or "software" in text.lower() or "application" in text.lower() or "app" in text.lower():
            software_pattern = re.compile(r'\b(microsoft|adobe|office|excel|word|powerpoint|photoshop|chrome|teams|zoom|slack|outlook|windows|mac os|ios|android|linux)\b(?:\s+\w+)?', re.IGNORECASE)
            software_matches = software_pattern.findall(text)
            
            if software_matches:
                # Clean up and standardize software names
                software_names = []
                for match in software_matches:
                    match = match.strip().title()  # Standardize capitalization
                    if match and match not in software_names:
                        software_names.append(match)
                
                if software_names:
                    entities["SOFTWARE_NAME"] = software_names
                    logger.debug(f"Found software references: {software_names}")
        
        # Log the final result
        if intent != "unknown":
            logger.info(f"Detected '{intent}' intent from: '{text}' with confidence: {top_score:.2f}")
        else:
            logger.info(f"Intent below confidence threshold ({top_score:.2f}): '{text}'")
        
        if entities:
            logger.info(f"Extracted entities: {entities}")
            
        return {
            "intent": intent, 
            "entities": entities, 
            "confidence_score": float(top_score)
        }
            
    except Exception as e:
        logger.error(f"Error during intent classification: {str(e)}")
        return {"intent": "unknown", "entities": {}, "confidence_score": None} 