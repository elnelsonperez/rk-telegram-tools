import logging
from dataclasses import dataclass, field
import anthropic

logger = logging.getLogger(__name__)

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
        last_code_exec_idx = -1

        # Find index of last code execution result
        for i, item in enumerate(response.content):
            if item.type == "bash_code_execution_tool_result":
                last_code_exec_idx = i
                content_item = item.content
                if content_item.type == "bash_code_execution_result":
                    for file in content_item.content:
                        if hasattr(file, "file_id"):
                            file_ids.append(file.file_id)

        # Only keep text blocks after the last code execution result
        # If no code execution happened, keep all text blocks
        for i, item in enumerate(response.content):
            if item.type == "text" and i > last_code_exec_idx:
                texts.append(item.text)

        return ClaudeResponse(
            text="".join(texts),
            file_ids=file_ids,
            container_id=response.container.id if response.container else None,
            raw_content=list(response.content),
        )

    def needs_continuation(self, response) -> bool:
        return response.stop_reason == "pause_turn"

    def send_message(self, messages: list[dict], container_id: str | None = None,
                     system_extra: str = "") -> ClaudeResponse:
        container = {
            "skills": [{"type": "custom", "skill_id": self._skill_id, "version": "latest"}]
        }
        if container_id:
            container["id"] = container_id

        system_text = SYSTEM_PROMPT + system_extra if system_extra else SYSTEM_PROMPT
        system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]

        # Mark the last message for caching (covers conversation history)
        cached_messages = list(messages)
        if cached_messages:
            last = cached_messages[-1]
            content = last.get("content", "")
            if isinstance(content, str):
                cached_messages[-1] = {
                    **last,
                    "content": [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}],
                }

        logger.info("Claude API call: %d messages, container=%s", len(messages), container_id)
        response = self._client.beta.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            betas=BETAS,
            system=system,
            container=container,
            messages=cached_messages,
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )
        logger.info("Claude API response: stop_reason=%s", response.stop_reason)

        # Handle pause_turn loops
        continuation = 0
        for _ in range(MAX_CONTINUATIONS):
            if not self.needs_continuation(response):
                break
            continuation += 1
            logger.info("Claude pause_turn, continuing (%d/%d)", continuation, MAX_CONTINUATIONS)
            messages = messages + [{"role": "assistant", "content": response.content}]
            response = self._client.beta.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                betas=BETAS,
                system=system,
                container={"id": response.container.id, **container},
                messages=messages,
                tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
            )
            logger.info("Claude continuation response: stop_reason=%s", response.stop_reason)

        return self.extract_response(response)

    def download_file(self, file_id: str) -> tuple[str, bytes]:
        logger.info("Downloading file: %s", file_id)
        metadata = self._client.beta.files.retrieve_metadata(
            file_id=file_id, betas=["files-api-2025-04-14"]
        )
        content = self._client.beta.files.download(
            file_id=file_id, betas=["files-api-2025-04-14"]
        )
        logger.info("File downloaded: %s (%s)", metadata.filename, file_id)
        return metadata.filename, content.read()
