import { type Context, GrammyError } from "grammy";
import type { Message } from "grammy/types";
import { createLogger } from "../logger";
import type { ConversationStore } from "../services/conversation";

const log = createLogger("safe-send");

type ReplyOptions = Parameters<Context["reply"]>[1];

function isMarkdownParseError(err: unknown): err is GrammyError {
  return (
    err instanceof GrammyError &&
    err.error_code === 400 &&
    err.description.includes("can't parse entities")
  );
}

/**
 * Reply with Markdown parse_mode, falling back to plain text if Telegram
 * rejects the message due to malformed entities. A styling failure must
 * never block delivery of user-facing content.
 */
export async function safeReplyMarkdown(
  ctx: Context,
  text: string,
  options?: ReplyOptions,
): Promise<Message.TextMessage> {
  try {
    return await ctx.reply(text, { ...options, parse_mode: "Markdown" });
  } catch (err) {
    if (!isMarkdownParseError(err)) throw err;
    log.warn(
      { description: err.description, textLength: text.length },
      "Markdown parse failed, retrying as plain text",
    );
    const { parse_mode: _omit, ...rest } = (options ?? {}) as Record<string, unknown>;
    return await ctx.reply(text, rest as ReplyOptions);
  }
}

export { isMarkdownParseError };

/**
 * Reply with Markdown fallback AND register the message with the conversation
 * store so future replies are threaded. A failure here is logged but never
 * thrown — styling/tracking must not block downstream file delivery.
 */
export async function safeReplyAndRegister(
  ctx: Context,
  text: string,
  store: ConversationStore,
  chatId: number,
  rootId: number,
  options?: ReplyOptions,
): Promise<void> {
  try {
    const sent = await safeReplyMarkdown(ctx, text, options);
    await store.registerMessage(chatId, sent.message_id, rootId);
  } catch (err) {
    log.error({ err, chatId, rootId }, "Failed to send/register message");
  }
}
