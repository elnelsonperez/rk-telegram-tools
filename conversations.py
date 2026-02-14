import functools
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool

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

CREATE TABLE IF NOT EXISTS document_counters (
    doc_type TEXT NOT NULL,
    year INT NOT NULL,
    last_number INT NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_type, year)
);
"""

DOC_TYPES = {"COT": "Cotización", "PRES": "Presupuesto", "REC": "Recibo", "CARTA": "Carta de Compromiso"}


def _retry_on_disconnect(method):
    """Retry a method once if the database connection was lost."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except psycopg.OperationalError as e:
            logger.warning("Database connection lost (%s), retrying...", e)
            time.sleep(0.5)
            return method(self, *args, **kwargs)
    return wrapper


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
        self._pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=4,
            check=ConnectionPool.check_connection,
            kwargs={"autocommit": True},
        )
        self._ttl = ttl_seconds
        with self._pool.connection() as conn:
            conn.execute(_CREATE_TABLES)
        logger.info("ConversationStore: tables ensured")

    @_retry_on_disconnect
    def get_or_create(self, chat_id: int, root_message_id: int) -> Conversation:
        with self._pool.connection() as conn:
            row = conn.execute(
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

    @_retry_on_disconnect
    def save(self, chat_id: int, root_message_id: int, conv: Conversation):
        with self._pool.connection() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET messages = %s::jsonb, container_id = %s, last_activity = NOW()
                WHERE chat_id = %s AND root_message_id = %s
                """,
                (json.dumps(conv.messages, default=_json_default), conv.container_id, chat_id, root_message_id),
            )

    @_retry_on_disconnect
    def register_message(self, chat_id: int, message_id: int, root_message_id: int):
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO message_registry (chat_id, message_id, root_message_id)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (chat_id, message_id, root_message_id),
            )

    @_retry_on_disconnect
    def find_root(self, chat_id: int, message_id: int) -> int | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT root_message_id FROM message_registry WHERE chat_id = %s AND message_id = %s",
                (chat_id, message_id),
            ).fetchone()
        return row[0] if row else None

    @_retry_on_disconnect
    def cleanup(self):
        with self._pool.connection() as conn:
            result = conn.execute(
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

    @_retry_on_disconnect
    def registry_size(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM message_registry").fetchone()
        return row[0]

    @_retry_on_disconnect
    def next_document_number(self, doc_type: str, year: int) -> str:
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO document_counters (doc_type, year, last_number)
                VALUES (%s, %s, 1)
                ON CONFLICT (doc_type, year) DO UPDATE SET last_number = document_counters.last_number + 1
                RETURNING last_number
                """,
                (doc_type, year),
            ).fetchone()
        return f"{doc_type}-{year}-{row[0]:03d}"

    @_retry_on_disconnect
    def get_last_document_numbers(self, year: int) -> dict[str, str]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT doc_type, last_number FROM document_counters WHERE year = %s",
                (year,),
            ).fetchall()
        return {row[0]: f"{row[0]}-{year}-{row[1]:03d}" for row in rows}
