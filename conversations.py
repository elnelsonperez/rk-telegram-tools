import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Conversation:
    messages: list = field(default_factory=list)
    container_id: str | None = None
    last_activity: float = field(default_factory=time.time)


class ConversationStore:
    def __init__(self, ttl_seconds: int = 86400):
        self._store: dict[tuple[int, int], Conversation] = {}
        self._message_to_root: dict[tuple[int, int], int] = {}  # (chat_id, msg_id) → root_id
        self._ttl = ttl_seconds

    def get_or_create(self, chat_id: int, root_message_id: int) -> Conversation:
        key = (chat_id, root_message_id)
        if key not in self._store:
            self._store[key] = Conversation()
        self._store[key].last_activity = time.time()
        return self._store[key]

    def register_message(self, chat_id: int, message_id: int, root_message_id: int):
        """Map a message_id to its conversation root so replies can find the conversation."""
        self._message_to_root[(chat_id, message_id)] = root_message_id

    def find_root(self, chat_id: int, message_id: int) -> int | None:
        """Look up the root_message_id for a given message_id, or None if unknown."""
        return self._message_to_root.get((chat_id, message_id))

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.last_activity > self._ttl]
        expired_keys = set(expired)
        for k in expired:
            del self._store[k]
        # Clean up message mappings for expired conversations
        expired_msgs = [k for k, root in self._message_to_root.items()
                        if (k[0], root) in expired_keys]
        for k in expired_msgs:
            del self._message_to_root[k]
        if expired:
            logger.info("Cleaned up %d expired conversations, %d remaining", len(expired), len(self._store))
