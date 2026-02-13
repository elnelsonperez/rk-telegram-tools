import time
import pytest
from conversations import ConversationStore


def test_new_mention_creates_conversation():
    store = ConversationStore()
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv.messages == []
    assert conv.container_id is None


def test_same_key_returns_same_conversation():
    store = ConversationStore()
    conv1 = store.get_or_create(chat_id=1, root_message_id=100)
    conv1.messages.append({"role": "user", "content": "hello"})

    conv2 = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv2.messages == [{"role": "user", "content": "hello"}]


def test_different_root_message_creates_separate_conversation():
    store = ConversationStore()
    conv1 = store.get_or_create(chat_id=1, root_message_id=100)
    conv1.messages.append({"role": "user", "content": "hello"})

    conv2 = store.get_or_create(chat_id=1, root_message_id=200)
    assert conv2.messages == []


def test_cleanup_removes_expired_conversations():
    store = ConversationStore(ttl_seconds=1)
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    conv.messages.append({"role": "user", "content": "test"})
    conv.last_activity = time.time() - 2  # expired

    store.cleanup()
    conv2 = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv2.messages == []  # new conversation, old one was cleaned


def test_get_or_create_updates_last_activity():
    store = ConversationStore()
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    t1 = conv.last_activity
    time.sleep(0.01)
    store.get_or_create(chat_id=1, root_message_id=100)
    assert conv.last_activity > t1
