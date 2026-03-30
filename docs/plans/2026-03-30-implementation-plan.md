# RK Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite rk-telegram-tools as a TypeScript project with state machine, structured Claude responses, active session attachment, and HTML→PDF generation via WeasyPrint skill.

**Architecture:** Grammy bot with Hono webhook server on Render. PostgreSQL for conversations, message registry, and document counters. Claude Skills API with code execution for PDF generation. Structured "respond" tool for predictable bot behavior. State machine (idle→collecting→confirming→generated) drives conversation flow.

**Tech Stack:** TypeScript, pnpm, Grammy, Hono, PostgreSQL (pg), Anthropic SDK, Soniox, Vitest, Biome, esbuild, pino.

---

## Task 1: Project Scaffold

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `biome.json`
- Create: `scripts/build.ts`
- Create: `Procfile`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/index.ts` (placeholder)

**Step 1: Initialize project**

```bash
cd /Users/nelsonperez/code/telegrambots/rk-bot
pnpm init
```

**Step 2: Install dependencies**

```bash
pnpm add grammy hono @hono/node-server @anthropic-ai/sdk pg pino zod
pnpm add -D typescript @types/node @types/pg vitest @biomejs/biome esbuild tsx pino-pretty
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

**Step 4: Create biome.json**

```json
{
  "$schema": "https://biomejs.dev/schemas/2.4.2/schema.json",
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "style": {
        "noNonNullAssertion": "off"
      }
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "semicolons": "always"
    }
  },
  "files": {
    "includes": ["src/**", "tests/**", "scripts/**", "*.json", "*.ts"]
  }
}
```

**Step 5: Create scripts/build.ts**

```typescript
import { build } from "esbuild";

await build({
  entryPoints: ["src/index.ts"],
  bundle: true,
  platform: "node",
  target: "node20",
  format: "esm",
  outfile: "dist/index.js",
  sourcemap: true,
  packages: "external",
});

console.log("Build complete: dist/index.js");
```

**Step 6: Create package.json scripts**

Add to package.json:
```json
{
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsx scripts/build.ts",
    "start": "node dist/index.js",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "typecheck": "tsc --noEmit"
  }
}
```

**Step 7: Create Procfile**

```
web: node dist/index.js
```

**Step 8: Create .env.example**

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
ANTHROPIC_API_KEY=
RK_SKILL_ID=
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SONIOX_API_KEY=
NODE_ENV=development
```

**Step 9: Create .gitignore**

```
node_modules/
dist/
.env
*.log
```

**Step 10: Create src/index.ts placeholder**

```typescript
console.log("rk-bot starting...");
```

**Step 11: Verify setup compiles**

```bash
pnpm typecheck && pnpm lint
```

**Step 12: Commit**

```bash
git init
git add -A
git commit -m "chore: scaffold rk-bot project"
```

---

## Task 2: Logger & Config

**Files:**
- Create: `src/logger.ts`
- Create: `src/config.ts`
- Create: `tests/config.test.ts`

**Step 1: Write config test**

```typescript
// tests/config.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("loadConfig", () => {
  const VALID_ENV = {
    TELEGRAM_BOT_TOKEN: "test-token",
    TELEGRAM_WEBHOOK_SECRET: "test-secret",
    ANTHROPIC_API_KEY: "test-api-key",
    RK_SKILL_ID: "test-skill-id",
    DATABASE_URL: "postgresql://localhost/test",
    SONIOX_API_KEY: "test-soniox",
  };

  beforeEach(() => {
    vi.stubEnv("TELEGRAM_BOT_TOKEN", VALID_ENV.TELEGRAM_BOT_TOKEN);
    vi.stubEnv("TELEGRAM_WEBHOOK_SECRET", VALID_ENV.TELEGRAM_WEBHOOK_SECRET);
    vi.stubEnv("ANTHROPIC_API_KEY", VALID_ENV.ANTHROPIC_API_KEY);
    vi.stubEnv("RK_SKILL_ID", VALID_ENV.RK_SKILL_ID);
    vi.stubEnv("DATABASE_URL", VALID_ENV.DATABASE_URL);
    vi.stubEnv("SONIOX_API_KEY", VALID_ENV.SONIOX_API_KEY);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("loads valid config from environment", async () => {
    const { loadConfig } = await import("../src/config");
    const config = loadConfig();
    expect(config.TELEGRAM_BOT_TOKEN).toBe("test-token");
    expect(config.NODE_ENV).toBe("development");
  });

  it("throws on missing required var", async () => {
    vi.stubEnv("TELEGRAM_BOT_TOKEN", "");
    const { loadConfig } = await import("../src/config");
    expect(() => loadConfig()).toThrow();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/config.test.ts
```
Expected: FAIL

**Step 3: Implement logger**

```typescript
// src/logger.ts
import pino from "pino";

const isDev = process.env.NODE_ENV !== "production";
const level = process.env.LOG_LEVEL ?? (isDev ? "debug" : "info");

const logger = pino(
  isDev
    ? { level, transport: { target: "pino-pretty", options: { colorize: true } } }
    : { level },
);

export function createLogger(name: string) {
  return logger.child({ component: name });
}

export default logger;
```

**Step 4: Implement config**

```typescript
// src/config.ts
import { z } from "zod";

const envSchema = z.object({
  TELEGRAM_BOT_TOKEN: z.string().min(1),
  TELEGRAM_WEBHOOK_SECRET: z.string().min(1),
  ANTHROPIC_API_KEY: z.string().min(1),
  RK_SKILL_ID: z.string().min(1),
  DATABASE_URL: z.string().min(1),
  SONIOX_API_KEY: z.string().min(1),
  NODE_ENV: z.enum(["development", "production"]).default("development"),
});

export type Config = z.infer<typeof envSchema>;

export function loadConfig(): Config {
  return envSchema.parse(process.env);
}
```

**Step 5: Run tests**

```bash
pnpm test -- tests/config.test.ts
```
Expected: PASS

**Step 6: Commit**

```bash
git add src/logger.ts src/config.ts tests/config.test.ts
git commit -m "feat: add logger and config modules"
```

---

## Task 3: Database Client & Schema

**Files:**
- Create: `src/db/client.ts`
- Create: `tests/db.test.ts`

**Step 1: Write database test**

```typescript
// tests/db.test.ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import pg from "pg";

// These tests require TEST_DATABASE_URL env var pointing to a test PostgreSQL database.
// Skip if not available.
const TEST_DB_URL = process.env.TEST_DATABASE_URL;

describe.skipIf(!TEST_DB_URL)("database", () => {
  let pool: pg.Pool;

  beforeAll(async () => {
    const { createPool, runMigrations } = await import("../src/db/client");
    pool = createPool(TEST_DB_URL!);
    await runMigrations(pool);
  });

  afterAll(async () => {
    // Clean up tables
    await pool.query("DROP TABLE IF EXISTS message_registry, document_counters, conversations");
    await pool.end();
  });

  it("creates conversations table", async () => {
    const result = await pool.query(
      "SELECT column_name FROM information_schema.columns WHERE table_name = 'conversations' ORDER BY ordinal_position",
    );
    const columns = result.rows.map((r) => r.column_name);
    expect(columns).toContain("chat_id");
    expect(columns).toContain("root_message_id");
    expect(columns).toContain("session_state");
    expect(columns).toContain("doc_type");
    expect(columns).toContain("container_id");
    expect(columns).toContain("messages");
    expect(columns).toContain("last_activity");
  });

  it("creates message_registry table", async () => {
    const result = await pool.query(
      "SELECT column_name FROM information_schema.columns WHERE table_name = 'message_registry' ORDER BY ordinal_position",
    );
    const columns = result.rows.map((r) => r.column_name);
    expect(columns).toContain("chat_id");
    expect(columns).toContain("message_id");
    expect(columns).toContain("root_message_id");
  });

  it("creates document_counters table", async () => {
    const result = await pool.query(
      "SELECT column_name FROM information_schema.columns WHERE table_name = 'document_counters' ORDER BY ordinal_position",
    );
    const columns = result.rows.map((r) => r.column_name);
    expect(columns).toContain("doc_type");
    expect(columns).toContain("year");
    expect(columns).toContain("last_number");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/db.test.ts
```
Expected: FAIL (module not found)

**Step 3: Implement database client**

```typescript
// src/db/client.ts
import pg from "pg";
import { createLogger } from "../logger";

const log = createLogger("db");

export function createPool(databaseUrl: string): pg.Pool {
  return new pg.Pool({
    connectionString: databaseUrl,
    max: 4,
    idleTimeoutMillis: 30000,
  });
}

export async function runMigrations(pool: pg.Pool): Promise<void> {
  log.info("Running database migrations");

  await pool.query(`
    CREATE TABLE IF NOT EXISTS conversations (
      chat_id BIGINT NOT NULL,
      root_message_id BIGINT NOT NULL,
      session_state TEXT NOT NULL DEFAULT 'idle',
      doc_type TEXT,
      container_id TEXT,
      messages JSONB NOT NULL DEFAULT '[]',
      last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (chat_id, root_message_id)
    )
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS message_registry (
      chat_id BIGINT NOT NULL,
      message_id BIGINT NOT NULL,
      root_message_id BIGINT NOT NULL,
      PRIMARY KEY (chat_id, message_id)
    )
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS document_counters (
      doc_type TEXT NOT NULL,
      year INT NOT NULL,
      last_number INT NOT NULL DEFAULT 0,
      PRIMARY KEY (doc_type, year)
    )
  `);

  // Index for active session lookups
  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_conversations_active
    ON conversations (chat_id, last_activity DESC)
    WHERE session_state != 'idle'
  `);

  log.info("Migrations complete");
}
```

**Step 4: Run tests**

```bash
pnpm test -- tests/db.test.ts
```
Expected: PASS (or SKIP if no TEST_DATABASE_URL)

**Step 5: Commit**

```bash
git add src/db/client.ts tests/db.test.ts
git commit -m "feat: add PostgreSQL database client and schema migrations"
```

---

## Task 4: Session State Machine

**Files:**
- Create: `src/bot/session.ts`
- Create: `tests/session.test.ts`

**Step 1: Write session tests**

```typescript
// tests/session.test.ts
import { describe, it, expect } from "vitest";
import { transition, mapActionToState } from "../src/bot/session";

describe("transition", () => {
  it("allows idle → collecting", () => {
    expect(transition("idle", "collecting")).toBe("collecting");
  });

  it("allows collecting → confirming", () => {
    expect(transition("collecting", "confirming")).toBe("confirming");
  });

  it("allows collecting → generated", () => {
    expect(transition("collecting", "generated")).toBe("generated");
  });

  it("allows confirming → generated", () => {
    expect(transition("confirming", "generated")).toBe("generated");
  });

  it("allows generated → collecting (revision)", () => {
    expect(transition("generated", "collecting")).toBe("collecting");
  });

  it("allows any state → idle", () => {
    expect(transition("collecting", "idle")).toBe("idle");
    expect(transition("confirming", "idle")).toBe("idle");
    expect(transition("generated", "idle")).toBe("idle");
  });

  it("rejects idle → generated", () => {
    expect(() => transition("idle", "generated")).toThrow("Invalid transition");
  });

  it("rejects idle → confirming", () => {
    expect(() => transition("idle", "confirming")).toThrow("Invalid transition");
  });
});

describe("mapActionToState", () => {
  it("continue from idle → collecting", () => {
    expect(mapActionToState("continue", "idle")).toBe("collecting");
  });

  it("continue from collecting stays collecting", () => {
    expect(mapActionToState("continue", "collecting")).toBe("collecting");
  });

  it("confirm from collecting → confirming", () => {
    expect(mapActionToState("confirm", "collecting")).toBe("confirming");
  });

  it("generate from collecting → generated", () => {
    expect(mapActionToState("generate", "collecting")).toBe("generated");
  });

  it("generate from confirming → generated", () => {
    expect(mapActionToState("generate", "confirming")).toBe("generated");
  });

  it("new from any state → idle", () => {
    expect(mapActionToState("new", "collecting")).toBe("idle");
    expect(mapActionToState("new", "confirming")).toBe("idle");
    expect(mapActionToState("new", "generated")).toBe("idle");
  });

  it("invalid transition preserves current state", () => {
    expect(mapActionToState("confirm", "idle")).toBe("idle");
    expect(mapActionToState("generate", "idle")).toBe("idle");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/session.test.ts
```
Expected: FAIL

**Step 3: Implement session state machine**

```typescript
// src/bot/session.ts
export type SessionState = "idle" | "collecting" | "confirming" | "generated";

const VALID_TRANSITIONS: Record<SessionState, SessionState[]> = {
  idle: ["collecting"],
  collecting: ["confirming", "generated", "idle"],
  confirming: ["generated", "collecting", "idle"],
  generated: ["collecting", "idle"],
};

export function transition(current: SessionState, next: SessionState): SessionState {
  if (!VALID_TRANSITIONS[current].includes(next)) {
    throw new Error(`Invalid transition: ${current} → ${next}`);
  }
  return next;
}

export function mapActionToState(
  action: "continue" | "confirm" | "generate" | "new",
  current: SessionState,
): SessionState {
  const target = actionToTarget(action, current);
  if (!VALID_TRANSITIONS[current].includes(target)) {
    return current;
  }
  return target;
}

function actionToTarget(
  action: "continue" | "confirm" | "generate" | "new",
  current: SessionState,
): SessionState {
  switch (action) {
    case "continue":
      return current === "idle" ? "collecting" : current;
    case "confirm":
      return "confirming";
    case "generate":
      return "generated";
    case "new":
      return "idle";
  }
}
```

**Step 4: Run tests**

```bash
pnpm test -- tests/session.test.ts
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/session.ts tests/session.test.ts
git commit -m "feat: add session state machine with validated transitions"
```

---

## Task 5: Conversation Store

**Files:**
- Create: `src/services/conversation.ts`
- Create: `tests/conversation.test.ts`

**Step 1: Write conversation store tests**

```typescript
// tests/conversation.test.ts
import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import pg from "pg";

const TEST_DB_URL = process.env.TEST_DATABASE_URL;

describe.skipIf(!TEST_DB_URL)("ConversationStore", () => {
  let pool: pg.Pool;
  let store: InstanceType<typeof import("../src/services/conversation").ConversationStore>;

  beforeAll(async () => {
    const { createPool, runMigrations } = await import("../src/db/client");
    const { ConversationStore } = await import("../src/services/conversation");
    pool = createPool(TEST_DB_URL!);
    await runMigrations(pool);
    store = new ConversationStore(pool);
  });

  beforeEach(async () => {
    await pool.query("DELETE FROM message_registry");
    await pool.query("DELETE FROM conversations");
    await pool.query("DELETE FROM document_counters");
  });

  afterAll(async () => {
    await pool.query("DROP TABLE IF EXISTS message_registry, document_counters, conversations");
    await pool.end();
  });

  it("creates a new conversation", async () => {
    const conv = await store.getOrCreate(100, 1);
    expect(conv.messages).toEqual([]);
    expect(conv.sessionState).toBe("idle");
    expect(conv.containerId).toBeNull();
    expect(conv.docType).toBeNull();
  });

  it("loads existing conversation", async () => {
    const conv = await store.getOrCreate(100, 1);
    conv.messages.push({ role: "user", content: "hello" });
    conv.sessionState = "collecting";
    await store.save(100, 1, conv);

    const loaded = await store.getOrCreate(100, 1);
    expect(loaded.messages).toEqual([{ role: "user", content: "hello" }]);
    expect(loaded.sessionState).toBe("collecting");
  });

  it("finds active conversation for chat", async () => {
    const conv = await store.getOrCreate(100, 1);
    conv.sessionState = "collecting";
    await store.save(100, 1, conv);

    const active = await store.findActiveForChat(100);
    expect(active).not.toBeNull();
    expect(active!.rootMessageId).toBe(1);
    expect(active!.sessionState).toBe("collecting");
  });

  it("returns null when no active conversation", async () => {
    await store.getOrCreate(100, 1); // idle by default
    const active = await store.findActiveForChat(100);
    expect(active).toBeNull();
  });

  it("registers and finds message root", async () => {
    await store.registerMessage(100, 5, 1);
    const root = await store.findRoot(100, 5);
    expect(root).toBe(1);
  });

  it("returns null for unregistered message", async () => {
    const root = await store.findRoot(100, 999);
    expect(root).toBeNull();
  });

  it("increments document counter", async () => {
    const num1 = await store.nextDocumentNumber("COT", 2026);
    expect(num1).toBe("COT-2026-001");

    const num2 = await store.nextDocumentNumber("COT", 2026);
    expect(num2).toBe("COT-2026-002");

    const num3 = await store.nextDocumentNumber("PRES", 2026);
    expect(num3).toBe("PRES-2026-001");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/conversation.test.ts
```
Expected: FAIL

**Step 3: Implement conversation store**

```typescript
// src/services/conversation.ts
import type pg from "pg";
import type { SessionState } from "../bot/session";
import { createLogger } from "../logger";

const log = createLogger("conversation");

export interface Conversation {
  messages: Array<{ role: string; content: unknown }>;
  sessionState: SessionState;
  containerId: string | null;
  docType: string | null;
  lastActivity: Date;
}

export interface ActiveConversationRef {
  rootMessageId: number;
  sessionState: SessionState;
  docType: string | null;
  lastActivity: Date;
}

export class ConversationStore {
  constructor(private pool: pg.Pool) {}

  async getOrCreate(chatId: number, rootMessageId: number): Promise<Conversation> {
    const result = await this.pool.query(
      "SELECT messages, session_state, container_id, doc_type, last_activity FROM conversations WHERE chat_id = $1 AND root_message_id = $2",
      [chatId, rootMessageId],
    );

    if (result.rows.length > 0) {
      const r = result.rows[0];
      log.debug({ chatId, rootMessageId, state: r.session_state, docType: r.doc_type }, "Conversation loaded");
      return {
        messages: r.messages,
        sessionState: r.session_state as SessionState,
        containerId: r.container_id || null,
        docType: r.doc_type || null,
        lastActivity: r.last_activity,
      };
    }

    log.info({ chatId, rootMessageId }, "New conversation created");
    await this.pool.query(
      "INSERT INTO conversations (chat_id, root_message_id) VALUES ($1, $2)",
      [chatId, rootMessageId],
    );

    return {
      messages: [],
      sessionState: "idle",
      containerId: null,
      docType: null,
      lastActivity: new Date(),
    };
  }

  async findActiveForChat(chatId: number): Promise<ActiveConversationRef | null> {
    const result = await this.pool.query(
      `SELECT root_message_id, session_state, doc_type, last_activity
       FROM conversations
       WHERE chat_id = $1 AND session_state != 'idle'
       ORDER BY last_activity DESC
       LIMIT 1`,
      [chatId],
    );

    if (result.rows.length === 0) return null;
    const r = result.rows[0];
    return {
      rootMessageId: Number(r.root_message_id),
      sessionState: r.session_state as SessionState,
      docType: r.doc_type || null,
      lastActivity: r.last_activity,
    };
  }

  async save(chatId: number, rootMessageId: number, conv: Conversation): Promise<void> {
    log.debug({ chatId, rootMessageId, state: conv.sessionState, docType: conv.docType }, "Saving conversation");
    await this.pool.query(
      `UPDATE conversations
       SET messages = $1, session_state = $2, container_id = $3, doc_type = $4, last_activity = NOW()
       WHERE chat_id = $5 AND root_message_id = $6`,
      [JSON.stringify(conv.messages), conv.sessionState, conv.containerId, conv.docType, chatId, rootMessageId],
    );
  }

  async registerMessage(chatId: number, messageId: number, rootMessageId: number): Promise<void> {
    await this.pool.query(
      "INSERT INTO message_registry (chat_id, message_id, root_message_id) VALUES ($1, $2, $3) ON CONFLICT (chat_id, message_id) DO UPDATE SET root_message_id = $3",
      [chatId, messageId, rootMessageId],
    );
  }

  async findRoot(chatId: number, messageId: number): Promise<number | null> {
    const result = await this.pool.query(
      "SELECT root_message_id FROM message_registry WHERE chat_id = $1 AND message_id = $2",
      [chatId, messageId],
    );
    if (result.rows.length === 0) return null;
    return Number(result.rows[0].root_message_id);
  }

  async nextDocumentNumber(docType: string, year: number): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO document_counters (doc_type, year, last_number)
       VALUES ($1, $2, 1)
       ON CONFLICT (doc_type, year)
       DO UPDATE SET last_number = document_counters.last_number + 1
       RETURNING last_number`,
      [docType, year],
    );
    const num = result.rows[0].last_number;
    return `${docType}-${year}-${String(num).padStart(3, "0")}`;
  }

  async cleanup(ttlSeconds: number): Promise<void> {
    log.info({ ttlSeconds }, "Running conversation cleanup");
    await this.pool.query(
      `DELETE FROM message_registry WHERE (chat_id, root_message_id) IN (
        SELECT chat_id, root_message_id FROM conversations
        WHERE last_activity < NOW() - INTERVAL '1 second' * $1
      )`,
      [ttlSeconds],
    );
    await this.pool.query(
      "DELETE FROM conversations WHERE last_activity < NOW() - INTERVAL '1 second' * $1",
      [ttlSeconds],
    );
  }
}
```

**Step 4: Run tests**

```bash
pnpm test -- tests/conversation.test.ts
```
Expected: PASS (or SKIP if no TEST_DATABASE_URL)

**Step 5: Commit**

```bash
git add src/services/conversation.ts tests/conversation.test.ts
git commit -m "feat: add conversation store with active session lookup and doc counters"
```

---

## Task 6: Claude Client

**Files:**
- Create: `src/services/claude.ts`
- Create: `tests/claude.test.ts`

**Step 1: Write Claude client tests**

```typescript
// tests/claude.test.ts
import { describe, it, expect } from "vitest";
import { extractResponse, needsContinuation, RESPOND_TOOL } from "../src/services/claude";

describe("needsContinuation", () => {
  it("returns true for pause_turn", () => {
    expect(needsContinuation("pause_turn")).toBe(true);
  });

  it("returns false for end_turn", () => {
    expect(needsContinuation("end_turn")).toBe(false);
  });

  it("returns false for null", () => {
    expect(needsContinuation(null)).toBe(false);
  });
});

describe("extractResponse", () => {
  it("extracts respond tool call", () => {
    const content = [
      { type: "text", text: "Internal thinking..." },
      {
        type: "tool_use",
        name: "respond",
        input: { text: "Hello user", session_action: "continue" },
      },
    ];
    const result = extractResponse(content);
    expect(result.text).toBe("Hello user");
    expect(result.sessionAction).toBe("continue");
    expect(result.fileIds).toEqual([]);
  });

  it("extracts file IDs from code execution results", () => {
    const content = [
      {
        type: "bash_code_execution_tool_result",
        content: {
          type: "bash_code_execution_result",
          content: [{ file_id: "file-abc123" }, { file_id: "file-def456" }],
        },
      },
      {
        type: "tool_use",
        name: "respond",
        input: { text: "Here's your doc", session_action: "generate" },
      },
    ];
    const result = extractResponse(content);
    expect(result.fileIds).toEqual(["file-abc123", "file-def456"]);
    expect(result.sessionAction).toBe("generate");
  });

  it("falls back to last text block when no respond tool", () => {
    const content = [
      { type: "text", text: "Thinking about it..." },
      { type: "text", text: "Here is my answer" },
    ];
    const result = extractResponse(content);
    expect(result.text).toBe("Here is my answer");
    expect(result.sessionAction).toBe("continue");
  });

  it("returns empty text when no content", () => {
    const result = extractResponse([]);
    expect(result.text).toBe("");
    expect(result.sessionAction).toBe("continue");
  });

  it("has correct respond tool schema", () => {
    expect(RESPOND_TOOL.name).toBe("respond");
    expect(RESPOND_TOOL.input_schema.required).toContain("text");
    expect(RESPOND_TOOL.input_schema.required).toContain("session_action");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/claude.test.ts
```
Expected: FAIL

**Step 3: Implement Claude client**

```typescript
// src/services/claude.ts
import Anthropic from "@anthropic-ai/sdk";
import { createLogger } from "../logger";

const log = createLogger("claude");
const BETAS = ["code-execution-2025-08-25", "skills-2025-10-02"];
const MAX_CONTINUATIONS = 10;

export const RESPOND_TOOL = {
  name: "respond",
  description:
    "Send your response to the user. Always call this tool with your message and the appropriate session action.",
  input_schema: {
    type: "object" as const,
    properties: {
      text: { type: "string", description: "Message to show the user in Telegram" },
      session_action: {
        type: "string",
        enum: ["continue", "confirm", "generate", "new"],
        description: "What state the session should transition to",
      },
      doc_type: {
        type: "string",
        description: "Inferred document type code, e.g. COT, PRES, REC, CARTA, or any free-form type",
      },
      doc_data: {
        type: "object",
        description: "Document metadata when generating",
        properties: {
          title: { type: "string" },
          clientName: { type: "string" },
        },
      },
      pending_question: {
        type: "string",
        description: "Set when asking a question that needs special UI (reserved for future use)",
      },
    },
    required: ["text", "session_action"],
    additionalProperties: false,
  },
};

export interface ClaudeResponse {
  text: string;
  sessionAction: "continue" | "confirm" | "generate" | "new";
  fileIds: string[];
  containerId: string | null;
  docType?: string;
  docData?: Record<string, unknown>;
  pendingQuestion?: string;
}

const TOOLS = [
  { type: "code_execution_20250825" as const, name: "code_execution" as const },
  {
    ...(RESPOND_TOOL as unknown as Anthropic.Beta.BetaToolUnion),
    cache_control: { type: "ephemeral" as const },
  },
] as Anthropic.Beta.BetaToolUnion[];

export function needsContinuation(stopReason: string | null): boolean {
  return stopReason === "pause_turn";
}

export function extractResponse(content: unknown[]): ClaudeResponse {
  const fileIds: string[] = [];
  let text = "";
  let sessionAction: ClaudeResponse["sessionAction"] = "continue";
  let docType: string | undefined;
  let docData: Record<string, unknown> | undefined;
  let pendingQuestion: string | undefined;

  for (const block of content as Array<Record<string, unknown>>) {
    if (block.type === "bash_code_execution_tool_result") {
      const result = block.content as Record<string, unknown>;
      if (result.type === "bash_code_execution_result" && Array.isArray(result.content)) {
        for (const file of result.content) {
          if ((file as Record<string, unknown>).file_id) {
            fileIds.push((file as Record<string, unknown>).file_id as string);
          }
        }
      }
    }

    if (block.type === "tool_use" && block.name === "respond") {
      const input = block.input as Record<string, unknown>;
      text = input.text as string;
      sessionAction = input.session_action as ClaudeResponse["sessionAction"];
      if (input.doc_type) docType = input.doc_type as string;
      if (input.doc_data) docData = input.doc_data as Record<string, unknown>;
      if (input.pending_question) pendingQuestion = input.pending_question as string;
    }
  }

  if (!text) {
    const textBlocks = (content as Array<Record<string, unknown>>)
      .filter((b) => b.type === "text")
      .map((b) => b.text as string);
    text = textBlocks.length > 0 ? textBlocks[textBlocks.length - 1] : "";
  }

  return { text, sessionAction, fileIds, containerId: null, docType, docData, pendingQuestion };
}

const SYSTEM_PROMPT = `Eres el asistente de documentos de RK ArtSide SRL. Generas documentos profesionales usando HTML y WeasyPrint.

## Comportamiento

1. Si tienes toda la información, genera el documento inmediatamente
2. Solo pregunta si hay ambigüedad real
3. Sé breve - es Telegram
4. SIEMPRE usa la herramienta "respond" para enviar tu respuesta
5. NO preguntes sobre ITBIS a menos que el usuario lo mencione explícitamente

## session_action values

- "continue": Necesitas más información del usuario
- "confirm": Tienes todos los datos y quieres que el usuario revise un resumen antes de generar. Usa esto solo para documentos complejos (3+ items o detalles ambiguos).
- "generate": Tienes todos los datos — genera el PDF AHORA usando code_execution, luego llama respond. CRÍTICO: DEBES ejecutar código para crear el documento ANTES de llamar respond con "generate".
- "new": El usuario está empezando una solicitud completamente nueva

IMPORTANTE: Cuando tengas todos los campos requeridos, prefiere "generate" sobre "confirm". Solo usa "confirm" cuando el documento sea lo suficientemente complejo para que un paso de revisión agregue valor.

CRÍTICO: La acción "generate" significa que DEBES ejecutar code_execution para producir el PDF en el MISMO turno. La secuencia correcta es: (1) escribir HTML, (2) convertir a PDF con WeasyPrint, (3) verificar que el PDF existe, (4) ENTONCES llamar respond con session_action "generate".

## Formato de respuesta

- Tus respuestas se envían por Telegram con Markdown.
- Usa saltos de línea reales, NUNCA uses "\\n" literal.
- No uses encabezados (#), tablas, ni bloques de código. Listas con - o • están bien.
- Negrita: *texto*. Cursiva: _texto_.
- Sé conciso — es un chat, no un documento.

## Cálculos

- Siempre verifica la aritmética antes de generar: subtotales y totales deben cuadrar.
- Usa code_execution para validar los cálculos si hay 2+ items.

## Notas

- Moneda: RD$ (Pesos Dominicanos)
- ITBIS (18%): Solo calcular si el usuario lo pide explícitamente. Por defecto, no incluir ITBIS.`;

export class ClaudeClient {
  private client: Anthropic;

  constructor(apiKey: string) {
    this.client = new Anthropic({ apiKey });
  }

  async sendMessage(
    messages: Array<{ role: string; content: unknown }>,
    skillId: string,
    systemExtra: string = "",
    containerId?: string,
  ): Promise<ClaudeResponse> {
    const system: Anthropic.Beta.BetaTextBlockParam[] = [
      { type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
    ];
    if (systemExtra) {
      system.push({ type: "text", text: systemExtra });
    }

    const container: Record<string, unknown> = {
      skills: [{ type: "custom", skill_id: skillId, version: "latest" }],
    };
    if (containerId) {
      container.id = containerId;
    }

    log.debug({ messageCount: messages.length, skillId, containerId }, "Sending Claude API request");

    let response = await this.client.beta.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 4096,
      betas: BETAS,
      system,
      container,
      messages: messages as Anthropic.Beta.BetaMessageParam[],
      tools: TOOLS,
    });

    const allContent: unknown[] = [...(response.content as unknown[])];
    let currentMessages = [...messages];
    let continuations = 0;

    for (let i = 0; i < MAX_CONTINUATIONS; i++) {
      if (!needsContinuation(response.stop_reason)) break;
      continuations++;
      log.debug({ continuation: continuations }, "Claude pause_turn continuation");

      currentMessages = [...currentMessages, { role: "assistant", content: response.content }];

      response = await this.client.beta.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 4096,
        betas: BETAS,
        system,
        container: { id: response.container?.id, ...container },
        messages: currentMessages as Anthropic.Beta.BetaMessageParam[],
        tools: TOOLS,
      });
      allContent.push(...(response.content as unknown[]));
    }

    const result = extractResponse(allContent);
    result.containerId = response.container?.id ?? null;
    const usage = response.usage as unknown as Record<string, number> | undefined;
    log.info(
      {
        action: result.sessionAction,
        fileCount: result.fileIds.length,
        continuations,
        containerId: result.containerId,
        inputTokens: usage?.input_tokens,
        cacheRead: usage?.cache_read_input_tokens,
        cacheCreation: usage?.cache_creation_input_tokens,
      },
      "Claude response received",
    );
    return result;
  }

  async downloadFile(fileId: string): Promise<{ filename: string; data: Buffer }> {
    log.debug({ fileId }, "Downloading file from Claude");
    const metadata = await this.client.beta.files.retrieveMetadata(fileId, {
      betas: ["files-api-2025-04-14"],
    });
    const content = await this.client.beta.files.download(fileId, {
      betas: ["files-api-2025-04-14"],
    });
    const data = Buffer.from(await content.arrayBuffer());
    log.debug({ fileId, filename: metadata.filename, size: data.length }, "File downloaded");
    return { filename: metadata.filename, data };
  }
}
```

**Step 4: Run tests**

```bash
pnpm test -- tests/claude.test.ts
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/claude.ts tests/claude.test.ts
git commit -m "feat: add Claude client with respond tool, pause-turn loop, and file download"
```

---

## Task 7: Transcriber Service

**Files:**
- Create: `src/services/transcriber.ts`

**Step 1: Implement transcriber**

Port from docuexpress's `src/bot/voice.ts` pattern, adapted for the Soniox Node SDK.

```typescript
// src/services/transcriber.ts
import { createLogger } from "../logger";

const log = createLogger("transcriber");

export async function transcribeVoice(
  botToken: string,
  sonioxApiKey: string,
  fileId: string,
): Promise<string | null> {
  // Get file path from Telegram
  const fileRes = await fetch(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`);
  const fileData = (await fileRes.json()) as { result?: { file_path?: string } };
  const filePath = fileData.result?.file_path;
  if (!filePath) {
    log.error({ fileId }, "Could not get file path from Telegram");
    return null;
  }

  // Download audio
  const audioRes = await fetch(`https://api.telegram.org/file/bot${botToken}/${filePath}`);
  const audioBuffer = Buffer.from(await audioRes.arrayBuffer());
  log.debug({ fileId, size: audioBuffer.length }, "Audio downloaded from Telegram");

  // Transcribe with Soniox
  const { SonioxClient } = await import("@soniox/node");
  const soniox = new SonioxClient({ apiKey: sonioxApiKey });

  const uploadRes = await soniox.files.upload(new File([audioBuffer], "voice.ogg", { type: "audio/ogg" }));

  const transcription = await soniox.transcriptions.transcribe({
    file_id: uploadRes.id,
    model: "stt-async-v4",
    language_hints: ["es", "en"],
  });

  // Clean up
  await soniox.files.delete(uploadRes.id).catch((err: unknown) => {
    log.warn({ err, fileId: uploadRes.id }, "Failed to delete Soniox file");
  });

  const text = transcription.text?.trim();
  if (!text) {
    log.warn({ fileId }, "Empty transcription result");
    return null;
  }

  log.debug({ fileId, transcript: text.slice(0, 200) }, "Transcription complete");
  return text;
}
```

**Note:** The exact Soniox SDK API may differ — adjust method names when implementing. The structure above follows the pattern from rk-telegram-tools's `transcriber.py`.

**Step 2: Commit**

```bash
git add src/services/transcriber.ts
git commit -m "feat: add Soniox voice transcription service"
```

---

## Task 8: Message Handler & Routing

**Files:**
- Create: `src/bot/handler.ts`
- Create: `tests/handler.test.ts`

**Step 1: Write handler utility tests**

```typescript
// tests/handler.test.ts
import { describe, it, expect } from "vitest";
import {
  isBotMentioned,
  extractUserText,
  inferDocType,
  isStale,
  getQuickReply,
} from "../src/bot/handler";

describe("isBotMentioned", () => {
  it("detects @mention by username", () => {
    const msg = {
      text: "@rkbot cotización para Juan",
      entities: [{ type: "mention", offset: 0, length: 6 }],
    };
    expect(isBotMentioned(msg, 123, "rkbot")).toBe(true);
  });

  it("detects text_mention by user ID", () => {
    const msg = {
      text: "RK Bot cotización para Juan",
      entities: [{ type: "text_mention", offset: 0, length: 6, user: { id: 123 } }],
    };
    expect(isBotMentioned(msg, 123, "rkbot")).toBe(true);
  });

  it("returns false when not mentioned", () => {
    const msg = { text: "hello world", entities: [] };
    expect(isBotMentioned(msg, 123, "rkbot")).toBe(false);
  });

  it("returns false with no entities", () => {
    const msg = { text: "hello" };
    expect(isBotMentioned(msg, 123, "rkbot")).toBe(false);
  });
});

describe("extractUserText", () => {
  it("removes @mention from text", () => {
    const msg = {
      text: "@rkbot cotización para Juan",
      entities: [{ type: "mention", offset: 0, length: 6 }],
    };
    expect(extractUserText(msg, 123, "rkbot")).toBe("cotización para Juan");
  });

  it("returns full text when no mention", () => {
    const msg = { text: "cotización para Juan" };
    expect(extractUserText(msg, 123, "rkbot")).toBe("cotización para Juan");
  });
});

describe("inferDocType", () => {
  it("detects cotización", () => {
    expect(inferDocType("cotización para Juan")).toBe("COT");
    expect(inferDocType("hazme una cotizacion")).toBe("COT");
  });

  it("detects presupuesto", () => {
    expect(inferDocType("presupuesto de diseño")).toBe("PRES");
  });

  it("detects recibo", () => {
    expect(inferDocType("recibo de pago")).toBe("REC");
  });

  it("detects carta de compromiso", () => {
    expect(inferDocType("carta de compromiso")).toBe("CARTA");
  });

  it("returns null for unknown", () => {
    expect(inferDocType("hello world")).toBeNull();
  });
});

describe("isStale", () => {
  it("returns true for old timestamps", () => {
    const old = new Date(Date.now() - 20 * 60 * 1000); // 20 min ago
    expect(isStale(old)).toBe(true);
  });

  it("returns false for recent timestamps", () => {
    const recent = new Date(Date.now() - 5 * 60 * 1000); // 5 min ago
    expect(isStale(recent)).toBe(false);
  });
});

describe("getQuickReply", () => {
  it("returns reply for greetings", () => {
    expect(getQuickReply("hola")).toContain("Hola");
    expect(getQuickReply("¡Hola!")).toContain("Hola");
  });

  it("returns reply for thanks", () => {
    expect(getQuickReply("gracias")).toContain("De nada");
  });

  it("returns null for long messages", () => {
    expect(getQuickReply("quiero una cotización para muebles de sala")).toBeNull();
  });

  it("returns null for unknown short messages", () => {
    expect(getQuickReply("mesa")).toBeNull();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
pnpm test -- tests/handler.test.ts
```
Expected: FAIL

**Step 3: Implement handler**

```typescript
// src/bot/handler.ts
import type { Bot } from "grammy";
import { InputFile } from "grammy";
import type { Config } from "../config";
import { createLogger } from "../logger";
import type { ClaudeClient, ClaudeResponse } from "../services/claude";
import type { Conversation, ConversationStore } from "../services/conversation";
import { transcribeVoice } from "../services/transcriber";
import { mapActionToState } from "./session";

const log = createLogger("handler");

const SESSION_TIMEOUT_MS = 15 * 60 * 1000;

const DOC_TYPE_KEYWORDS: Record<string, string[]> = {
  COT: ["cotizaci", "cotización"],
  PRES: ["presupuest"],
  REC: ["recibo"],
  CARTA: ["carta", "compromiso"],
};

const QUICK_REPLIES: Record<string, string> = {
  hola: "👋 ¡Hola! Cuéntame qué documento necesitas, o escribe /nuevo.",
  hello: "👋 ¡Hola! Cuéntame qué documento necesitas, o escribe /nuevo.",
  buenas: "👋 ¡Hola! Cuéntame qué documento necesitas, o escribe /nuevo.",
  "buenos dias": "👋 ¡Buenos días! Cuéntame qué documento necesitas.",
  "buenas tardes": "👋 ¡Buenas tardes! Cuéntame qué documento necesitas.",
  "buenas noches": "👋 ¡Buenas noches! Cuéntame qué documento necesitas.",
  gracias: "👍 ¡De nada! Si necesitas otro documento, escríbeme.",
  "muchas gracias": "👍 ¡De nada! Si necesitas otro documento, escríbeme.",
  ok: "👍 Si necesitas algo más, escríbeme.",
};

const QUICK_REPLY_MAX_WORDS = 3;

export function isStale(lastActivity: Date): boolean {
  return Date.now() - lastActivity.getTime() > SESSION_TIMEOUT_MS;
}

export function getQuickReply(text: string): string | null {
  const normalized = text.toLowerCase().replace(/[¡!¿?.,:;]/g, "").trim();
  if (normalized.split(/\s+/).length > QUICK_REPLY_MAX_WORDS) return null;
  return QUICK_REPLIES[normalized] ?? null;
}

export function inferDocType(text: string): string | null {
  const lower = text.toLowerCase();
  for (const [docType, keywords] of Object.entries(DOC_TYPE_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return docType;
  }
  return null;
}

export function isBotMentioned(
  message: {
    text?: string;
    entities?: Array<{ type: string; offset: number; length: number; user?: { id: number } }>;
  },
  botId: number,
  botUsername: string,
): boolean {
  if (!message.entities || !message.text) return false;
  const lower = botUsername.toLowerCase();
  for (const e of message.entities) {
    if (e.type === "text_mention" && e.user?.id === botId) return true;
    if (e.type === "mention") {
      const mention = message.text.slice(e.offset, e.offset + e.length).toLowerCase();
      if (mention === `@${lower}`) return true;
    }
  }
  return false;
}

export function extractUserText(
  message: {
    text?: string;
    entities?: Array<{ type: string; offset: number; length: number; user?: { id: number } }>;
  },
  botId: number,
  botUsername: string,
): string {
  let text = message.text || "";
  const lower = botUsername.toLowerCase();
  if (message.entities) {
    for (const e of [...message.entities].reverse()) {
      let isBot = false;
      if (e.type === "text_mention" && e.user?.id === botId) isBot = true;
      if (e.type === "mention") {
        const mention = text.slice(e.offset, e.offset + e.length).toLowerCase();
        if (mention === `@${lower}`) isBot = true;
      }
      if (isBot) {
        text = text.slice(0, e.offset) + text.slice(e.offset + e.length);
      }
    }
  }
  return text.trim();
}

export function registerHandlers(
  bot: Bot,
  conversationStore: ConversationStore,
  claudeClient: ClaudeClient,
  config: Config,
): void {
  const voiceReminded = new Set<number>();

  // Handle voice messages
  bot.on("message:voice", async (ctx) => {
    const chatId = ctx.chat.id;
    const msg = ctx.message;
    const botUser = ctx.me;
    log.debug({ chatId, msgId: msg.message_id }, "Voice message received");

    const isReplyToBot = msg.reply_to_message?.from?.id === botUser.id;
    const active = !isReplyToBot ? await conversationStore.findActiveForChat(chatId) : null;

    if (!isReplyToBot && !active) {
      if (!voiceReminded.has(chatId)) {
        voiceReminded.add(chatId);
        await ctx.reply(
          "Para que pueda escuchar tu nota de voz, responde directamente a uno de mis mensajes.",
          { reply_to_message_id: msg.message_id },
        );
      }
      return;
    }

    let rootId: number;
    if (active) {
      rootId = active.rootMessageId;
    } else {
      const repliedToId = msg.reply_to_message?.message_id;
      const found = repliedToId ? await conversationStore.findRoot(chatId, repliedToId) : null;
      rootId = found ?? repliedToId ?? msg.message_id;
    }

    await conversationStore.registerMessage(chatId, msg.message_id, rootId);

    const statusMsg = await ctx.reply("🎤 Transcribiendo audio...", {
      reply_to_message_id: msg.message_id,
    });

    let transcript: string | null = null;
    try {
      transcript = await transcribeVoice(
        config.TELEGRAM_BOT_TOKEN,
        config.SONIOX_API_KEY,
        msg.voice.file_id,
      );
    } catch (err) {
      log.error({ err, chatId }, "Voice transcription failed");
      await ctx.api.deleteMessage(chatId, statusMsg.message_id);
      await ctx.reply("❌ No pude transcribir el audio. Intenta de nuevo.", {
        reply_to_message_id: msg.message_id,
      });
      return;
    }

    await ctx.api.deleteMessage(chatId, statusMsg.message_id);

    if (!transcript) {
      await ctx.reply("❌ No pude entender el audio. Intenta de nuevo o escribe tu mensaje.", {
        reply_to_message_id: msg.message_id,
      });
      return;
    }

    await processMessage(ctx, chatId, rootId, msg.message_id, transcript, conversationStore, claudeClient, config);
  });

  // Handle text messages
  bot.on("message:text", async (ctx) => {
    const msg = ctx.message;
    const chatId = ctx.chat.id;
    const botUser = ctx.me;

    voiceReminded.delete(chatId);

    const isReplyToBot = msg.reply_to_message?.from?.id === botUser.id;
    const mentioned = isBotMentioned(msg, botUser.id, botUser.username ?? "");

    // In groups, require mention or reply
    if (!isReplyToBot && !mentioned) return;

    log.debug(
      { chatId, msgId: msg.message_id, isReplyToBot, mentioned, text: msg.text?.slice(0, 200) },
      "User message received",
    );

    // Determine root message ID
    let rootId: number;
    if (msg.reply_to_message) {
      const repliedToId = msg.reply_to_message.message_id;
      const found = await conversationStore.findRoot(chatId, repliedToId);
      rootId = found ?? repliedToId;
    } else if (mentioned) {
      // New @mention: check for active session first
      const active = await conversationStore.findActiveForChat(chatId);
      rootId = active ? active.rootMessageId : msg.message_id;
    } else {
      rootId = msg.message_id;
    }

    await conversationStore.registerMessage(chatId, msg.message_id, rootId);

    const userText = extractUserText(msg, botUser.id, botUser.username ?? "");
    if (!userText) return;

    await processMessage(ctx, chatId, rootId, msg.message_id, userText, conversationStore, claudeClient, config);
  });
}

export async function processMessage(
  // biome-ignore lint/complexity/noBannedTypes: Grammy context duck-typing
  ctx: { reply: Function; api: { deleteMessage: Function; sendDocument: Function } },
  chatId: number,
  rootId: number,
  replyToMsgId: number,
  userText: string,
  conversationStore: ConversationStore,
  claudeClient: ClaudeClient,
  config: Config,
): Promise<void> {
  log.info({ chatId, rootId }, "Processing message");

  // Quick reply shortcut when no active session
  const activeConv = await conversationStore.findActiveForChat(chatId);
  const quickReply = !activeConv ? getQuickReply(userText) : null;
  if (quickReply) {
    log.info({ chatId, userText }, "Quick reply (skipping Claude)");
    await ctx.reply(quickReply, { reply_to_message_id: replyToMsgId });
    return;
  }

  const conv: Conversation = await conversationStore.getOrCreate(chatId, rootId);

  // Stale session check
  if (conv.sessionState !== "idle" && isStale(conv.lastActivity)) {
    log.info({ chatId, rootId, state: conv.sessionState }, "Stale session detected");
    await ctx.reply(
      "Tienes un documento pendiente. ¿Continúas donde lo dejaste o empiezas de nuevo?\n\nEscribe /nuevo para empezar de cero.",
      { reply_to_message_id: replyToMsgId },
    );
    return;
  }

  // Build per-turn system context
  const year = new Date().getFullYear();
  const docType = inferDocType(userText) ?? conv.docType;
  let systemExtra = "";

  // Company info (always injected)
  systemExtra += `\n\n## Datos de la empresa
- Nombre: RK ArtSide SRL
- RNC: 1-33-51750-7
- Email: rkartside@gmail.com
- Teléfono: 809 645 7575
- Contacto: Reyka Kawashiro
- Ubicación: Santiago, R.D.
- Moneda: RD$ (Pesos Dominicanos)

Usa estos datos en los documentos.`;

  if (docType) {
    if (!conv.docType) conv.docType = docType;
    const docNum = await conversationStore.nextDocumentNumber(docType, year);
    systemExtra += `\n\n## Documento en curso\nTipo: ${docType}. Número: ${docNum}.`;
  }

  systemExtra += `\n\n## Estado de sesión actual\nEstado: ${conv.sessionState}. Si el usuario está claramente empezando una solicitud completamente nueva, responde con session_action "new".`;

  conv.messages.push({ role: "user", content: userText });

  const statusMsg = await ctx.reply("⏳ Procesando...", { reply_to_message_id: replyToMsgId });

  let result: ClaudeResponse;
  try {
    result = await claudeClient.sendMessage(
      conv.messages,
      config.RK_SKILL_ID,
      systemExtra,
      conv.containerId ?? undefined,
    );
  } catch (err) {
    log.error({ err, chatId, rootId }, "Claude API call failed");
    await ctx.api.deleteMessage(chatId, statusMsg.message_id);
    await ctx.reply("❌ Error generando el documento. Intenta de nuevo.", {
      reply_to_message_id: replyToMsgId,
    });
    conv.messages.pop();
    await conversationStore.save(chatId, rootId, conv);
    return;
  }

  await ctx.api.deleteMessage(chatId, statusMsg.message_id);

  conv.containerId = result.containerId;
  conv.messages.push({ role: "assistant", content: result.text });

  // Guard: if "generate" but no files, downgrade to "continue"
  const effectiveAction =
    result.sessionAction === "generate" && result.fileIds.length === 0
      ? "continue"
      : result.sessionAction;

  if (effectiveAction !== result.sessionAction) {
    log.warn({ chatId, rootId, originalAction: result.sessionAction }, "Generate with no files — downgrading to continue");
  }

  const newState = mapActionToState(effectiveAction, conv.sessionState);
  log.info({ chatId, rootId, action: effectiveAction, from: conv.sessionState, to: newState, fileCount: result.fileIds.length }, "State transition");
  conv.sessionState = newState;

  // Update doc type from Claude if provided
  if (result.docType && !conv.docType) {
    conv.docType = result.docType;
  }

  await conversationStore.save(chatId, rootId, conv);

  // Send response text
  const hasFiles = result.fileIds.length > 0;
  const canUseCaption = hasFiles && result.text && result.text.length <= 1024;

  if (result.text && (!hasFiles || !canUseCaption)) {
    const botMsg = await ctx.reply(result.text, {
      reply_to_message_id: replyToMsgId,
      parse_mode: "Markdown",
    });
    await conversationStore.registerMessage(chatId, botMsg.message_id, rootId);
  }

  // Send generated files
  for (let i = 0; i < result.fileIds.length; i++) {
    const fileId = result.fileIds[i];
    try {
      const { filename, data } = await claudeClient.downloadFile(fileId);
      log.info({ chatId, rootId, filename, size: data.length }, "Sending document");
      const docMsg = await ctx.api.sendDocument(
        chatId,
        new InputFile(new Uint8Array(data), filename),
        {
          reply_to_message_id: replyToMsgId,
          ...(canUseCaption && i === 0 ? { caption: result.text, parse_mode: "Markdown" as const } : {}),
        },
      );
      await conversationStore.registerMessage(chatId, docMsg.message_id, rootId);
    } catch (err) {
      log.error({ err, chatId, rootId, fileId }, "Failed to send document");
    }
  }
}
```

**Step 4: Run tests**

```bash
pnpm test -- tests/handler.test.ts
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot/handler.ts tests/handler.test.ts
git commit -m "feat: add message handler with routing, active session attachment, and processMessage flow"
```

---

## Task 9: Bot Commands

**Files:**
- Create: `src/bot/commands.ts`

**Step 1: Implement commands**

```typescript
// src/bot/commands.ts
import type { Bot } from "grammy";
import { createLogger } from "../logger";
import type { ConversationStore } from "../services/conversation";

const log = createLogger("commands");

export function registerCommands(bot: Bot, conversationStore: ConversationStore): void {
  bot.command("nuevo", async (ctx) => {
    const chatId = ctx.chat.id;
    log.info({ chatId }, "/nuevo command");

    const active = await conversationStore.findActiveForChat(chatId);
    if (active) {
      // Reset active conversation to idle
      const conv = await conversationStore.getOrCreate(chatId, active.rootMessageId);
      conv.sessionState = "idle";
      await conversationStore.save(chatId, active.rootMessageId, conv);
    }

    await ctx.reply("🆕 ¡Listo! Cuéntame qué documento necesitas.");
  });

  bot.command("cancelar", async (ctx) => {
    const chatId = ctx.chat.id;
    log.info({ chatId }, "/cancelar command");

    const active = await conversationStore.findActiveForChat(chatId);
    if (!active) {
      await ctx.reply("No hay ningún documento en proceso.");
      return;
    }

    const conv = await conversationStore.getOrCreate(chatId, active.rootMessageId);
    conv.sessionState = "idle";
    await conversationStore.save(chatId, active.rootMessageId, conv);
    await ctx.reply("❌ Documento cancelado.");
  });

  bot.command("ayuda", async (ctx) => {
    await ctx.reply(
      `*Comandos disponibles:*

/nuevo — Empezar un nuevo documento
/cancelar — Cancelar el documento actual
/ayuda — Ver esta ayuda

*Para crear un documento:*
Mencióneme con @nombre y dígame qué necesita. Ejemplo:
"@rkbot cotización para Juan, mesa de centro RD$15,000"

También puede responder a mis mensajes para continuar la conversación.`,
      { parse_mode: "Markdown" },
    );
  });
}
```

**Step 2: Commit**

```bash
git add src/bot/commands.ts
git commit -m "feat: add /nuevo, /cancelar, /ayuda bot commands"
```

---

## Task 10: Webhook Server & Entry Point

**Files:**
- Create: `src/app.ts`
- Modify: `src/index.ts`

**Step 1: Implement webhook app**

```typescript
// src/app.ts
import type { Update } from "grammy/types";
import { Hono } from "hono";
import { createLogger } from "./logger";

const log = createLogger("server");

interface AppDeps {
  bot: { handleUpdate(update: Update): Promise<void> };
  webhookSecret: string;
}

export function createWebhookApp(deps: AppDeps) {
  const inflight = new Set<Promise<void>>();
  let shuttingDown = false;

  const app = new Hono();

  app.get("/health", (c) => {
    if (shuttingDown) return c.json({ status: "shutting_down" }, 503);
    return c.json({ status: "ok" });
  });

  app.post("/webhook", async (c) => {
    if (shuttingDown) return c.json({ error: "Shutting down" }, 503);

    const secret = c.req.header("X-Telegram-Bot-Api-Secret-Token");
    if (secret !== deps.webhookSecret) {
      log.warn("Webhook request with invalid secret");
      return c.json({ error: "Unauthorized" }, 401);
    }

    const update = await c.req.json<Update>();
    log.debug({ updateId: update.update_id }, "Webhook update received");

    const task = deps.bot
      .handleUpdate(update)
      .catch((err) => {
        log.error({ err, updateId: update.update_id }, "Update processing failed");
      })
      .finally(() => {
        inflight.delete(task);
      });
    inflight.add(task);

    return c.json({ ok: true });
  });

  return {
    app,
    drain: async (timeoutMs = 30_000) => {
      if (inflight.size === 0) return;
      const drain = Promise.allSettled([...inflight]);
      const timeout = new Promise<void>((resolve) => setTimeout(resolve, timeoutMs));
      await Promise.race([drain, timeout]);
    },
    beginShutdown: () => { shuttingDown = true; },
  };
}
```

**Step 2: Implement index.ts (entry point)**

```typescript
// src/index.ts
import { serve } from "@hono/node-server";
import { Bot } from "grammy";
import { createWebhookApp } from "./app";
import { registerCommands } from "./bot/commands";
import { registerHandlers } from "./bot/handler";
import { loadConfig } from "./config";
import { createPool, runMigrations } from "./db/client";
import { createLogger } from "./logger";
import { ClaudeClient } from "./services/claude";
import { ConversationStore } from "./services/conversation";

const log = createLogger("server");
const config = loadConfig();

// Initialize services
const pool = createPool(config.DATABASE_URL);
const conversationStore = new ConversationStore(pool);
const claudeClient = new ClaudeClient(config.ANTHROPIC_API_KEY);

// Initialize Grammy bot
const bot = new Bot(config.TELEGRAM_BOT_TOKEN);

// Log all incoming updates
const botLog = createLogger("bot");
bot.use(async (ctx, next) => {
  const msg = ctx.message ?? ctx.callbackQuery?.message;
  botLog.info(
    {
      updateId: ctx.update.update_id,
      chatId: msg?.chat?.id,
      from: ctx.from?.username ?? ctx.from?.id,
      text: ctx.message?.text?.slice(0, 100),
      voice: !!ctx.message?.voice,
    },
    "Update received",
  );
  await next();
});

// Register handlers
registerCommands(bot, conversationStore);
registerHandlers(bot, conversationStore, claudeClient, config);

// Create webhook app
const { app, drain, beginShutdown } = createWebhookApp({
  bot,
  webhookSecret: config.TELEGRAM_WEBHOOK_SECRET,
});

const CLEANUP_TTL_SECONDS = 86400;
const CLEANUP_INTERVAL_MS = 60 * 60 * 1000;

async function main() {
  await runMigrations(pool);
  await conversationStore.cleanup(CLEANUP_TTL_SECONDS);

  const cleanupTimer = setInterval(() => {
    conversationStore.cleanup(CLEANUP_TTL_SECONDS).catch((err) => {
      log.error({ err }, "Cleanup failed");
    });
  }, CLEANUP_INTERVAL_MS);

  await bot.init();

  const port = parseInt(process.env.PORT || "8000", 10);
  log.info({ port, env: config.NODE_ENV }, "RK Bot starting");

  const server = serve({ fetch: app.fetch, port });

  async function shutdown(signal: string) {
    log.info({ signal }, "Shutdown signal received, draining...");
    beginShutdown();
    clearInterval(cleanupTimer);
    server.close();
    await drain();
    await pool.end();
    log.info("Shutdown complete");
    process.exit(0);
  }

  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));
}

main().catch((err) => {
  log.fatal({ err }, "Startup failed");
  process.exit(1);
});
```

**Step 3: Verify typecheck**

```bash
pnpm typecheck
```
Expected: PASS (may need minor type fixes)

**Step 4: Commit**

```bash
git add src/app.ts src/index.ts
git commit -m "feat: add Hono webhook server and application entry point"
```

---

## Task 11: RK ArtSide Skill (HTML→PDF)

**Files:**
- Create: `rk-artside-documents/SKILL.md`
- Create: `rk-artside-documents/references/patterns.md`
- Copy: `rk-artside-documents/assets/logo.png` (from old project)
- Copy: `rk-artside-documents/assets/sello.png` (from old project)

**Step 1: Create SKILL.md**

Write the skill with brand system, component library, WeasyPrint workflow, and example compositions. Key principles:
- Brand: gold (#9A8455), cream (#FFF6ED), dark (#333), light gold (#C4B896)
- Page size: Legal by default, Claude can choose
- ITBIS: opt-in only
- Doc types are examples, not limits
- Claude has layout freedom within brand

**Step 2: Create references/patterns.md**

HTML/CSS templates for:
- Branded header with logo
- Client info block
- Item table (simple and with columns)
- Totals section
- Amount box (receipts)
- Signature area
- Stamp overlay
- Full example: cotización, presupuesto, recibo, carta de compromiso

**Step 3: Copy assets**

```bash
mkdir -p /Users/nelsonperez/code/telegrambots/rk-bot/rk-artside-documents/assets
cp /Users/nelsonperez/code/telegrambots/rk-telegram-tools/rk-artside-documents/assets/logo.png /Users/nelsonperez/code/telegrambots/rk-bot/rk-artside-documents/assets/
cp /Users/nelsonperez/code/telegrambots/rk-telegram-tools/rk-artside-documents/assets/sello.png /Users/nelsonperez/code/telegrambots/rk-bot/rk-artside-documents/assets/
```

**Step 4: Commit**

```bash
git add rk-artside-documents/
git commit -m "feat: add RK ArtSide HTML→PDF skill with brand system and example templates"
```

---

## Task 12: Build, Lint, Final Verification

**Step 1: Run all tests**

```bash
pnpm test
```
Expected: All PASS

**Step 2: Lint and typecheck**

```bash
pnpm lint && pnpm typecheck
```
Expected: Clean

**Step 3: Build**

```bash
pnpm build
```
Expected: `dist/index.js` created

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: fix lint and type errors"
```

---

## Task 13: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

**Step 1: Write CLAUDE.md**

```markdown
# RK Bot

Telegram bot for RK ArtSide SRL document generation. Generates professional PDFs (cotizaciones, presupuestos, recibos, cartas, and any branded document) via Claude Skills API with HTML→PDF (WeasyPrint).

## Stack

TypeScript, pnpm, Grammy (Telegram), Hono (HTTP), PostgreSQL (pg), Claude Sonnet 4.6 (Skills API + Code Execution), Soniox (voice), Vitest, Biome, esbuild.

## Commands

```bash
pnpm dev            # Dev server (tsx watch)
pnpm test           # vitest run
pnpm typecheck      # tsc --noEmit
pnpm lint           # biome check
pnpm build          # esbuild → dist/index.js
```

## Project Structure

```
src/
├── index.ts                 # Entry point: services init, bot setup, server start
├── app.ts                   # Hono webhook server (GET /health, POST /webhook)
├── config.ts                # Zod-validated env vars
├── logger.ts                # Pino logger
├── bot/
│   ├── handler.ts           # Text/voice message routing, processMessage flow
│   ├── commands.ts          # /nuevo, /cancelar, /ayuda
│   └── session.ts           # State machine (idle→collecting→confirming→generated)
├── services/
│   ├── claude.ts            # Claude client, respond tool, pause_turn loop, file download
│   ├── conversation.ts      # Conversation CRUD, message registry, doc counters
│   └── transcriber.ts       # Soniox voice transcription
└── db/
    └── client.ts            # PostgreSQL pool + migrations
rk-artside-documents/        # Claude skill (SKILL.md + HTML/CSS patterns + assets)
```

## Key Patterns

- **State machine:** `session.ts` owns transitions. `mapActionToState()` validates — invalid actions silently preserve state.
- **Structured responses:** Claude uses the `respond` tool, not raw text. Bot extracts `session_action` to drive state.
- **Active session attachment:** New @mentions in groups check for active (non-idle) sessions. Claude decides continue vs. new.
- **ITBIS:** Opt-in only. Never ask about ITBIS unless the user mentions it.
- **Document types:** The 4 examples (COT, PRES, REC, CARTA) are baselines. Any document can be generated with RK branding.

## Deployment

Render. `Procfile`: `web: node dist/index.js`
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md project guide"
```
