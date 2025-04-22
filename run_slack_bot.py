import os
import sys
from dotenv import load_dotenv
import logging


logging.basicConfig(level=logging.DEBUG)

# Load environment variables first
print("Loading environment variables...")
load_dotenv()  # Load variables from .env file

# Manually set environment variables if they're not set already
if "SLACK_BOT_TOKEN" not in os.environ:
    print("⚠️ SLACK_BOT_TOKEN not found in environment, trying to read from .env file directly")
    with open(".env", "r") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                if key.strip() == "SLACK_BOT_TOKEN":
                    os.environ["SLACK_BOT_TOKEN"] = value.strip()
                    print(f"Manually set SLACK_BOT_TOKEN from .env file")
                if key.strip() == "SLACK_SIGNING_SECRET":
                    os.environ["SLACK_SIGNING_SECRET"] = value.strip()
                    print(f"Manually set SLACK_SIGNING_SECRET from .env file")
                if key.strip() == "SLACK_APP_TOKEN":
                    os.environ["SLACK_APP_TOKEN"] = value.strip()
                    print(f"Manually set SLACK_APP_TOKEN from .env file")

print("Environment variables loaded.")
print(f"SLACK_BOT_TOKEN exists: {'SLACK_BOT_TOKEN' in os.environ}")
print(f"SLACK_SIGNING_SECRET exists: {'SLACK_SIGNING_SECRET' in os.environ}")
print(f"SLACK_APP_TOKEN exists: {'SLACK_APP_TOKEN' in os.environ}")

# 重要错误信息：
print("\n===== IMPORTANT NOTICE =====")
print("如果脚本启动失败，最可能的原因是 Slack API 令牌无效。")
print("请前往 https://api.slack.com/apps 重新获取 Slack Bot Token 和 App Token。")
print("然后更新 .env 文件中的 SLACK_BOT_TOKEN 和 SLACK_APP_TOKEN。")
print("============================\n")

# Now import the slack app
print("Before importing slack_app")
from app.services.slack_service import slack_app
print("After importing slack_app")

# Make sure tokens are loaded correctly before starting
# Add checks here if needed, or rely on Bolt's internal checks

print("正在尝试连接 Slack...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    # If you set it up to run via an HTTP server instead (like FastAPI integration or gunicorn):
    # The FastAPI server below would handle incoming Slack events via a specific endpoint.
    # In that case, you wouldn't run this script directly. Revisit Prompt 2/5 logic.
