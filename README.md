# RK Bot

Telegram bot for **RK ArtSide SRL** document generation. Generates professional branded PDFs (cotizaciones, presupuestos, recibos, cartas, and any custom document) via Claude Skills API with HTML-to-PDF (WeasyPrint).

## Stack

- **TypeScript** + pnpm
- **Grammy** (Telegram Bot API)
- **Hono** (HTTP server)
- **PostgreSQL** (conversations, message registry, document counters)
- **Claude Sonnet 4.6** (Skills API + Code Execution)
- **Soniox** (voice transcription)
- **WeasyPrint** (HTML-to-PDF in Claude's sandbox)

## Setup

### 1. Install dependencies

```bash
pnpm install
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_WEBHOOK_SECRET` | Random secret string for webhook validation |
| `ANTHROPIC_API_KEY` | Claude API key |
| `RK_SKILL_ID` | Custom skill ID (upload `rk-artside-documents/` to Claude) |
| `DATABASE_URL` | PostgreSQL connection string |
| `SONIOX_API_KEY` | Soniox API key for voice transcription |

### 3. Set up the database

The bot runs migrations automatically on startup. Just provide a valid `DATABASE_URL`.

### 4. Register the webhook

```bash
npx tsx scripts/set-webhook.ts https://your-render-url.onrender.com
```

This tells Telegram to send updates to your server. You need `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` in your environment.

### 5. Upload the Claude skill

The `rk-artside-documents/` folder contains the custom Claude skill. Upload it via the Anthropic dashboard to get the `RK_SKILL_ID`.

## Development

```bash
pnpm dev          # Dev server with hot reload (tsx watch)
pnpm test         # Run tests
pnpm test:coverage # Run tests with coverage report
pnpm typecheck    # TypeScript type checking
pnpm lint         # Biome linting
pnpm build        # Build for production (esbuild)
```

## Deployment (Render)

- **Root directory:** `/`
- **Build command:** `pnpm install && pnpm build`
- **Start command:** `node dist/index.js`

The `Procfile` is also included for platforms that use it.

After deploying, register the webhook:

```bash
npx tsx scripts/set-webhook.ts https://your-app.onrender.com
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/nuevo` | Start a new document |
| `/cancelar` | Cancel the current document |
| `/ayuda` | Show help |

## How It Works

1. User @mentions the bot in a group chat with a document request
2. Bot routes the message through a state machine (idle - collecting - confirming - generated)
3. Claude gathers required info via structured responses
4. When ready, Claude generates an HTML document with RK ArtSide branding
5. WeasyPrint converts HTML to PDF in Claude's sandbox
6. Bot sends the PDF back to the chat

The bot supports voice notes (transcribed via Soniox), conversation continuations via replies, and active session attachment (new @mentions attach to in-progress documents).
