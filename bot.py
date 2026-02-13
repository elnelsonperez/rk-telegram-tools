import logging
from datetime import datetime

import httpx
from claude_client import ClaudeClient, ClaudeResponse
from conversations import ConversationStore, DOC_TYPES
from transcriber import Transcriber

logger = logging.getLogger(__name__)

# Track chats where we already sent a voice reminder (reset on non-voice messages)
_voice_reminded: set[int] = set()

_DOC_TYPE_KEYWORDS = {
    "COT": ["cotizaci", "cotización"],
    "PRES": ["presupuest"],
    "REC": ["recibo"],
}


def _infer_doc_type(text: str) -> str | None:
    text_lower = text.lower()
    for doc_type, keywords in _DOC_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return doc_type
    return None


def is_bot_mentioned(message, bot_user_id: int, bot_username: str = "") -> bool:
    if not message.entities:
        return False
    text = message.text or ""
    bot_username_lower = bot_username.lower()
    for e in message.entities:
        # text_mention: user without username, has e.user
        if e.type == "text_mention" and e.user and e.user.id == bot_user_id:
            return True
        # mention: @username style, no e.user — compare text
        if e.type == "mention" and bot_username_lower:
            mention_text = text[e.offset:e.offset + e.length].lower()
            if mention_text == f"@{bot_username_lower}":
                return True
    return False


def is_reply_to_bot(message, bot_user_id: int) -> bool:
    if not message.reply_to_message:
        return False
    return message.reply_to_message.from_user.id == bot_user_id


def extract_user_text(message, bot_user_id: int, bot_username: str = "") -> str:
    text = message.text or ""
    bot_username_lower = bot_username.lower()
    if message.entities:
        for e in message.entities:
            is_bot = False
            if e.type == "text_mention" and e.user and e.user.id == bot_user_id:
                is_bot = True
            elif e.type == "mention" and bot_username_lower:
                mention_text = text[e.offset:e.offset + e.length].lower()
                is_bot = mention_text == f"@{bot_username_lower}"
            if is_bot:
                text = text[:e.offset] + text[e.offset + e.length:]
    return text.strip()


def find_root_message_id(message) -> int:
    current = message
    while current.reply_to_message is not None:
        current = current.reply_to_message
    return current.message_id


async def handle_message(
    message,
    bot_user_id: int,
    bot_username: str,
    claude: ClaudeClient,
    store: ConversationStore,
    transcriber: Transcriber,
    telegram_token: str,
):
    is_voice = message.voice is not None
    chat_id = message.chat.id

    if not is_voice:
        _voice_reminded.discard(chat_id)

    mentioned = is_bot_mentioned(message, bot_user_id, bot_username) if not is_voice else False
    replied = is_reply_to_bot(message, bot_user_id)

    # Voice messages sent as replies to the bot are always handled
    if not is_voice and not mentioned and not replied:
        return

    # For voice messages not directed at the bot, send a one-time reminder
    if is_voice and not replied:
        if chat_id not in _voice_reminded:
            _voice_reminded.add(chat_id)
            await _send_text(telegram_token, chat_id, message.message_id,
                             "Para que pueda escuchar tu nota de voz, responde directamente a uno de mis mensajes.")
        return

    # Check if the replied-to message has content we should include
    reply_has_voice = (not is_voice and message.reply_to_message
                       and hasattr(message.reply_to_message, 'voice')
                       and message.reply_to_message.voice is not None)
    reply_has_text = (not is_voice and mentioned and message.reply_to_message
                      and not replied
                      and getattr(message.reply_to_message, 'text', None))

    if is_voice:
        user_text = None  # will be transcribed below
    else:
        user_text = extract_user_text(message, bot_user_id, bot_username)
        if not user_text and not reply_has_voice and not reply_has_text:
            logger.debug("Message matched but extracted text is empty, ignoring")
            return

    if mentioned and not message.reply_to_message:
        root_id = message.message_id  # new conversation
        logger.info("New conversation: chat=%s msg_id=%s root=%s",
                     chat_id, message.message_id, root_id)
    else:
        # Look up root from registry (Telegram only nests reply_to_message 1 level deep)
        replied_to_id = message.reply_to_message.message_id
        root_id = store.find_root(chat_id, replied_to_id)
        if root_id is None:
            root_id = replied_to_id
            logger.warning("Root not in registry: chat=%s replied_to=%s, falling back to root=%s",
                           chat_id, replied_to_id, root_id)
        logger.info("Continue conversation: chat=%s msg_id=%s root=%s replied_to=%s",
                     chat_id, message.message_id, root_id, replied_to_id)

    # Register user's message so future replies to it can find this conversation
    store.register_message(chat_id, message.message_id, root_id)
    logger.info("Registered msg %s -> root %s (registry size: %d)",
                message.message_id, root_id, store.registry_size())

    # Transcribe voice (either the message itself or the replied-to message)
    voice_file_id = None
    if is_voice:
        voice_file_id = message.voice.file_id
    elif reply_has_voice:
        voice_file_id = message.reply_to_message.voice.file_id

    if voice_file_id:
        status_msg_id = await _send_status(telegram_token, chat_id, message.message_id,
                                            "Transcribiendo audio...")
        try:
            transcript = transcriber.transcribe_voice(telegram_token, voice_file_id)
        except Exception:
            logger.exception("Transcription failed for chat=%s", chat_id)
            await _delete_message(telegram_token, chat_id, status_msg_id)
            await _send_text(telegram_token, chat_id, message.message_id,
                             "No pude transcribir el audio. Intenta de nuevo.")
            return
        if not transcript:
            await _delete_message(telegram_token, chat_id, status_msg_id)
            await _send_text(telegram_token, chat_id, message.message_id,
                             "No pude entender el audio. Intenta de nuevo o escribe tu mensaje.")
            return
        logger.info("Transcribed voice: %r", transcript[:120])
        await _delete_message(telegram_token, chat_id, status_msg_id)

        if is_voice:
            user_text = transcript
        else:
            # Text reply to a voice note — combine both
            user_text = f"[Nota de voz transcrita]: {transcript}\n\n{user_text or ''}".strip()
    elif reply_has_text:
        # Mention in reply to a non-bot message — include the original text as context
        original_text = message.reply_to_message.text
        user_text = f"[Mensaje original]: {original_text}\n\n{user_text or ''}".strip()

    conv = store.get_or_create(chat_id=chat_id, root_message_id=root_id)
    conv.messages.append({"role": "user", "content": user_text})
    logger.info("Sending to Claude: %d messages, container=%s", len(conv.messages), conv.container_id)

    # Pre-assign document number based on user's request
    year = datetime.now().year
    doc_type = _infer_doc_type(user_text)
    if doc_type:
        doc_num = store.next_document_number(doc_type, year)
        logger.info("Pre-assigned document number: %s", doc_num)
        doc_number_context = f"\n\n## Numeración de documentos\nUsa exactamente este número para el documento: **{doc_num}**"
    else:
        # No doc type detected — provide last numbers as context for follow-ups
        last_numbers = store.get_last_document_numbers(year)
        if last_numbers:
            lines = [f"\n\n## Numeración de documentos\nÚltimos números generados en {year}:"]
            for dt, num in sorted(last_numbers.items()):
                label = DOC_TYPES.get(dt, dt)
                lines.append(f"- {label}: {num}")
            lines.append("Si necesitas generar un documento, usa el siguiente número consecutivo.")
            doc_number_context = "\n".join(lines)
        else:
            doc_number_context = f"\n\n## Numeración de documentos\nNo hay documentos generados en {year}. Formato: TIPO-{year}-001 (COT para cotización, PRES para presupuesto, REC para recibo)."

    try:
        result = claude.send_message(conv.messages, container_id=conv.container_id,
                                     system_extra=doc_number_context)
    except Exception:
        logger.exception("Claude API error for chat=%s root=%s", chat_id, root_id)
        await _send_text(telegram_token, chat_id, message.message_id,
                         "Error generando el documento. Intenta de nuevo.")
        conv.messages.pop()  # remove failed user message
        store.save(chat_id, root_id, conv)
        return

    conv.container_id = result.container_id
    conv.messages.append({"role": "assistant", "content": result.raw_content})
    store.save(chat_id, root_id, conv)
    logger.info("Claude response: text_len=%d files=%d container=%s text=%r",
                len(result.text), len(result.file_ids), result.container_id, result.text[:120])

    if result.text:
        bot_msg_id = await _send_text(telegram_token, chat_id, message.message_id, result.text)
        logger.info("Text sent: bot_msg_id=%s -> root=%s", bot_msg_id, root_id)
        if bot_msg_id:
            store.register_message(chat_id, bot_msg_id, root_id)

    async with httpx.AsyncClient() as http:
        for file_id in result.file_ids:
            try:
                filename, content = claude.download_file(file_id)
                logger.info("Sending document: %s (%d bytes) to chat=%s", filename, len(content), chat_id)
                bot_msg_id = await _send_document(http, telegram_token, chat_id, message.message_id,
                                                   filename, content)
                logger.info("Document sent: bot_msg_id=%s -> root=%s", bot_msg_id, root_id)
                if bot_msg_id:
                    store.register_message(chat_id, bot_msg_id, root_id)
            except Exception:
                logger.exception("Failed to download/send file %s", file_id)


async def _send_status(token: str, chat_id: int, reply_to: int, text: str) -> int | None:
    """Send a status message and return its message_id for later deletion."""
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_to_message_id": reply_to,
            },
        )
        try:
            return resp.json()["result"]["message_id"]
        except (KeyError, TypeError):
            logger.warning("Could not get status message_id from response")
            return None


async def _delete_message(token: str, chat_id: int, message_id: int | None):
    """Delete a message. Silently ignores failures."""
    if message_id is None:
        return
    async with httpx.AsyncClient() as http:
        await http.post(
            f"https://api.telegram.org/bot{token}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        )


async def _send_text(token: str, chat_id: int, reply_to: int, text: str) -> int | None:
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_to_message_id": reply_to,
                "parse_mode": "Markdown",
            },
        )
        data = resp.json()
        try:
            return data["result"]["message_id"]
        except (KeyError, TypeError):
            logger.warning("sendMessage failed or missing message_id: %s", data)
            return None


async def _send_document(
    http: httpx.AsyncClient, token: str, chat_id: int, reply_to: int,
    filename: str, content: bytes,
) -> int | None:
    resp = await http.post(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data={"chat_id": chat_id, "reply_to_message_id": reply_to},
        files={"document": (filename, content)},
    )
    data = resp.json()
    try:
        return data["result"]["message_id"]
    except (KeyError, TypeError):
        logger.warning("sendDocument failed or missing message_id: %s", data)
        return None
