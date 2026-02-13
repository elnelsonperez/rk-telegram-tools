# RK ArtSide Telegram Bot - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram bot that generates company documents (cotizaciones, presupuestos, recibos) by bridging Telegram messages to the Claude API with a custom PDF-generating skill.

**Architecture:** Webhook-based Starlette server receives Telegram updates, detects @mentions and replies, manages conversation history in-memory, calls Claude API with the rk-artside-documents skill, downloads generated PDFs via the Files API, and sends them back as Telegram documents.

**Tech Stack:** Python 3.13, uv, Starlette, python-telegram-bot v20+, anthropic SDK, uvicorn. Deployed on Koyeb free tier.

**Design doc:** `docs/plans/2026-02-13-telegram-bot-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `Procfile`
- Create: `.pre-commit-config.yaml`

**Step 1: Initialize uv project**

```bash
cd /Users/nelsonperez/code/rkbot
uv init --no-readme
```

This creates `pyproject.toml`, `.python-version`, and `hello.py`. Delete `hello.py`.

**Step 2: Set Python version**

Ensure `.python-version` contains `3.13`.

**Step 3: Add dependencies**

```bash
uv add anthropic python-telegram-bot starlette uvicorn httpx
uv add --dev pytest pytest-asyncio pre-commit
```

Dependencies:
- `anthropic` — Claude API SDK
- `python-telegram-bot` — Telegram bot framework (we use its data types, not its built-in server)
- `starlette` — ASGI web framework for webhook endpoint
- `uvicorn` — ASGI server
- `httpx` — async HTTP client (for Telegram API calls and file downloads)
- `pytest` / `pytest-asyncio` — testing
- `pre-commit` — git hooks

**Step 4: Create .gitignore**

```gitignore
__pycache__/
*.pyc
.env
.venv/
*.egg-info/
dist/
```

**Step 5: Create Procfile**

```
web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
```

**Step 6: Create pre-commit config**

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: uv-export
        name: Export requirements.txt
        entry: bash -c 'uv export --no-hashes --no-dev -o requirements.txt && git add requirements.txt'
        language: system
        pass_filenames: false
        files: '(pyproject\.toml|uv\.lock)$'
```

**Step 7: Install pre-commit hooks**

```bash
uv run pre-commit install
```

**Step 8: Generate initial requirements.txt**

```bash
uv export --no-hashes --no-dev -o requirements.txt
```

**Step 9: Commit**

```bash
git add pyproject.toml uv.lock .python-version .gitignore Procfile .pre-commit-config.yaml requirements.txt
git commit -m "Scaffold project with uv, deps, and pre-commit hook"
```

---

### Task 2: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

`tests/test_config.py`:
```python
import os
import pytest
from config import load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("RK_SKILL_ID", "skill_123")
    monkeypatch.setenv("WEBHOOK_SECRET", "secret123")

    cfg = load_config()
    assert cfg.telegram_bot_token == "test-token"
    assert cfg.anthropic_api_key == "test-key"
    assert cfg.rk_skill_id == "skill_123"
    assert cfg.webhook_secret == "secret123"


def test_load_config_missing_var_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RK_SKILL_ID", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        load_config()
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

**Step 3: Write minimal implementation**

`config.py`:
```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    anthropic_api_key: str
    rk_skill_id: str
    webhook_secret: str


_REQUIRED = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "RK_SKILL_ID", "WEBHOOK_SECRET"]


def load_config() -> Config:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        rk_skill_id=os.environ["RK_SKILL_ID"],
        webhook_secret=os.environ["WEBHOOK_SECRET"],
    )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "Add config module with env var loading"
```

---

### Task 3: Conversation Store

**Files:**
- Create: `conversations.py`
- Create: `tests/test_conversations.py`

The conversation store manages Claude API message history keyed by reply chain. Each conversation tracks:
- `messages`: list of Claude API message dicts (`{"role": "user"|"assistant", "content": ...}`)
- `container_id`: optional, reused across multi-turn Claude calls
- `last_activity`: timestamp for TTL cleanup

**Step 1: Write the failing tests**

`tests/test_conversations.py`:
```python
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_conversations.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'conversations'`

**Step 3: Write minimal implementation**

`conversations.py`:
```python
import time
from dataclasses import dataclass, field


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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_conversations.py -v
```

Expected: 5 passed

**Step 5: Commit**

```bash
git add conversations.py tests/test_conversations.py
git commit -m "Add in-memory conversation store with TTL cleanup"
```

---

### Task 4: Claude Client

**Files:**
- Create: `claude_client.py`
- Create: `tests/test_claude_client.py`

This module wraps the Anthropic SDK to:
1. Send messages with the rk-artside-documents skill
2. Handle `pause_turn` loops
3. Extract text content and file_ids from responses
4. Download files via the Files API

**Step 1: Write the failing tests**

`tests/test_claude_client.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from claude_client import ClaudeClient, ClaudeResponse


@pytest.fixture
def client():
    return ClaudeClient(api_key="test-key", skill_id="skill_123")


def test_extract_text_from_response(client):
    """Test extracting text blocks from a Claude API response."""
    response = MagicMock()
    response.content = [
        MagicMock(type="text", text="Here is your document"),
        MagicMock(type="text", text=" - total RD$ 12,435"),
    ]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_123")

    result = client.extract_response(response)
    assert result.text == "Here is your document - total RD$ 12,435"
    assert result.file_ids == []
    assert result.container_id == "container_123"


def test_extract_file_ids_from_response(client):
    """Test extracting file_ids from code execution results."""
    file_block = MagicMock()
    file_block.file_id = "file_abc"
    file_block.type = "file"

    exec_result = MagicMock()
    exec_result.type = "bash_code_execution_result"
    exec_result.content = [file_block]

    tool_result = MagicMock()
    tool_result.type = "bash_code_execution_tool_result"
    tool_result.content = exec_result

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "PDF generated"

    response = MagicMock()
    response.content = [tool_result, text_block]
    response.stop_reason = "end_turn"
    response.container = MagicMock(id="container_456")

    result = client.extract_response(response)
    assert result.text == "PDF generated"
    assert result.file_ids == ["file_abc"]


def test_needs_continuation(client):
    response = MagicMock()
    response.stop_reason = "pause_turn"
    assert client.needs_continuation(response) is True

    response.stop_reason = "end_turn"
    assert client.needs_continuation(response) is False
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_claude_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'claude_client'`

**Step 3: Write minimal implementation**

`claude_client.py`:
```python
from dataclasses import dataclass, field
import anthropic

SYSTEM_PROMPT = """Eres el asistente de documentos de RK ArtSide SRL. Generas cotizaciones, presupuestos y recibos de pago.

## Comportamiento

1. Si tienes toda la información, genera el documento inmediatamente
2. Solo pregunta si hay ambigüedad real
3. Sé breve - es Telegram

## Qué necesitas para cada documento

Cotización/Presupuesto:
- Nombre del cliente
- Items/servicios con cantidades y precios
- Si incluye ITBIS (si no se menciona, pregunta)

Recibo:
- Nombre del cliente
- Monto
- Concepto

## Cuando generes

1. Verifica la matemática
2. Genera el PDF usando el skill rk-artside-documents
3. Envía el documento con un resumen breve

## Notas

- Moneda: RD$ (Pesos Dominicanos)
- Si el usuario da toda la info, actúa. No confirmes si no es necesario.
- Solo pregunta lo que realmente falta."""

BETAS = ["code-execution-2025-08-25", "skills-2025-10-02"]
MAX_CONTINUATIONS = 10


@dataclass
class ClaudeResponse:
    text: str
    file_ids: list[str] = field(default_factory=list)
    container_id: str | None = None
    raw_content: list = field(default_factory=list)


class ClaudeClient:
    def __init__(self, api_key: str, skill_id: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._skill_id = skill_id

    def extract_response(self, response) -> ClaudeResponse:
        texts = []
        file_ids = []
        for item in response.content:
            if item.type == "text":
                texts.append(item.text)
            elif item.type == "bash_code_execution_tool_result":
                content_item = item.content
                if content_item.type == "bash_code_execution_result":
                    for file in content_item.content:
                        if hasattr(file, "file_id"):
                            file_ids.append(file.file_id)

        return ClaudeResponse(
            text="".join(texts),
            file_ids=file_ids,
            container_id=response.container.id if response.container else None,
            raw_content=list(response.content),
        )

    def needs_continuation(self, response) -> bool:
        return response.stop_reason == "pause_turn"

    def send_message(self, messages: list[dict], container_id: str | None = None) -> ClaudeResponse:
        container = {
            "skills": [{"type": "custom", "skill_id": self._skill_id, "version": "latest"}]
        }
        if container_id:
            container["id"] = container_id

        response = self._client.beta.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            betas=BETAS,
            system=SYSTEM_PROMPT,
            container=container,
            messages=messages,
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )

        # Handle pause_turn loops
        for _ in range(MAX_CONTINUATIONS):
            if not self.needs_continuation(response):
                break
            messages = messages + [{"role": "assistant", "content": response.content}]
            response = self._client.beta.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                betas=BETAS,
                system=SYSTEM_PROMPT,
                container={"id": response.container.id, **container},
                messages=messages,
                tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
            )

        return self.extract_response(response)

    def download_file(self, file_id: str) -> tuple[str, bytes]:
        metadata = self._client.beta.files.retrieve_metadata(
            file_id=file_id, betas=["files-api-2025-04-14"]
        )
        content = self._client.beta.files.download(
            file_id=file_id, betas=["files-api-2025-04-14"]
        )
        return metadata.filename, content.read()
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_claude_client.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add claude_client.py tests/test_claude_client.py
git commit -m "Add Claude client with skill invocation and file download"
```

---

### Task 5: Bot Message Handler

**Files:**
- Create: `bot.py`
- Create: `tests/test_bot.py`

This module handles Telegram message routing:
1. Determines if a message is a @mention or a reply to the bot
2. Extracts the user's text (stripping the @mention)
3. Traces the reply chain to find the root message ID (conversation key)
4. Orchestrates: conversation lookup -> Claude API call -> send response + files

**Step 1: Write the failing tests**

`tests/test_bot.py`:
```python
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


def test_is_bot_mentioned_true():
    bot_user = MagicMock()
    bot_user.id = 123

    mention_user = MagicMock()
    mention_user.id = 123
    entity = _make_entity("mention", offset=0, length=8, user=mention_user)

    msg = _make_message(text="@rkbot cotización", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123) is True


def test_is_bot_mentioned_false_different_user():
    entity = _make_entity("mention", user=MagicMock(id=999))
    msg = _make_message(text="@someone hello", entities=[entity])
    assert is_bot_mentioned(msg, bot_user_id=123) is False


def test_is_bot_mentioned_false_no_entities():
    msg = _make_message(text="hello")
    assert is_bot_mentioned(msg, bot_user_id=123) is False


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


def test_extract_user_text_strips_mention():
    entity = _make_entity("mention", offset=0, length=6, user=MagicMock(id=123))
    msg = _make_message(text="@rkbot cotización para María", entities=[entity])
    result = extract_user_text(msg, bot_user_id=123)
    assert result == "cotización para María"


def test_extract_user_text_no_mention():
    msg = _make_message(text="sí, incluye ITBIS")
    result = extract_user_text(msg, bot_user_id=123)
    assert result == "sí, incluye ITBIS"


def test_find_root_message_id_no_reply():
    msg = _make_message(message_id=100, reply_to=None)
    assert find_root_message_id(msg) == 100


def test_find_root_message_id_with_reply_chain():
    root = _make_message(message_id=100, reply_to=None)
    mid = _make_message(message_id=101, reply_to=root)
    leaf = _make_message(message_id=102, reply_to=mid)
    assert find_root_message_id(leaf) == 100
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_bot.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bot'`

**Step 3: Write minimal implementation**

`bot.py`:
```python
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
        return

    chat_id = message.chat.id

    if mentioned and not message.reply_to_message:
        root_id = message.message_id  # new conversation
    else:
        root_id = find_root_message_id(message)

    conv = store.get_or_create(chat_id=chat_id, root_message_id=root_id)
    conv.messages.append({"role": "user", "content": user_text})

    try:
        result = claude.send_message(conv.messages, container_id=conv.container_id)
    except Exception:
        logger.exception("Claude API error")
        await _send_text(telegram_token, chat_id, message.message_id,
                         "Error generando el documento. Intenta de nuevo.")
        conv.messages.pop()  # remove failed user message
        return

    conv.container_id = result.container_id
    conv.messages.append({"role": "assistant", "content": result.raw_content})

    # Send files first, then text
    async with httpx.AsyncClient() as http:
        for file_id in result.file_ids:
            try:
                filename, content = claude.download_file(file_id)
                await _send_document(http, telegram_token, chat_id, message.message_id,
                                     filename, content)
            except Exception:
                logger.exception(f"Failed to download/send file {file_id}")

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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_bot.py -v
```

Expected: 10 passed

**Step 5: Commit**

```bash
git add bot.py tests/test_bot.py
git commit -m "Add bot message handler with mention/reply detection"
```

---

### Task 6: Starlette Webhook App

**Files:**
- Create: `app.py`
- Create: `tests/test_app.py`

The app has two endpoints:
- `GET /health` — returns 200, used by Koyeb health checks
- `POST /webhook` — receives Telegram updates, verifies secret header, dispatches to bot handler

**Step 1: Write the failing tests**

`tests/test_app.py`:
```python
import pytest
import os
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("RK_SKILL_ID", "skill_123")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")


@pytest.fixture
def client():
    from app import app
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_rejects_missing_secret(client):
    response = client.post("/webhook", json={"update_id": 1})
    assert response.status_code == 403


def test_webhook_rejects_wrong_secret(client):
    response = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 403


def test_webhook_accepts_correct_secret(client):
    response = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )
    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_app.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

**Step 3: Write minimal implementation**

`app.py`:
```python
import asyncio
import logging
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from telegram import Update

from config import load_config
from claude_client import ClaudeClient
from conversations import ConversationStore
from bot import handle_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = load_config()
claude = ClaudeClient(api_key=config.anthropic_api_key, skill_id=config.rk_skill_id)
store = ConversationStore()

# We need the bot's user ID to detect mentions/replies.
# This is fetched once on startup via getMe.
_bot_user_id: int | None = None


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def webhook(request: Request) -> JSONResponse:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != config.webhook_secret:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    body = await request.json()
    update = Update.de_json(body, bot=None)

    if update and update.message and update.message.text:
        global _bot_user_id
        if _bot_user_id is None:
            import httpx
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    f"https://api.telegram.org/bot{config.telegram_bot_token}/getMe"
                )
                _bot_user_id = resp.json()["result"]["id"]

        asyncio.create_task(
            handle_message(
                message=update.message,
                bot_user_id=_bot_user_id,
                claude=claude,
                store=store,
                telegram_token=config.telegram_bot_token,
            )
        )

    # Always respond 200 quickly so Telegram doesn't retry
    return JSONResponse({"ok": True})


async def on_startup():
    store.cleanup()
    logger.info("RK ArtSide bot started")


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/webhook", webhook, methods=["POST"]),
    ],
    on_startup=[on_startup],
)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_app.py -v
```

Expected: 4 passed

**Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "Add Starlette webhook app with health check and secret verification"
```

---

### Task 7: Webhook Registration Script

**Files:**
- Create: `scripts/set_webhook.py`

A one-time script to register the webhook URL with Telegram. Run manually after deploying to Koyeb.

**Step 1: Write the script**

`scripts/set_webhook.py`:
```python
"""Register the Telegram webhook. Run once after deploying.

Usage: uv run python scripts/set_webhook.py <APP_URL>
Example: uv run python scripts/set_webhook.py https://rkbot-xyz.koyeb.app
"""
import sys
import os
import httpx


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <APP_URL>")
        sys.exit(1)

    app_url = sys.argv[1].rstrip("/")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    secret = os.environ.get("WEBHOOK_SECRET")

    if not token or not secret:
        print("Error: Set TELEGRAM_BOT_TOKEN and WEBHOOK_SECRET env vars")
        sys.exit(1)

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": f"{app_url}/webhook",
            "secret_token": secret,
            "allowed_updates": ["message"],
        },
    )

    result = response.json()
    if result.get("ok"):
        print(f"Webhook set to {app_url}/webhook")
    else:
        print(f"Error: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/set_webhook.py
git commit -m "Add webhook registration script"
```

---

### Task 8: Final Wiring and Manual Test

**Step 1: Create .env.example for documentation**

`.env.example`:
```
TELEGRAM_BOT_TOKEN=
ANTHROPIC_API_KEY=
RK_SKILL_ID=
WEBHOOK_SECRET=
```

**Step 2: Run all tests**

```bash
uv run pytest -v
```

Expected: All tests pass (config: 2, conversations: 5, bot: 10, app: 4 = 21 total)

**Step 3: Test locally**

```bash
# Copy .env.example to .env and fill in real values
# Then:
export $(cat .env | xargs) && uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

Verify health endpoint:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

**Step 4: Commit everything**

```bash
git add .env.example
git commit -m "Add env example file"
```

**Step 5: Push to GitHub and deploy**

```bash
git push -u origin main
```

Then:
1. Go to Koyeb dashboard
2. Create new service from GitHub repo `elnelsonperez/rk-telegram-tools`
3. Set environment variables: `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `RK_SKILL_ID`, `WEBHOOK_SECRET`
4. Deploy
5. Once deployed, run the webhook registration:
   ```bash
   export $(cat .env | xargs) && uv run python scripts/set_webhook.py https://<your-app>.koyeb.app
   ```
6. Go to Telegram group, @mention the bot with a document request, verify it responds

---

## Task Dependency Graph

```
Task 1 (scaffolding)
  └── Task 2 (config)
  └── Task 3 (conversations)
  └── Task 4 (claude_client)
        └── Task 5 (bot) ← depends on claude_client + conversations
              └── Task 6 (app) ← depends on everything
                    └── Task 7 (webhook script)
                          └── Task 8 (final wiring + deploy)
```

Tasks 2, 3, and 4 can be done in parallel after Task 1.
