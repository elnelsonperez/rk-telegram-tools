# RK ArtSide Telegram Bot - Design Document

## Overview

A Telegram bot for RK ArtSide SRL's company group that generates business documents (cotizaciones, presupuestos, recibos) using Claude's API with a custom skill that produces PDFs via code execution.

## Stack

- **Language:** Python 3.13
- **Package manager:** uv (with requirements.txt exported for deploy)
- **Web framework:** Starlette (async, lightweight)
- **Telegram SDK:** python-telegram-bot v20+ (async)
- **AI:** Anthropic SDK with beta headers (code-execution, skills, files)
- **Deployment:** Koyeb free tier, webhook mode, auto-deploy on GitHub push

## Architecture

```
Telegram Group
    |
    | (user @mentions bot or replies to bot message)
    v
Telegram API --webhook POST--> Koyeb (Python app)
                                    |
                                    +-- /webhook: verify secret header, parse update
                                    +-- bot.py: detect mention or reply-to-bot
                                    +-- conversations.py: lookup/create conversation
                                    +-- claude_client.py: call Claude API with skill
                                    |     - system prompt (RK ArtSide doc assistant)
                                    |     - conversation history
                                    |     - container.skills: [rk-artside-documents]
                                    |     - tools: [code_execution]
                                    |     - handle pause_turn loops
                                    |
                                    +-- If response has file_ids:
                                    |     - Download PDF via Files API
                                    |     - Send as Telegram document
                                    |
                                    +-- Send text response to Telegram
                                    +-- Update conversation history
```

## Bot Behavior

### Trigger Rules

- **@mention (not a reply):** Always starts a fresh conversation. No prior context.
- **Reply to bot's message:** Continues the existing conversation. Preserves context for follow-up questions and document revisions.
- **All other messages:** Ignored.

### Conversation Lifecycle

Conversations are keyed by reply chain (traced back to the original @mention). This means:

1. `@bot cotizacion para Maria Lopez...` -> new conversation
2. Bot asks "incluye ITBIS?" -> user replies "si" -> same conversation
3. Bot generates PDF -> user replies "cambia el precio a $5000" -> same conversation (revision)
4. `@bot recibo para Juan...` -> new conversation (fresh, no Maria context)

### Conversation Storage

- In-memory Python dict
- Keyed by reply chain root message ID + chat ID
- Daily TTL cleanup (conversations expire after 24 hours of inactivity)
- State lost on redeploy (acceptable for short-lived doc generation workflows)

## Claude API Integration

### Request Shape

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250929",  # or appropriate model
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    system=SYSTEM_PROMPT,
    container={
        "skills": [{"type": "custom", "skill_id": RK_SKILL_ID, "version": "latest"}]
    },
    messages=conversation_history,
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
)
```

### pause_turn Handling

Skills may take multiple turns to generate PDFs. The bot loops on `pause_turn` stop reasons, feeding the response back as assistant messages until the operation completes. Max 10 retries.

### File Download

When the response contains `file_id` attributes (from code execution results), the bot:
1. Retrieves file metadata via Files API
2. Downloads file content
3. Sends as a Telegram document with the original filename

### Multi-turn Container Reuse

For conversations that span multiple user messages, the container ID from the first Claude response is stored and reused in subsequent requests to maintain the code execution environment.

## System Prompt

```
Eres el asistente de documentos de RK ArtSide SRL. Generas cotizaciones, presupuestos y recibos de pago.

## Comportamiento

1. Si tienes toda la informacion, genera el documento inmediatamente
2. Solo pregunta si hay ambiguedad real
3. Se breve - es Telegram

## Que necesitas para cada documento

Cotizacion/Presupuesto:
- Nombre del cliente
- Items/servicios con cantidades y precios
- Si incluye ITBIS (si no se menciona, pregunta)

Recibo:
- Nombre del cliente
- Monto
- Concepto

## Cuando generes

1. Verifica la matematica
2. Genera el PDF usando el skill rk-artside-documents
3. Envia el documento con un resumen breve

## Notas

- Moneda: RD$ (Pesos Dominicanos)
- Si el usuario da toda la info, actua. No confirmes si no es necesario.
- Solo pregunta lo que realmente falta.
```

## Project Structure

```
rkbot/
├── pyproject.toml             # uv project: deps declared here
├── uv.lock                    # uv lockfile
├── requirements.txt           # auto-generated via pre-commit hook
├── .python-version            # 3.13
├── .pre-commit-config.yaml    # hook to export requirements.txt
├── Procfile                   # web: uvicorn app:app --host 0.0.0.0 --port $PORT
├── .gitignore
├── app.py                     # Starlette app: /webhook + /health endpoints
├── bot.py                     # Telegram message handling (mentions, replies, routing)
├── claude_client.py           # Claude API wrapper (skills, pause_turn, file download)
├── conversations.py           # In-memory conversation store (reply-chain keyed, daily TTL)
└── config.py                  # Environment variable loading and validation
```

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `ANTHROPIC_API_KEY` | Claude API key |
| `RK_SKILL_ID` | Custom skill ID for rk-artside-documents |
| `WEBHOOK_SECRET` | Random string for Telegram webhook verification |

## Webhook Security

Telegram's `setWebhook` accepts a `secret_token` parameter. Every webhook request includes this as the `X-Telegram-Bot-Api-Secret-Token` header. The `/webhook` endpoint verifies this header and rejects requests with a 403 if it doesn't match.

## Deployment

- **Platform:** Koyeb free tier (512MB RAM, 0.1 vCPU)
- **Build:** Koyeb buildpack detects `requirements.txt` and `.python-version`
- **Auto-deploy:** Connected to GitHub repo, deploys on push to main
- **Scale-to-zero:** After 1 hour of inactivity; cold start 1-5 seconds
- **Request timeout:** 100 seconds (fits 30-60 second Claude API calls)

## Pre-commit Hook

A pre-commit hook runs `uv export --no-hashes -o requirements.txt` before each commit, ensuring requirements.txt stays in sync with pyproject.toml.
