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
from app.services.state_service import get_state, save_state, delete_state

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track active conversation threads
active_threads = {}
# Track processed message IDs to prevent duplicates
processed_messages = set()

def create_slack_app():
    """Create and configure a Slack Bolt app instance."""
    bot_token = os.environ.get("SLACK_BOT_TOKEN", settings.SLACK_BOT_TOKEN)
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", settings.SLACK_SIGNING_SECRET)
    
    logger.info(f"Creating Slack app with token: {bot_token[:10]}...")
    
    slack_app = App(
        token=bot_token,
        signing_secret=signing_secret,
        token_verification_enabled=False
    )

    def process_and_respond(message_text, user_id, channel_id, thread_ts=None, message_ts=None):
        """统一的消息处理和响应函数"""
        # 生成消息唯一标识
        message_id = f"{channel_id}:{message_ts}:{message_text}"
        logger.info(f"Processing message ID: {message_id}")
        
        # 检查消息是否已处理
        if message_id in processed_messages:
            logger.info(f"Skipping already processed message: {message_id}")
            return
            
        try:
            # 获取当前对话状态 - 使用Redis
            current_state = get_state(user_id, channel_id) or {}
            logger.info(f"Current state for user {user_id} in channel {channel_id}: {current_state}")
            
            # 检查是否在等待确认
            if current_state.get("waiting_for") == "confirmation":
                if message_text.lower() in ["yes", "y", "是", "确认"]:
                    # 用户确认，继续密码重置流程
                    response = {
                        "response": "好的，我将为您重置密码。请提供您的员工ID或用户名。",
                        "next_state": {"intent": "password_reset", "waiting_for": "employee_id"}
                    }
                else:
                    # 用户取消
                    response = {
                        "response": "已取消密码重置流程。如果您之后需要帮助，随时可以询问我。",
                        "next_state": None
                    }
            # 检查是否在等待员工ID
            elif current_state.get("waiting_for") == "employee_id":
                # 处理员工ID输入
                response = {
                    "response": "已收到您的员工ID。我们将在24小时内处理您的密码重置请求，并通过邮件通知您。\n如果您有紧急需求，请联系IT服务台: 400-888-8888",
                    "next_state": None
                }
            else:
                # 处理常规消息
                intent_data = understand_intent(message_text)
                
                # 如果是密码重置请求
                if "password" in message_text.lower() and "reset" in message_text.lower():
                    response = {
                        "response": "我可以帮助您重置密码。这个操作会将您的密码重置为一个临时密码。您确定要继续吗？",
                        "next_state": {"intent": "password_reset", "waiting_for": "confirmation"}
                    }
                else:
                    # 其他常规消息处理
                    response = process_message(message_text, user_id, current_state)
            
            # 确定回复的线程
            reply_thread = thread_ts or message_ts
            logger.info(f"Sending response in thread: {reply_thread}")
            
            # 发送响应
            slack_app.client.chat_postMessage(
                channel=channel_id,
                text=response["response"],
                thread_ts=reply_thread
            )
            
            # 更新对话状态 - 使用Redis
            if response.get("next_state") is not None:
                # 保存对话状态，设置15分钟过期时间
                save_state(user_id, channel_id, response["next_state"], ttl_seconds=900)
                logger.info(f"Saved state to Redis for user {user_id} in channel {channel_id}: {response['next_state']}")
            elif response.get("next_state") is None:
                # 如果next_state是None，清除对话状态
                delete_state(user_id, channel_id)
                logger.info(f"Deleted state from Redis for user {user_id} in channel {channel_id}")
            
            # 记录已处理的消息
            processed_messages.add(message_id)
            
            # 更新活跃线程
            if reply_thread:
                active_threads[reply_thread] = {
                    "channel": channel_id,
                    "user": user_id,
                    "last_message": message_text
                }
                logger.info(f"Updated active thread {reply_thread}: {active_threads[reply_thread]}")
                
        except Exception as e:
            logger.error(f"Error in process_and_respond: {str(e)}", exc_info=True)
            slack_app.client.chat_postMessage(
                channel=channel_id,
                text="抱歉，处理您的请求时出现了错误。",
                thread_ts=thread_ts or message_ts
            )
    
    @slack_app.event("app_mention")
    def handle_app_mention(event, say):
        """处理 app_mention 事件"""
        logger.debug(f"Received app_mention event: {event}")
        try:
            # 提取消息信息
            bot_id = event.get("authorizations", [{}])[0].get("user_id", "")
            message_text = event.get("text", "").replace(f"<@{bot_id}>", "").strip()
            user_id = event.get("user")
            channel_id = event.get("channel")
            thread_ts = event.get("thread_ts")
            message_ts = event.get("ts")
            
            logger.info(f"Processing app_mention - User: {user_id}, Channel: {channel_id}, Message: {message_text}")
            logger.info(f"Thread TS: {thread_ts}, Message TS: {message_ts}")
            
            process_and_respond(message_text, user_id, channel_id, thread_ts, message_ts)
            
        except Exception as e:
            logger.error(f"Error in handle_app_mention: {str(e)}", exc_info=True)
            say("抱歉，处理您的请求时出现了错误。")
    
    @slack_app.event("message")
    def handle_message(event, say):
        """处理普通消息事件"""
        logger.debug(f"Received message event: {event}")
        
        if event.get("user") and not event.get("bot_id"):
            channel_type = event.get("channel_type")
            thread_ts = event.get("thread_ts")
            message_ts = event.get("ts")
            user_id = event.get("user")
            channel_id = event.get("channel")
            message_text = event.get("text", "").strip()
            
            logger.info(f"Processing message - Type: {channel_type}, User: {user_id}, Channel: {channel_id}")
            logger.info(f"Thread TS: {thread_ts}, Message TS: {message_ts}, Text: {message_text}")
            
            # Check if this is a thread we should respond to
            should_respond = (
                channel_type == "im" or
                (thread_ts and thread_ts in active_threads) or
                (message_ts and message_ts in active_threads)
            )
            
            logger.info(f"Should respond: {should_respond}")
            logger.info(f"Active threads: {active_threads}")
            
            if should_respond:
                process_and_respond(message_text, user_id, channel_id, thread_ts, message_ts)
    
    return slack_app

def process_message(message_text: str, user_id: str, current_state: dict = None) -> dict:
    """处理消息并返回响应"""
    try:
        # 如果正在等待工单号且消息包含工单号格式
        if current_state and current_state.get("waiting_for") == "ticket_number" and "INC" in message_text:
            dialogue_result = get_next_action({"intent": "check_ticket", "ticket_number": message_text}, current_state)
        else:
            # 正常的 NLU 处理流程
            intent_data = understand_intent(message_text)
            intent_data["text"] = message_text
            dialogue_result = get_next_action(intent_data, current_state)
        
        return dialogue_result
    except Exception as e:
        logger.error(f"Error in process_message: {str(e)}", exc_info=True)
        return {
            "response": "抱歉，处理您的请求时出现了错误。",
            "next_state": None
        }

# Create an instance of the Slack app
slack_app = create_slack_app()

# Create a request handler for FastAPI integration
slack_handler = SlackRequestHandler(slack_app) 