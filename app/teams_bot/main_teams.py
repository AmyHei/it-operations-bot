import os
import logging
from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from app.teams_bot.bot import MyTeamsBot

# Load credentials from environment variables
MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create adapter and bot
adapter_settings = BotFrameworkAdapterSettings(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)
bot = MyTeamsBot()

async def messages(request: web.Request):
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def aux_func(turn_context: TurnContext):
        await bot.on_turn(turn_context)

    response = await adapter.process_activity(activity, auth_header, aux_func)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)

# 添加 OPTIONS 路由处理
async def options_handler(request):
    return web.Response(status=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    })

app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_options("/api/messages", options_handler)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3978))
    web.run_app(app, port=port)
