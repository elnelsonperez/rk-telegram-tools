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
        self._ttl = ttl_seconds

    def get_or_create(self, chat_id: int, root_message_id: int) -> Conversation:
        key = (chat_id, root_message_id)
        if key not in self._store:
            self._store[key] = Conversation()
        self._store[key].last_activity = time.time()
        return self._store[key]

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.last_activity > self._ttl]
        for k in expired:
            del self._store[k]
        if expired:
            logger.info("Cleaned up %d expired conversations, %d remaining", len(expired), len(self._store))
