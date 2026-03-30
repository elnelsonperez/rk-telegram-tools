# RK Bot

Telegram bot for RK ArtSide SRL document generation. Generates professional PDFs (cotizaciones, presupuestos, recibos, cartas, and any branded document) via Claude Skills API with HTML→PDF (WeasyPrint).

## Stack

TypeScript, pnpm, Grammy (Telegram), Hono (HTTP), PostgreSQL (pg), Claude Sonnet 4.6 (Skills API + Code Execution), Soniox (voice), Vitest, Biome, esbuild.

## Commands

- `pnpm dev` — Dev server (tsx watch)
- `pnpm test` — vitest run
- `pnpm test:coverage` — vitest with v8 coverage
- `pnpm typecheck` — tsc --noEmit
- `pnpm lint` — biome check
- `pnpm build` — esbuild → dist/index.js

## Project Structure

- `src/index.ts` — Entry point: services init, bot setup, server start
- `src/app.ts` — Hono webhook server (GET /health, POST /webhook)
- `src/config.ts` — Zod-validated env vars
- `src/logger.ts` — Pino logger
- `src/bot/handler.ts` — Text/voice message routing, active session attachment, and processMessage flow
- `src/bot/commands.ts` — /nuevo, /cancelar, /ayuda
- `src/bot/session.ts` — State machine (idle→collecting→confirming→generated) using TypeScript enums
- `src/services/claude.ts` — Claude client, respond tool, pause_turn loop, file download
- `src/services/conversation.ts` — Conversation CRUD, message registry, doc counters
- `src/services/transcriber.ts` — Soniox voice transcription
- `src/db/client.ts` — PostgreSQL pool + migrations
- `rk-artside-documents/` — Claude skill (SKILL.md + HTML/CSS patterns + assets)

## Key Patterns

- **Enums for state:** `SessionState` and `SessionAction` are TypeScript enums in `session.ts`. Always use enum values, never string literals.
- **State machine:** `session.ts` owns transitions. `mapActionToState()` validates — invalid actions silently preserve state.
- **Structured responses:** Claude uses the `respond` tool, not raw text. Bot extracts `session_action` to drive state.
- **Active session attachment:** New @mentions in groups check for active (non-idle) sessions. Claude decides continue vs. new.
- **ITBIS:** Opt-in only. Never ask about ITBIS unless the user mentions it.
- **Currency:** Default RD$ but user can override.
- **Document types:** The 4 examples (COT, PRES, REC, CARTA) are baselines. Any document can be generated with RK branding.
- **No Markdown tables:** System prompt forbids tables in responses (Telegram doesn't render them). Use lists instead.

## Deployment

Render. `Procfile`: `web: node dist/index.js`
