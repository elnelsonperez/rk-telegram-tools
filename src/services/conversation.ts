import type pg from "pg";
import { SessionState } from "../bot/session.js";
import { createLogger } from "../logger.js";

const log = createLogger("conversation");

export interface Conversation {
  messages: Array<{ role: string; content: unknown }>;
  sessionState: SessionState;
  containerId: string | null;
  docType: string | null;
  lastActivity: Date;
  /** Text the user sent that triggered a stale-session prompt, stashed so
   *  the resume/new callbacks can process it without re-asking. */
  pendingUserText: string | null;
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
      `INSERT INTO conversations (chat_id, root_message_id)
       VALUES ($1, $2)
       ON CONFLICT (chat_id, root_message_id) DO UPDATE SET chat_id = conversations.chat_id
       RETURNING messages, session_state, container_id, doc_type, last_activity, pending_user_text`,
      [chatId, rootMessageId],
    );
    const row = result.rows[0];
    return {
      messages: row.messages,
      sessionState: row.session_state as SessionState,
      containerId: row.container_id,
      docType: row.doc_type,
      lastActivity: row.last_activity,
      pendingUserText: row.pending_user_text,
    };
  }

  async findActiveForChat(chatId: number): Promise<ActiveConversationRef | null> {
    const result = await this.pool.query(
      `SELECT root_message_id, session_state, doc_type, last_activity
       FROM conversations
       WHERE chat_id = $1 AND session_state != $2
       ORDER BY last_activity DESC
       LIMIT 1`,
      [chatId, SessionState.Idle],
    );
    if (result.rows.length === 0) return null;
    const row = result.rows[0];
    return {
      rootMessageId: Number(row.root_message_id),
      sessionState: row.session_state as SessionState,
      docType: row.doc_type,
      lastActivity: row.last_activity,
    };
  }

  async save(chatId: number, rootMessageId: number, conv: Conversation): Promise<void> {
    await this.pool.query(
      `UPDATE conversations
       SET messages = $1,
           session_state = $2,
           container_id = $3,
           doc_type = $4,
           pending_user_text = $5,
           last_activity = NOW()
       WHERE chat_id = $6 AND root_message_id = $7`,
      [
        JSON.stringify(conv.messages),
        conv.sessionState,
        conv.containerId,
        conv.docType,
        conv.pendingUserText,
        chatId,
        rootMessageId,
      ],
    );
    log.debug({ chatId, rootMessageId, state: conv.sessionState }, "conversation saved");
  }

  async registerMessage(chatId: number, messageId: number, rootMessageId: number): Promise<void> {
    await this.pool.query(
      `INSERT INTO message_registry (chat_id, message_id, root_message_id)
       VALUES ($1, $2, $3)
       ON CONFLICT (chat_id, message_id) DO UPDATE SET root_message_id = $3`,
      [chatId, messageId, rootMessageId],
    );
  }

  async findRoot(chatId: number, messageId: number): Promise<number | null> {
    const result = await this.pool.query(
      `SELECT root_message_id FROM message_registry WHERE chat_id = $1 AND message_id = $2`,
      [chatId, messageId],
    );
    if (result.rows.length === 0) return null;
    return Number(result.rows[0].root_message_id);
  }

  async nextDocumentNumber(docType: string, year: number): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO document_counters (doc_type, year, last_number)
       VALUES ($1, $2, 1)
       ON CONFLICT (doc_type, year) DO UPDATE SET last_number = document_counters.last_number + 1
       RETURNING last_number`,
      [docType, year],
    );
    const num = result.rows[0].last_number;
    return `${docType}-${year}-${String(num).padStart(3, "0")}`;
  }

  async cleanup(ttlSeconds: number): Promise<void> {
    const cutoff = `NOW() - INTERVAL '${ttlSeconds} seconds'`;
    await this.pool.query(`DELETE FROM message_registry WHERE (chat_id, root_message_id) IN (
      SELECT chat_id, root_message_id FROM conversations WHERE last_activity < ${cutoff}
    )`);
    await this.pool.query(`DELETE FROM conversations WHERE last_activity < ${cutoff}`);
    log.info({ ttlSeconds }, "cleanup complete");
  }
}
