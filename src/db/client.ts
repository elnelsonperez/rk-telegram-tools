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
    ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS pending_user_text TEXT
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

  await pool.query(`
    CREATE INDEX IF NOT EXISTS idx_conversations_active
    ON conversations (chat_id, last_activity DESC)
    WHERE session_state != 'idle'
  `);

  log.info("Migrations complete");
}
