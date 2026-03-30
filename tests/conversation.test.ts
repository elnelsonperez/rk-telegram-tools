import type pg from "pg";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { SessionState } from "../src/bot/session";

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
    await pool.query("DELETE FROM document_counters");
    await pool.query("DELETE FROM conversations");
  });

  afterAll(async () => {
    await pool.query("DROP TABLE IF EXISTS message_registry, document_counters, conversations");
    await pool.end();
  });

  it("creates a new conversation with defaults", async () => {
    const conv = await store.getOrCreate(100, 1);
    expect(conv.messages).toEqual([]);
    expect(conv.sessionState).toBe(SessionState.Idle);
    expect(conv.containerId).toBeNull();
    expect(conv.docType).toBeNull();
    expect(conv.lastActivity).toBeInstanceOf(Date);
  });

  it("loads existing conversation after save", async () => {
    const conv = await store.getOrCreate(100, 1);
    conv.sessionState = SessionState.Collecting;
    conv.docType = "COT";
    conv.messages = [{ role: "user", content: "hello" }];
    conv.containerId = "ctr_123";
    await store.save(100, 1, conv);

    const loaded = await store.getOrCreate(100, 1);
    expect(loaded.sessionState).toBe(SessionState.Collecting);
    expect(loaded.docType).toBe("COT");
    expect(loaded.messages).toEqual([{ role: "user", content: "hello" }]);
    expect(loaded.containerId).toBe("ctr_123");
  });

  it("finds active conversation for chat (non-idle)", async () => {
    const conv = await store.getOrCreate(200, 10);
    conv.sessionState = SessionState.Collecting;
    conv.docType = "COT";
    await store.save(200, 10, conv);

    const active = await store.findActiveForChat(200);
    expect(active).not.toBeNull();
    expect(active!.rootMessageId).toBe(10);
    expect(active!.sessionState).toBe(SessionState.Collecting);
    expect(active!.docType).toBe("COT");
  });

  it("returns null when no active conversation (only idle ones exist)", async () => {
    await store.getOrCreate(300, 20); // defaults to idle
    const active = await store.findActiveForChat(300);
    expect(active).toBeNull();
  });

  it("registers and finds message root", async () => {
    await store.registerMessage(400, 50, 40);
    const root = await store.findRoot(400, 50);
    expect(root).toBe(40);
  });

  it("returns null for unregistered message", async () => {
    const root = await store.findRoot(400, 999);
    expect(root).toBeNull();
  });

  it("increments document counter", async () => {
    const first = await store.nextDocumentNumber("COT", 2026);
    expect(first).toBe("COT-2026-001");

    const second = await store.nextDocumentNumber("COT", 2026);
    expect(second).toBe("COT-2026-002");

    const third = await store.nextDocumentNumber("COT", 2026);
    expect(third).toBe("COT-2026-003");

    // Different type resets counter
    const other = await store.nextDocumentNumber("FAC", 2026);
    expect(other).toBe("FAC-2026-001");
  });
});
