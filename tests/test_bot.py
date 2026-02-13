import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import (
    is_bot_mentioned, is_reply_to_bot, extract_user_text,
    find_root_message_id, handle_message, _send_status, _delete_message,
)
from claude_client import ClaudeResponse
from conversations import ConversationStore


def _make_message(text="", entities=None, reply_to=None, message_id=1):
    msg = MagicMock()
    msg.text = text
    msg.message_id = message_id
    msg.entities = entities or []
    msg.reply_to_message = reply_to
    return msg


def _make_entity(entity_type, offset=0, length=0, user=None):
    entity = MagicMock()
    entity.type = entity_type
    entity.offset = offset
    entity.length = length
    entity.user = user
    return entity


# --- is_bot_mentioned ---

def test_is_bot_mentioned_by_username():
    """@username mention: entity type=mention, no user field."""
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg = _make_message(text="@rkartside_bot cotización", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123, bot_username="rkartside_bot") is True


def test_is_bot_mentioned_by_username_case_insensitive():
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg = _make_message(text="@RkArtSide_Bot cotización", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123, bot_username="rkartside_bot") is True


def test_is_bot_mentioned_by_text_mention():
    """text_mention: user without username, has e.user."""
    entity = _make_entity("text_mention", offset=0, length=8, user=MagicMock(id=123))
    msg = _make_message(text="rk-tools cotización", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123, bot_username="rkartside_bot") is True


def test_is_bot_mentioned_false_different_username():
    entity = _make_entity("mention", offset=0, length=8, user=None)
    msg = _make_message(text="@someone hello", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123, bot_username="rkartside_bot") is False


def test_is_bot_mentioned_false_no_entities():
    msg = _make_message(text="hello")
    assert is_bot_mentioned(msg, bot_user_id=123, bot_username="rkartside_bot") is False


# --- is_reply_to_bot ---

def test_is_reply_to_bot_true():
    reply = MagicMock()
    reply.from_user = MagicMock(id=123)
    msg = _make_message(reply_to=reply)
    assert is_reply_to_bot(msg, bot_user_id=123) is True


def test_is_reply_to_bot_false():
    reply = MagicMock()
    reply.from_user = MagicMock(id=999)
    msg = _make_message(reply_to=reply)
    assert is_reply_to_bot(msg, bot_user_id=123) is False


def test_is_reply_to_bot_no_reply():
    msg = _make_message(reply_to=None)
    assert is_reply_to_bot(msg, bot_user_id=123) is False


# --- extract_user_text ---

def test_extract_user_text_strips_username_mention():
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg = _make_message(text="@rkartside_bot cotización para María", entities=[entity])
    result = extract_user_text(msg, bot_user_id=123, bot_username="rkartside_bot")
    assert result == "cotización para María"


def test_extract_user_text_strips_text_mention():
    entity = _make_entity("text_mention", offset=0, length=8, user=MagicMock(id=123))
    msg = _make_message(text="rk-tools cotización para María", entities=[entity])
    result = extract_user_text(msg, bot_user_id=123, bot_username="rkartside_bot")
    assert result == "cotización para María"


def test_extract_user_text_no_mention():
    msg = _make_message(text="sí, incluye ITBIS")
    result = extract_user_text(msg, bot_user_id=123, bot_username="rkartside_bot")
    assert result == "sí, incluye ITBIS"


# --- find_root_message_id ---

def test_find_root_message_id_no_reply():
    msg = _make_message(message_id=100, reply_to=None)
    assert find_root_message_id(msg) == 100


def test_find_root_message_id_with_reply_chain():
    root = _make_message(message_id=100, reply_to=None)
    mid = _make_message(message_id=101, reply_to=root)
    leaf = _make_message(message_id=102, reply_to=mid)
    assert find_root_message_id(leaf) == 100


# --- _send_status ---

@pytest.mark.asyncio
async def test_send_status_returns_message_id():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "result": {"message_id": 999}}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_resp

    with patch("bot.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await _send_status("tok", 1, 2, "Working...")

    assert result == 999


@pytest.mark.asyncio
async def test_send_status_returns_none_on_bad_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": False}

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_resp

    with patch("bot.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await _send_status("tok", 1, 2, "Working...")

    assert result is None


# --- _delete_message ---

@pytest.mark.asyncio
async def test_delete_message_skips_none():
    """Should not make any HTTP call when message_id is None."""
    with patch("bot.httpx.AsyncClient") as mock_client_cls:
        await _delete_message("tok", 1, None)
        mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_delete_message_calls_api():
    mock_http = AsyncMock()

    with patch("bot.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await _delete_message("tok", 123, 456)

    mock_http.post.assert_called_once()
    call_args = mock_http.post.call_args
    assert "deleteMessage" in call_args[0][0]
    assert call_args[1]["json"]["message_id"] == 456


# --- handle_message integration ---

@pytest.mark.asyncio
async def test_handle_message_sends_status_then_text_then_file():
    """Verify order: status msg sent, then deleted, then text, then files."""
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg = _make_message(text="@rkartside_bot cotización", entities=[entity], message_id=10)
    msg.chat = MagicMock(id=1)
    msg.reply_to_message = None

    claude = MagicMock()
    claude.send_message.return_value = ClaudeResponse(
        text="Tu cotización:", file_ids=["file_1"],
        container_id="c1", raw_content=[],
    )
    claude.download_file.return_value = ("cotizacion.pdf", b"pdf-bytes")

    store = ConversationStore()

    calls = []

    async def mock_send_status(token, chat_id, reply_to, text):
        calls.append(("status", text))
        return 999

    async def mock_delete_message(token, chat_id, message_id):
        calls.append(("delete", message_id))

    async def mock_send_text(token, chat_id, reply_to, text):
        calls.append(("text", text))
        return 500  # bot's text message_id

    async def mock_send_document(http, token, chat_id, reply_to, filename, content):
        calls.append(("document", filename))
        return 501  # bot's document message_id

    with patch("bot._send_status", mock_send_status), \
         patch("bot._delete_message", mock_delete_message), \
         patch("bot._send_text", mock_send_text), \
         patch("bot._send_document", mock_send_document):
        await handle_message(
            message=msg, bot_user_id=123, bot_username="rkartside_bot",
            claude=claude, store=store, telegram_token="tok",
        )

    assert calls == [
        ("status", "Generando documento..."),
        ("delete", 999),
        ("text", "Tu cotización:"),
        ("document", "cotizacion.pdf"),
    ]
    # Bot replies should be registered for conversation continuity
    assert store.find_root(1, 500) == 10  # text msg mapped to root
    assert store.find_root(1, 501) == 10  # document msg mapped to root


@pytest.mark.asyncio
async def test_handle_message_deletes_status_on_error():
    """On Claude API error, status message should be deleted before error msg."""
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg = _make_message(text="@rkartside_bot cotización", entities=[entity], message_id=10)
    msg.chat = MagicMock(id=1)
    msg.reply_to_message = None

    claude = MagicMock()
    claude.send_message.side_effect = RuntimeError("API down")

    store = ConversationStore()

    calls = []

    async def mock_send_status(token, chat_id, reply_to, text):
        calls.append(("status", text))
        return 888

    async def mock_delete_message(token, chat_id, message_id):
        calls.append(("delete", message_id))

    async def mock_send_text(token, chat_id, reply_to, text):
        calls.append(("text", text))
        return 501

    with patch("bot._send_status", mock_send_status), \
         patch("bot._delete_message", mock_delete_message), \
         patch("bot._send_text", mock_send_text):
        await handle_message(
            message=msg, bot_user_id=123, bot_username="rkartside_bot",
            claude=claude, store=store, telegram_token="tok",
        )

    assert calls == [
        ("status", "Generando documento..."),
        ("delete", 888),
        ("text", "Error generando el documento. Intenta de nuevo."),
    ]


@pytest.mark.asyncio
async def test_handle_message_reply_continues_conversation():
    """Replying to a bot message should continue the same conversation via registry."""
    store = ConversationStore()

    # Step 1: User @mentions bot (new conversation)
    entity = _make_entity("mention", offset=0, length=14, user=None)
    msg1 = _make_message(text="@rkartside_bot cotización para Manuel", entities=[entity], message_id=100)
    msg1.chat = MagicMock(id=1)
    msg1.reply_to_message = None

    claude = MagicMock()
    claude.send_message.return_value = ClaudeResponse(
        text="Generando cotización...", file_ids=[],
        container_id="c1", raw_content=["mock"],
    )

    async def mock_send_status(token, chat_id, reply_to, text):
        return 900

    async def mock_delete_message(token, chat_id, message_id):
        pass

    async def mock_send_text(token, chat_id, reply_to, text):
        return 201  # bot's reply message_id

    async def mock_send_document(http, token, chat_id, reply_to, filename, content):
        return 202

    with patch("bot._send_status", mock_send_status), \
         patch("bot._delete_message", mock_delete_message), \
         patch("bot._send_text", mock_send_text), \
         patch("bot._send_document", mock_send_document):
        await handle_message(
            message=msg1, bot_user_id=123, bot_username="rkartside_bot",
            claude=claude, store=store, telegram_token="tok",
        )

    # Verify first conversation has 2 messages (user + assistant)
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    assert len(conv.messages) == 2

    # Step 2: User replies to bot's text message (msg 201) with "quita los itbis"
    bot_reply = MagicMock()
    bot_reply.message_id = 201
    bot_reply.from_user = MagicMock(id=123)  # bot's user id
    bot_reply.reply_to_message = None  # Telegram truncates nesting

    msg2 = _make_message(text="quita los itbis", message_id=300)
    msg2.chat = MagicMock(id=1)
    msg2.reply_to_message = bot_reply
    msg2.entities = []

    claude.send_message.return_value = ClaudeResponse(
        text="Listo, sin ITBIS.", file_ids=[],
        container_id="c1", raw_content=["mock2"],
    )

    with patch("bot._send_status", mock_send_status), \
         patch("bot._delete_message", mock_delete_message), \
         patch("bot._send_text", mock_send_text), \
         patch("bot._send_document", mock_send_document):
        await handle_message(
            message=msg2, bot_user_id=123, bot_username="rkartside_bot",
            claude=claude, store=store, telegram_token="tok",
        )

    # Should have 4 messages now (2 from first turn + 2 from second turn)
    assert len(conv.messages) == 4
    assert conv.messages[2]["content"] == "quita los itbis"
