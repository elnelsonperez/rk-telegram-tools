# RK Bot Modernization Design

TypeScript rewrite of rk-telegram-tools, borrowing architectural patterns from docuexpress. Single-tenant Telegram bot for RK ArtSide SRL document generation with HTML→PDF via WeasyPrint.

## Tech Stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Runtime | Node.js + TypeScript | Match docuexpress |
| Bot framework | Grammy | Proven in docuexpress |
| Web server | Hono | Lightweight, docuexpress pattern |
| Database | PostgreSQL | Already in use, single-tenant — no need for Turso |
| AI | Anthropic SDK + Skills API + Code Execution | Same capabilities, TypeScript SDK |
| Voice | Soniox | Keep current provider |
| PDF generation | WeasyPrint in Claude's sandbox | HTML→PDF via skill |
| Testing | Vitest | Match docuexpress |
| Linting | Biome | Match docuexpress |
| Deployment | Render | Current platform |

## Project Structure

```
rk-bot/
├── src/
│   ├── app.ts                  # Hono server, webhook endpoint, health check
│   ├── config.ts               # Env config (typed)
│   ├── bot/
│   │   ├── handler.ts          # Message routing (mention, reply, voice, active session)
│   │   ├── commands.ts         # /nuevo, /cancelar
│   │   └── session.ts          # State machine + transitions
│   ├── services/
│   │   ├── claude.ts           # Claude client (skills, code exec, pause-turn)
│   │   ├── conversation.ts     # DB-backed conversation store + message registry
│   │   └── transcriber.ts      # Soniox wrapper
│   └── db/
│       └── client.ts           # PostgreSQL connection + schema init
├── rk-artside-documents/       # The skill (uploaded to Claude)
│   ├── SKILL.md
│   ├── references/
│   │   └── patterns.md         # HTML/CSS templates per doc type
│   └── assets/
│       ├── logo.png
│       └── sello.png
├── tests/
│   ├── session.test.ts
│   ├── handler.test.ts
│   ├── claude.test.ts
│   └── conversation.test.ts
├── package.json
├── tsconfig.json
├── biome.json
└── Procfile
```

## State Machine

```
idle → collecting → confirming → generated
                        ↑            |
                        └────────────┘  (user asks for changes)
```

### States

- **idle** — no active document session
- **collecting** — Claude is gathering info from user
- **confirming** — Claude has enough info, presenting summary before generating
- **generated** — PDF was created and sent

### Transitions

Driven by Claude via the structured `respond` tool returning a `session_action`:

- `"continue"` — stay in current state, keep gathering
- `"confirm"` — move to confirming, show summary
- `"generate"` — trigger PDF generation
- `"new"` — reset to idle, start fresh conversation

Invalid transitions are silently ignored (fail-safe).

## Message Routing

```
Message arrives
    ↓
Is it a command? (/nuevo, /cancelar)
    ├─ YES → handle command directly
    └─ NO ↓
Is it a reply to a bot message?
    ├─ YES → find conversation via message registry
    └─ NO ↓
Is the bot @mentioned?
    ├─ YES → check for active session in chat
    │         ├─ Active session exists → attach, let Claude decide new vs continue
    │         └─ No active session → start new conversation
    └─ NO → ignore
```

### Stale Session Handling

If the active session is >15min old, prompt "resume or start fresh?" before processing.

### Active Session Attachment

New @mentions in group chat check for an active (non-idle) session via `findActiveForChat(chatId)`. If one exists, the message attaches to it and Claude decides from context whether to continue or start fresh. User can explicitly start new with `/nuevo`.

## Claude Integration

### Respond Tool

Claude calls a structured tool instead of returning raw text:

```typescript
{
  name: "respond",
  input: {
    text: string,              // Message to send to user
    session_action: "continue" | "confirm" | "generate" | "new",
    doc_type?: string,         // Inferred doc type (free-form, not enum)
    doc_data?: {               // Only when session_action is "generate"
      title: string,           // e.g. "Cotización", "Contrato de Servicios"
      client_name: string,
      doc_number: string,      // Assigned by bot, passed in context
    },
    pending_question?: string  // What Claude is waiting on from the user
  }
}
```

### Per-Turn System Injection

Each Claude call gets dynamic context appended:

- Current `session_state`
- Current `doc_type` (if inferred)
- Document number (assigned at generation time, not before)
- Instruction: "if the user is clearly starting a new request, return session_action: new"

### Pause-Turn Handling

Claude can emit `stop_reason: "pause_turn"` during code execution (PDF generation). Bot auto-continues up to 10 times, collecting file IDs from results.

### Prompt Caching

- System prompt cached with `ephemeral` control type
- Last user message also cached

### Container Reuse

Store Claude's `container_id` per conversation so skill, assets, and generated files persist across turns. Enables revisions without re-uploading.

### Document Numbering

Bot assigns the number right before telling Claude to generate (injected in that turn's context). Counter table: `(doc_type, year) → last_number`. The `doc_type` key is whatever Claude inferred, normalized to uppercase short code.

## Database Schema

```sql
CREATE TABLE conversations (
    chat_id BIGINT NOT NULL,
    root_message_id BIGINT NOT NULL,
    session_state TEXT NOT NULL DEFAULT 'idle',
    doc_type TEXT,
    container_id TEXT,
    messages JSONB NOT NULL DEFAULT '[]',
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chat_id, root_message_id)
);

CREATE TABLE message_registry (
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    root_message_id BIGINT NOT NULL,
    PRIMARY KEY (chat_id, message_id)
);

CREATE TABLE document_counters (
    doc_type TEXT NOT NULL,
    year INT NOT NULL,
    last_number INT NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_type, year)
);

CREATE INDEX idx_conversations_active
    ON conversations (chat_id, last_activity DESC)
    WHERE session_state != 'idle';
```

TTL-based cleanup (24h) on startup + periodic.

## The Skill — rk-artside-documents

### SKILL.md Structure

1. **Brand system** — colors (gold #9A8455, cream #FFF6ED, dark #333, light gold #C4B896), typography, logo/stamp placement rules
2. **Component library** — reusable HTML/CSS blocks: branded header, client info, item tables, totals, amount box, signature area, stamp overlay
3. **WeasyPrint workflow** — install, generate HTML, convert to PDF, page size defaults to Legal but Claude can choose
4. **ITBIS reference** — only compute if user explicitly asks, opt-in only
5. **Example compositions** — cotización, presupuesto, recibo, carta de compromiso as examples of how to combine components — not the only document types

### Key Principles

- Claude has full freedom to compose new document types using the brand toolkit
- Gold/cream aesthetic is the constant; layout (orientation, columns) is Claude's judgment call
- ITBIS is opt-in — do not ask about it unless the user mentions it
- The four example doc types are a baseline, not an exhaustive list

## Testing Strategy

### Unit Tests

- `session.test.ts` — state machine transitions, invalid transition handling
- `handler.test.ts` — message routing (mention detection, reply detection, active session attachment)
- `claude.test.ts` — response parsing, respond tool extraction, pause-turn continuation
- `conversation.test.ts` — DB operations (get/create, findRoot, findActiveForChat, counters)

### Test Infrastructure

- Test PostgreSQL database (`TEST_DATABASE_URL` env var)
- Mock Grammy context factory
- Mock Claude responses for structured respond tool output

### Linting/Formatting

- Biome for lint + format
- `tsc --noEmit` for type checking
- Pre-commit hooks via lefthook
