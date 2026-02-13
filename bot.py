import logging
import httpx
from claude_client import ClaudeClient, ClaudeResponse
from conversations import ConversationStore

logger = logging.getLogger(__name__)


def is_bot_mentioned(message, bot_user_id: int) -> bool:
    if not message.entities:
        return False
    return any(
        e.type == "mention" and e.user and e.user.id == bot_user_id
        for e in message.entities
    )


def is_reply_to_bot(message, bot_user_id: int) -> bool:
    if not message.reply_to_message:
        return False
    return message.reply_to_message.from_user.id == bot_user_id


def extract_user_text(message, bot_user_id: int) -> str:
    text = message.text or ""
    if message.entities:
        for e in message.entities:
            if e.type == "mention" and e.user and e.user.id == bot_user_id:
                mention_text = text[e.offset:e.offset + e.length]
                text = text.replace(mention_text, "", 1)
    return text.strip()


def find_root_message_id(message) -> int:
    current = message
    while current.reply_to_message is not None:
        current = current.reply_to_message
    return current.message_id


async def handle_message(
    message,
    bot_user_id: int,
    claude: ClaudeClient,
    store: ConversationStore,
    telegram_token: str,
):
    mentioned = is_bot_mentioned(message, bot_user_id)
    replied = is_reply_to_bot(message, bot_user_id)

    if not mentioned and not replied:
        return

    user_text = extract_user_text(message, bot_user_id)
    if not user_text:
        logger.debug("Message matched but extracted text is empty, ignoring")
        return

    chat_id = message.chat.id

    if mentioned and not message.reply_to_message:
        root_id = message.message_id  # new conversation
        logger.info("New conversation started: chat=%s root=%s trigger=mention", chat_id, root_id)
    else:
        root_id = find_root_message_id(message)
        logger.info("Continuing conversation: chat=%s root=%s trigger=%s",
                     chat_id, root_id, "mention+reply" if mentioned else "reply")

    conv = store.get_or_create(chat_id=chat_id, root_message_id=root_id)
    conv.messages.append({"role": "user", "content": user_text})
    logger.info("Sending to Claude: %d messages, container=%s", len(conv.messages), conv.container_id)

    try:
        result = claude.send_message(conv.messages, container_id=conv.container_id)
    except Exception:
        logger.exception("Claude API error for chat=%s root=%s", chat_id, root_id)
        await _send_text(telegram_token, chat_id, message.message_id,
                         "Error generando el documento. Intenta de nuevo.")
        conv.messages.pop()  # remove failed user message
        return

    conv.container_id = result.container_id
    conv.messages.append({"role": "assistant", "content": result.raw_content})
    logger.info("Claude response: text_len=%d files=%d container=%s",
                len(result.text), len(result.file_ids), result.container_id)

    # Send files first, then text
    async with httpx.AsyncClient() as http:
        for file_id in result.file_ids:
            try:
                filename, content = claude.download_file(file_id)
                logger.info("Sending document: %s (%d bytes) to chat=%s", filename, len(content), chat_id)
                await _send_document(http, telegram_token, chat_id, message.message_id,
                                     filename, content)
            except Exception:
                logger.exception("Failed to download/send file %s", file_id)

    if result.text:
        await _send_text(telegram_token, chat_id, message.message_id, result.text)


async def _send_text(token: str, chat_id: int, reply_to: int, text: str):
    async with httpx.AsyncClient() as http:
        await http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_to_message_id": reply_to,
            },
        )


async def _send_document(
    http: httpx.AsyncClient, token: str, chat_id: int, reply_to: int,
    filename: str, content: bytes,
):
    await http.post(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data={"chat_id": chat_id, "reply_to_message_id": reply_to},
        files={"document": (filename, content)},
    )
