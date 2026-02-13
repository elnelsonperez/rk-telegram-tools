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
