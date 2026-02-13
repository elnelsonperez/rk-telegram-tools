import pytest
from unittest.mock import MagicMock
from bot import is_bot_mentioned, is_reply_to_bot, extract_user_text, find_root_message_id


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
