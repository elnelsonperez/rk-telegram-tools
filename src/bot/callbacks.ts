import type { Bot } from "grammy";
import { InputFile } from "grammy";
import type { Message } from "grammy/types";
import type { Config } from "../config.js";
import { createLogger } from "../logger.js";
import type { ClaudeClient, ClaudeResponse } from "../services/claude.js";
import type { ConversationStore } from "../services/conversation.js";
import { processMessage } from "./handler.js";
import { DOC_TYPE_LABELS, getDocTypeKeyboard, getPostGenerateKeyboard } from "./keyboards.js";
import { isMarkdownParseError, safeReplyAndRegister } from "./safe-send.js";
import { SessionState } from "./session.js";

const log = createLogger("callbacks");

async function dismissInlineKeyboard(ctx: {
  editMessageReplyMarkup: (markup: { reply_markup?: { inline_keyboard: [] } }) => Promise<unknown>;
}) {
  try {
    await ctx.editMessageReplyMarkup({ reply_markup: { inline_keyboard: [] } });
  } catch {
    // Message may have been deleted or already edited
  }
}

export function registerCallbacks(
  bot: Bot,
  conversationStore: ConversationStore,
  claudeClient: ClaudeClient,
  config: Config,
): void {
  // Document type selection from keyboard
  for (const docType of ["COT", "PRES", "REC", "CARTA", "OTHER"]) {
    bot.callbackQuery(`new_doc:${docType}`, async (ctx) => {
      await ctx.answerCallbackQuery();
      await dismissInlineKeyboard(ctx);
      const chatId = ctx.chat!.id;
      const msgId = ctx.callbackQuery.message?.message_id ?? Date.now();
      log.info({ chatId, docType }, "Document type selected");

      const rootId = msgId;
      const conv = await conversationStore.getOrCreate(chatId, rootId);
      conv.sessionState = SessionState.Collecting;
      conv.docType = docType === "OTHER" ? null : docType;
      await conversationStore.save(chatId, rootId, conv);
      await conversationStore.registerMessage(chatId, msgId, rootId);

      const label = docType === "OTHER" ? "documento" : (DOC_TYPE_LABELS[docType] ?? "documento");
      const botMsg = await ctx.reply(`📄 Nueva ${label}. Cuéntame los detalles.`, {
        reply_markup: { force_reply: true },
      });
      await conversationStore.registerMessage(chatId, botMsg.message_id, rootId);
    });
  }

  // Generate action
  bot.callbackQuery("action:generate", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    const chatId = ctx.chat!.id;
    const msgId = ctx.callbackQuery.message?.message_id;
    if (!msgId) return;
    log.info({ chatId }, "Generate button pressed");

    const rootId = (await conversationStore.findRoot(chatId, msgId)) ?? msgId;
    const conv = await conversationStore.getOrCreate(chatId, rootId);

    conv.messages.push({ role: "user", content: "Generar el documento ahora." });

    const statusMsg = await ctx.reply("⏳ Generando documento...");

    let result: ClaudeResponse;
    try {
      result = await claudeClient.sendMessage(
        conv.messages as Parameters<ClaudeClient["sendMessage"]>[0],
        config.RK_SKILL_ID,
        "",
        conv.containerId ?? undefined,
      );
    } catch (err) {
      log.error({ err, chatId, rootId }, "Generate: Claude API call failed");
      await ctx.api.deleteMessage(chatId, statusMsg.message_id);
      await ctx.reply("❌ Error generando el documento. Intenta de nuevo.");
      return;
    }

    await ctx.api.deleteMessage(chatId, statusMsg.message_id);

    conv.containerId = result.containerId;
    conv.messages.push({ role: "assistant", content: result.text });
    conv.sessionState =
      result.fileIds.length > 0 ? SessionState.Generated : SessionState.Collecting;
    await conversationStore.save(chatId, rootId, conv);

    const hasFiles = result.fileIds.length > 0;
    const canUseCaption = hasFiles && result.text && result.text.length <= 1024;
    let captionAlreadySent = false;

    if (result.text && (!hasFiles || !canUseCaption)) {
      await safeReplyAndRegister(ctx, result.text, conversationStore, chatId, rootId);
    }

    for (let i = 0; i < result.fileIds.length; i++) {
      const fileId = result.fileIds[i];
      try {
        const { filename, data } = await claudeClient.downloadFile(fileId);
        const isLast = i === result.fileIds.length - 1;
        const useCaptionNow = canUseCaption && i === 0;
        const baseOpts = isLast ? { reply_markup: getPostGenerateKeyboard() } : {};
        const inputFile = new InputFile(new Uint8Array(data), filename);
        let docMsg: Message.DocumentMessage;
        try {
          docMsg = await ctx.api.sendDocument(chatId, inputFile, {
            ...(useCaptionNow ? { caption: result.text, parse_mode: "Markdown" as const } : {}),
            ...baseOpts,
          });
          if (useCaptionNow) captionAlreadySent = true;
        } catch (err) {
          // If the caption's Markdown is malformed, Telegram rejects the whole
          // sendDocument. Retry without caption so the file still ships, and
          // send the text as a separate reply via the safe helper.
          if (useCaptionNow && isMarkdownParseError(err)) {
            log.warn(
              { err, chatId, rootId, fileId },
              "Caption Markdown parse failed, retrying document without caption",
            );
            docMsg = await ctx.api.sendDocument(chatId, inputFile, baseOpts);
          } else {
            throw err;
          }
        }
        await conversationStore.registerMessage(chatId, docMsg.message_id, rootId);
      } catch (err) {
        log.error({ err, chatId, rootId, fileId }, "Failed to send generated document");
      }
    }

    if (canUseCaption && !captionAlreadySent && result.text) {
      await safeReplyAndRegister(ctx, result.text, conversationStore, chatId, rootId);
    }
  });

  // Modify action
  bot.callbackQuery("action:modify", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    const chatId = ctx.chat!.id;
    const msgId = ctx.callbackQuery.message?.message_id;
    if (!msgId) return;
    log.info({ chatId }, "Modify button pressed");

    const rootId = (await conversationStore.findRoot(chatId, msgId)) ?? msgId;
    const conv = await conversationStore.getOrCreate(chatId, rootId);
    conv.sessionState = SessionState.Collecting;
    await conversationStore.save(chatId, rootId, conv);

    const botMsg = await ctx.reply("✏️ ¿Qué deseas modificar?", {
      reply_markup: { force_reply: true },
    });
    await conversationStore.registerMessage(chatId, botMsg.message_id, rootId);
  });

  // Cancel action
  bot.callbackQuery("action:cancel", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    const chatId = ctx.chat!.id;
    const msgId = ctx.callbackQuery.message?.message_id;
    if (!msgId) return;
    log.info({ chatId }, "Cancel button pressed");

    const rootId = (await conversationStore.findRoot(chatId, msgId)) ?? msgId;
    const conv = await conversationStore.getOrCreate(chatId, rootId);
    conv.sessionState = SessionState.Idle;
    await conversationStore.save(chatId, rootId, conv);

    await ctx.reply("❌ Cancelado.");
  });

  // New document from post-generate keyboard
  bot.callbackQuery("action:new_doc", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    log.info({ chatId: ctx.chat!.id }, "New document button pressed");
    await ctx.reply("¿Qué documento necesitas?", { reply_markup: getDocTypeKeyboard() });
  });

  // Session resume — keep history, and if the stale check stashed a pending
  // message, replay it so the user doesn't have to retype it.
  bot.callbackQuery("session:resume", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    const chatId = ctx.chat!.id;
    const msgId = ctx.callbackQuery.message?.message_id;
    if (!msgId) return;
    log.info({ chatId }, "Session resume selected");

    const rootId = (await conversationStore.findRoot(chatId, msgId)) ?? msgId;
    const conv = await conversationStore.getOrCreate(chatId, rootId);
    const pendingText = conv.pendingUserText;
    conv.pendingUserText = null;
    await conversationStore.save(chatId, rootId, conv); // also bumps last_activity

    if (pendingText) {
      await processMessage(
        ctx,
        chatId,
        rootId,
        undefined,
        pendingText,
        conversationStore,
        claudeClient,
        config,
      );
      return;
    }

    const botMsg = await ctx.reply("▶️ Continuando. ¿Qué necesitas?", {
      reply_markup: { force_reply: true },
    });
    await conversationStore.registerMessage(chatId, botMsg.message_id, rootId);
  });

  // Session new (discard stale) — clear conversation history and, if the
  // stale check stashed a pending message, process it as the first turn of
  // the fresh session instead of asking the user to retype.
  bot.callbackQuery("session:new", async (ctx) => {
    await ctx.answerCallbackQuery();
    await dismissInlineKeyboard(ctx);
    const chatId = ctx.chat!.id;
    const msgId = ctx.callbackQuery.message?.message_id;
    if (!msgId) return;
    log.info({ chatId }, "New session selected");

    const rootId = (await conversationStore.findRoot(chatId, msgId)) ?? msgId;
    const conv = await conversationStore.getOrCreate(chatId, rootId);
    const pendingText = conv.pendingUserText;
    conv.sessionState = SessionState.Idle;
    conv.messages = [];
    conv.docType = null;
    conv.containerId = null;
    conv.pendingUserText = null;
    await conversationStore.save(chatId, rootId, conv);

    if (pendingText) {
      await processMessage(
        ctx,
        chatId,
        rootId,
        undefined,
        pendingText,
        conversationStore,
        claudeClient,
        config,
      );
      return;
    }

    await ctx.reply("🆕 ¿Qué documento necesitas?", { reply_markup: getDocTypeKeyboard() });
  });
}
