"""
Slack integration service using Slack Bolt for Python.
"""
import logging
import os
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from app.config.settings import settings
from app.services.nlu_service import understand_intent
from app.services.dialogue_service import get_next_action

# Set up logging
logger = logging.getLogger(__name__)

# In-memory conversation state storage
# In production, this should be replaced with a proper database
conversation_states = {}

# Initialize the Slack app with credentials from settings
def create_slack_app():
    """Create and configure a Slack Bolt app instance."""
    # Try to get tokens directly from environment first, then fall back to settings
    bot_token = os.environ.get("SLACK_BOT_TOKEN", settings.SLACK_BOT_TOKEN)
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", settings.SLACK_SIGNING_SECRET)
    
    logger.info(f"Creating Slack app with token: {bot_token[:5] if bot_token else 'None'}...")
    
    slack_app = App(
        token=bot_token,
        signing_secret=signing_secret,
        token_verification_enabled=False  # Disable token verification for troubleshooting
    )
    
    # Register event handlers
    @slack_app.event("app_mention")
    def handle_app_mention(event, say):
        """处理 app_mention 事件 - 当有人在频道中提及 Bot 时触发"""
        try:
            # 提取用户消息
            message_text = event.get("text", "").replace(f"<@{event.get('authorizations', [{}])[0].get('user_id', '')}>", "").strip()
            user_id = event.get("user", "unknown_user")
            
            logger.info(f"[DEBUG] 原始消息: {event.get('text')}")
            logger.info(f"[DEBUG] 处理后消息: {message_text}")
            logger.info(f"[DEBUG] 用户ID: {user_id}")
            logger.info(f"[DEBUG] 当前所有对话状态: {conversation_states}")
            
            # 获取当前用户的对话状态
            current_state = conversation_states.get(user_id)
            logger.info(f"[DEBUG] 当前用户状态: {current_state}")
            
            # 使用 NLU 服务处理消息
            intent_data = understand_intent(message_text)
            logger.info(f"[DEBUG] NLU结果: {intent_data}")
            
            # 从对话服务获取下一个动作和响应
            dialogue_result = get_next_action(intent_data, current_state)
            logger.info(f"[DEBUG] 对话服务结果: {dialogue_result}")
            
            # 更新对话状态
            if dialogue_result.get("next_state"):
                conversation_states[user_id] = dialogue_result["next_state"]
                logger.info(f"[DEBUG] 更新后状态: {conversation_states[user_id]}")
            else:
                conversation_states.pop(user_id, None)
                logger.info("[DEBUG] 状态已清除")
            
            # 发送对话服务的响应
            say(dialogue_result["response"])
            
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            say("抱歉，处理您的请求时出现了错误。")
    
    @slack_app.event("message")
    def handle_message(event, say):
        # 仅处理直接消息，且不是 Bot 自己发送的消息
        if (event.get("user") and not event.get("bot_id") 
                and event.get("channel_type") == "im"):
            message_text = event.get("text", "")
            user_id = event.get("user", "unknown_user")
            
            try:
                # 获取当前用户的对话状态
                current_state = conversation_states.get(user_id)
                logger.info(f"[DEBUG] 当前用户状态: {current_state}")
                
                # 如果正在等待工单号
                if current_state and current_state.get("waiting_for") == "ticket_number":
                    # 直接处理工单号查询
                    dialogue_result = get_next_action({"intent": "check_ticket", "ticket_number": message_text}, current_state)
                else:
                    # 正常的 NLU 处理流程
                    intent_data = understand_intent(message_text)
                    intent_data["text"] = message_text
                    dialogue_result = get_next_action(intent_data, current_state)
                
                logger.info(f"[DEBUG] 对话服务结果: {dialogue_result}")
                
                # 更新对话状态
                if dialogue_result.get("next_state"):
                    conversation_states[user_id] = dialogue_result["next_state"]
                    logger.info(f"[DEBUG] 更新状态为: {dialogue_result['next_state']}")
                else:
                    conversation_states.pop(user_id, None)
                    logger.info("[DEBUG] 状态已清除")
                
                # 发送对话服务的响应
                say(dialogue_result["response"])
                
            except Exception as e:
                logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
                say("抱歉，处理您的请求时出现了错误。")
    
    # Optional: add other event handlers as needed
    @slack_app.error
    def handle_errors(error):
        """Global error handler for Slack app."""
        logger.error(f"Error in Slack app: {error}")
    
    return slack_app

# Create an instance of the Slack app
slack_app = create_slack_app()

# Create a request handler for FastAPI integration
slack_handler = SlackRequestHandler(slack_app) 