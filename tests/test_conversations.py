import os
import time
import pytest
from conversations import ConversationStore

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/rkbot_test",
)


def _exec(store, sql, params=None):
    with store._pool.connection() as conn:
        return conn.execute(sql, params).fetchone()


@pytest.fixture
def store():
    s = ConversationStore(database_url=TEST_DB_URL, ttl_seconds=86400)
    with s._pool.connection() as conn:
        conn.execute("DELETE FROM message_registry")
        conn.execute("DELETE FROM conversations")
    yield s
    s._pool.close()


def test_new_mention_creates_conversation(store):
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv.messages == []
    assert conv.container_id is None


def test_same_key_returns_same_conversation(store):
    conv1 = store.get_or_create(chat_id=1, root_message_id=100)
    conv1.messages.append({"role": "user", "content": "hello"})
    store.save(1, 100, conv1)

    conv2 = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv2.messages == [{"role": "user", "content": "hello"}]


def test_different_root_message_creates_separate_conversation(store):
    conv1 = store.get_or_create(chat_id=1, root_message_id=100)
    conv1.messages.append({"role": "user", "content": "hello"})
    store.save(1, 100, conv1)

    conv2 = store.get_or_create(chat_id=1, root_message_id=200)
    assert conv2.messages == []


def test_cleanup_removes_expired_conversations(store):
    store._ttl = 1
    conv = store.get_or_create(chat_id=1, root_message_id=100)
    conv.messages.append({"role": "user", "content": "test"})
    store.save(1, 100, conv)
    _exec(store,
        "UPDATE conversations SET last_activity = NOW() - interval '2 seconds' WHERE chat_id = 1 AND root_message_id = 100"
    )

    store.cleanup()
    conv2 = store.get_or_create(chat_id=1, root_message_id=100)
    assert conv2.messages == []


def test_get_or_create_updates_last_activity(store):
    store.get_or_create(chat_id=1, root_message_id=100)
    row1 = _exec(store,
        "SELECT last_activity FROM conversations WHERE chat_id = 1 AND root_message_id = 100"
    )

    time.sleep(0.01)
    store.get_or_create(chat_id=1, root_message_id=100)
    row2 = _exec(store,
        "SELECT last_activity FROM conversations WHERE chat_id = 1 AND root_message_id = 100"
    )
    assert row2[0] >= row1[0]


# --- register_message / find_root ---

def test_register_and_find_root(store):
    store.register_message(chat_id=1, message_id=101, root_message_id=100)
    assert store.find_root(chat_id=1, message_id=101) == 100


def test_find_root_returns_none_for_unknown(store):
    assert store.find_root(chat_id=1, message_id=999) is None


def test_find_root_isolates_by_chat(store):
    store.register_message(chat_id=1, message_id=101, root_message_id=100)
    assert store.find_root(chat_id=2, message_id=101) is None


def test_cleanup_removes_message_mappings(store):
    store._ttl = 1
    store.get_or_create(chat_id=1, root_message_id=100)
    store.register_message(chat_id=1, message_id=100, root_message_id=100)
    store.register_message(chat_id=1, message_id=101, root_message_id=100)
    _exec(store,
        "UPDATE conversations SET last_activity = NOW() - interval '2 seconds' WHERE chat_id = 1 AND root_message_id = 100"
    )

    store.cleanup()
    assert store.find_root(chat_id=1, message_id=100) is None
    assert store.find_root(chat_id=1, message_id=101) is None


def test_cleanup_preserves_active_message_mappings(store):
    store.get_or_create(chat_id=1, root_message_id=100)
    store.register_message(chat_id=1, message_id=101, root_message_id=100)

    store.cleanup()
    assert store.find_root(chat_id=1, message_id=101) == 100


def test_registry_size(store):
    assert store.registry_size() == 0
    store.register_message(chat_id=1, message_id=101, root_message_id=100)
    store.register_message(chat_id=1, message_id=102, root_message_id=100)
    assert store.registry_size() == 2
