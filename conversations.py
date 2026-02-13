import json
import logging
from dataclasses import dataclass, field
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS conversations (
    chat_id BIGINT NOT NULL,
    root_message_id BIGINT NOT NULL,
    container_id TEXT,
    messages JSONB NOT NULL DEFAULT '[]',
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chat_id, root_message_id)
);

CREATE TABLE IF NOT EXISTS message_registry (
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    root_message_id BIGINT NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_message_registry_root
    ON message_registry (chat_id, root_message_id);
"""


def _json_default(obj: Any) -> Any:
    """Serialize Anthropic SDK objects (BetaTextBlock, etc.) to dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@dataclass
class Conversation:
    messages: list = field(default_factory=list)
    container_id: str | None = None


class ConversationStore:
    def __init__(self, database_url: str, ttl_seconds: int = 86400):
        self._conninfo = database_url
        self._ttl = ttl_seconds
        self._conn = psycopg.connect(self._conninfo, autocommit=True)
        self._conn.execute(_CREATE_TABLES)
        logger.info("ConversationStore: tables ensured")

    def get_or_create(self, chat_id: int, root_message_id: int) -> Conversation:
        row = self._conn.execute(
            """
            INSERT INTO conversations (chat_id, root_message_id, messages, last_activity)
            VALUES (%s, %s, '[]'::jsonb, NOW())
            ON CONFLICT (chat_id, root_message_id) DO UPDATE SET last_activity = NOW()
            RETURNING messages, container_id
            """,
            (chat_id, root_message_id),
        ).fetchone()
        messages = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return Conversation(messages=messages, container_id=row[1])

    def save(self, chat_id: int, root_message_id: int, conv: Conversation):
        self._conn.execute(
            """
            UPDATE conversations
            SET messages = %s::jsonb, container_id = %s, last_activity = NOW()
            WHERE chat_id = %s AND root_message_id = %s
            """,
            (json.dumps(conv.messages, default=_json_default), conv.container_id, chat_id, root_message_id),
        )

    def register_message(self, chat_id: int, message_id: int, root_message_id: int):
        self._conn.execute(
            """
            INSERT INTO message_registry (chat_id, message_id, root_message_id)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (chat_id, message_id, root_message_id),
        )

    def find_root(self, chat_id: int, message_id: int) -> int | None:
        row = self._conn.execute(
            "SELECT root_message_id FROM message_registry WHERE chat_id = %s AND message_id = %s",
            (chat_id, message_id),
        ).fetchone()
        return row[0] if row else None

    def cleanup(self):
        result = self._conn.execute(
            """
            WITH expired AS (
                DELETE FROM conversations
                WHERE last_activity < NOW() - make_interval(secs => %s)
                RETURNING chat_id, root_message_id
            )
            DELETE FROM message_registry
            USING expired
            WHERE message_registry.chat_id = expired.chat_id
              AND message_registry.root_message_id = expired.root_message_id
            """,
            (self._ttl,),
        )
        if result.rowcount:
            logger.info("Cleaned up expired conversations/registry entries")

    def registry_size(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM message_registry").fetchone()
        return row[0]
