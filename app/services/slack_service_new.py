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
from app.services.software_service import submit_software_request
from app.services.knowledge_service import log_article_feedback

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
            
            # Handle specific actions returned by the dialogue manager
            if response.get("action") == "execute_software_request":
                # Extract necessary details
                software_name = response.get("details", {}).get("software_name", "Unknown software")
                logger.info(f"Executing software request: {software_name} for user {user_id}")
                
                # Call the software service to submit the request
                action_result = submit_software_request(user_id, software_name)
                
                # Update the response based on the action result
                if action_result.get("status") == "success":
                    ticket_number = action_result.get("ticket_number", "Unknown")
                    response["response"] = f"Your request for {software_name} has been submitted successfully. Ticket {ticket_number} has been created to track your request."
                    if action_result.get("simulated"):
                        response["response"] += " (Note: This is a simulated response)"
                else:
                    # Handle error case
                    error_message = action_result.get("message", "Unknown error")
                    response["response"] = f"I'm sorry, there was an issue processing your software request: {error_message}"
                
                # Clear the state as determined by the dialogue manager
                response["next_state"] = None
            
            # Check if response requires Block Kit buttons for password reset
            if response.get("response_type") == "blocks" and response.get("blocks_config", {}).get("type") == "confirm_password_reset":
                # Extract the confirmation text
                confirmation_text = response.get("blocks_config", {}).get("text", "Would you like to proceed with the password reset?")
                
                # Generate Block Kit JSON
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": confirmation_text
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Yes",
                                    "emoji": True
                                },
                                "style": "primary",
                                "value": "proceed",
                                "action_id": "confirm_password_reset_yes"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "No",
                                    "emoji": True
                                },
                                "style": "danger",
                                "value": "cancel",
                                "action_id": "confirm_password_reset_no"
                            }
                        ]
                    }
                ]
                
                # Send response with Block Kit
                slack_app.client.chat_postMessage(
                    channel=channel_id,
                    blocks=blocks,
                    text=response.get("response", "Would you like to proceed with the password reset?"),  # Fallback text
                    thread_ts=reply_thread
                )
            
            # Check if response requires KB article blocks
            elif response.get("response_type") == "blocks" and response.get("blocks_config", {}).get("type") == "kb_results":
                # Extract articles and query
                articles = response.get("blocks_config", {}).get("articles", [])
                query = response.get("blocks_config", {}).get("query", "your search")
                
                # Create blocks for the KB articles
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Here are some articles I found about '{query}'*:"
                        }
                    }
                ]
                
                # Add each article with dividers and feedback buttons
                for article in articles:
                    # Add divider before each article (except the first one to avoid double dividers)
                    if len(blocks) > 1:
                        blocks.append({"type": "divider"})
                    
                    # Add article section with title as link
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*<{article.get('url')}|{article.get('title')}>*\n{article.get('summary', 'No summary available')}"
                        }
                    })
                    
                    # Add feedback buttons for this article
                    blocks.append({
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "✅ This Helped",
                                    "emoji": True
                                },
                                "style": "primary",
                                "value": article.get("id", "unknown"),
                                "action_id": "kb_feedback_helpful"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "❌ Didn't Help",
                                    "emoji": True
                                },
                                "value": article.get("id", "unknown"),
                                "action_id": "kb_feedback_unhelpful"
                            }
                        ]
                    })
                
                # Add a final divider
                blocks.append({"type": "divider"})
                
                # Add a context note
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "If none of these articles address your issue, you can create a support ticket by saying *\"I need help with...\"*"
                        }
                    ]
                })
                
                # Send response with Block Kit
                slack_app.client.chat_postMessage(
                    channel=channel_id,
                    blocks=blocks,
                    text=response.get("response", f"Here are some articles about {query}."),  # Fallback text
                    thread_ts=reply_thread
                )
            
            # Check if response requires urgency selection dropdown
            elif response.get("response_type") == "blocks" and response.get("blocks_config", {}).get("type") == "select_urgency":
                # Extract the text
                instruction_text = response.get("blocks_config", {}).get("text", "Please select the urgency level for your ticket:")
                
                # Generate Block Kit JSON for the dropdown
                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": instruction_text
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "static_select",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Select urgency...",
                                    "emoji": True
                                },
                                "options": [
                                    {
                                        "text": {
                                            "type": "plain_text",
                                            "text": "🔴 High - Critical business impact",
                                            "emoji": True
                                        },
                                        "value": "1"
                                    },
                                    {
                                        "text": {
                                            "type": "plain_text",
                                            "text": "🟠 Medium - Limited business impact",
                                            "emoji": True
                                        },
                                        "value": "2"
                                    },
                                    {
                                        "text": {
                                            "type": "plain_text",
                                            "text": "🟢 Low - Minimal business impact",
                                            "emoji": True
                                        },
                                        "value": "3"
                                    }
                                ],
                                "action_id": "select_ticket_urgency"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "The urgency level helps us prioritize your ticket appropriately."
                            }
                        ]
                    }
                ]
                
                # Send response with Block Kit
                slack_app.client.chat_postMessage(
                    channel=channel_id,
                    blocks=blocks,
                    text=response.get("response", "Please select the urgency level for your ticket."),  # Fallback text
                    thread_ts=reply_thread
                )
            else:
                # Send regular text response
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
    
    # Add action handler for urgency selection dropdown
    @slack_app.action("select_ticket_urgency")
    def handle_urgency_selection(ack, body, client):
        """Handle urgency selection for ticket creation"""
        # Acknowledge the action right away
        ack()
        
        # Extract details from the interaction
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        message_ts = body["container"]["message_ts"]
        
        # Get the selected option value
        selected_option = body["actions"][0]["selected_option"]["value"]
        selected_text = body["actions"][0]["selected_option"]["text"]["text"]
        
        logger.info(f"User {user_id} selected ticket urgency: {selected_option} ({selected_text})")
        
        try:
            # Get the current state
            current_state = get_state(user_id, channel_id) or {}
            
            # Process the selection through the dialogue service
            intent_data = {
                "intent": "create_ticket",
                "text": "",
                "selected_option": selected_option
            }
            
            # Call dialogue service with the selected option
            result = handle_urgency_selection(intent_data, current_state) if "handle_urgency_selection" in globals() else get_next_action(intent_data, current_state)
            
            # Update the original message to show the selection
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"Ticket urgency set to: {selected_text}",
                blocks=[
                    {
                        "type": "section",
