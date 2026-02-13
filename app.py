import asyncio
import logging
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from telegram import Update

from config import load_config
from claude_client import ClaudeClient
from conversations import ConversationStore
from bot import handle_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = load_config()
claude = ClaudeClient(api_key=config.anthropic_api_key, skill_id=config.rk_skill_id)
store = ConversationStore()

# We need the bot's user ID to detect mentions/replies.
# This is fetched once on startup via getMe.
_bot_user_id: int | None = None


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def webhook(request: Request) -> JSONResponse:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != config.webhook_secret:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    body = await request.json()
    update = Update.de_json(body, bot=None)

    if update and update.message and update.message.text:
        global _bot_user_id
        if _bot_user_id is None:
            import httpx
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    f"https://api.telegram.org/bot{config.telegram_bot_token}/getMe"
                )
                _bot_user_id = resp.json()["result"]["id"]
                logger.info("Bot user ID fetched: %s", _bot_user_id)

        user = update.message.from_user
        user_name = f"{user.first_name} ({user.id})" if user else "unknown"
        logger.info("Webhook received: chat=%s user=%s text=%r",
                     update.message.chat.id, user_name, update.message.text[:80])

        asyncio.create_task(
            handle_message(
                message=update.message,
                bot_user_id=_bot_user_id,
                claude=claude,
                store=store,
                telegram_token=config.telegram_bot_token,
            )
        )
    else:
        logger.debug("Webhook received non-text update, ignoring")

    # Always respond 200 quickly so Telegram doesn't retry
    return JSONResponse({"ok": True})


async def on_startup():
    store.cleanup()
    logger.info("RK ArtSide bot started")


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/webhook", webhook, methods=["POST"]),
    ],
    on_startup=[on_startup],
)
