import type pg from "pg";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const TEST_DB_URL = process.env.TEST_DATABASE_URL;

describe.skipIf(!TEST_DB_URL)("database", () => {
  let pool: pg.Pool;

  beforeAll(async () => {
    const { createPool, runMigrations } = await import("../src/db/client");
    pool = createPool(TEST_DB_URL!);
    await runMigrations(pool);
  });

  afterAll(async () => {
    await pool.query("DROP TABLE IF EXISTS message_registry, document_counters, conversations");
    await pool.end();
  });

  it("creates conversations table", async () => {
    const result = await pool.query(
      "SELECT column_name FROM information_schema.columns WHERE table_name = 'conversations' ORDER BY ordinal_position",
    );
    const columns = result.rows.map((r) => r.column_name);
    expect(columns).toContain("chat_id");
    expect(columns).toContain("session_state");
    expect(columns).toContain("messages");
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
