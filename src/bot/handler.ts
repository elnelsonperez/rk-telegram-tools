import { type Bot, type Context, InputFile } from "grammy";
import type { Message, MessageEntity } from "grammy/types";
import { mapActionToState, SessionAction, SessionState } from "../bot/session.js";
import type { Config } from "../config.js";
import { createLogger } from "../logger.js";
import type { ClaudeClient, ClaudeResponse } from "../services/claude.js";
import type { ConversationStore } from "../services/conversation.js";
import { transcribeVoice } from "../services/transcriber.js";

const log = createLogger("handler");

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STALE_THRESHOLD_MS = 15 * 60 * 1000; // 15 minutes

const COMPANY_INFO = `Información de la empresa:
- Nombre: RK ArtSide SRL
- RNC: 1-33-51750-7
- Email: rkartside@gmail.com
- Teléfono: 809 645 7575
- Contacto: Reyka Kawashiro
- Ubicación: Santiago, R.D.
- Moneda: RD$ (Pesos Dominicanos)`;

const QUICK_REPLIES: Record<string, string> = {
  hola: "¡Hola! 👋 Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  hello: "¡Hola! 👋 Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  buenas: "¡Hola! 👋 Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  "buenos dias":
    "¡Buenos días! ☀️ Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  "buenas tardes":
    "¡Buenas tardes! Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  "buenas noches":
    "¡Buenas noches! Soy el asistente de RK ArtSide. Usa /nuevo para iniciar un documento.",
  gracias: "¡De nada! Si necesitas algo más, mencióneme.",
  "muchas gracias": "¡De nada! Fue un placer ayudarte.",
  ok: "Entendido. Si necesitas algo más, mencióneme.",
};

const DOC_TYPE_PATTERNS: Array<[RegExp, string]> = [
  [/cotizaci[oó]n/i, "COT"],
  [/presupuesto/i, "PRES"],
  [/recibo/i, "REC"],
  [/carta\s+de\s+compromiso/i, "CARTA"],
];

// ---------------------------------------------------------------------------
// Exported utility functions
// ---------------------------------------------------------------------------

export function isStale(lastActivity: Date): boolean {
  return Date.now() - lastActivity.getTime() > STALE_THRESHOLD_MS;
}

export function getQuickReply(text: string): string | null {
  const cleaned = text
    .replace(/[¡!¿?.,;:]/g, "")
    .trim()
    .toLowerCase();
  if (cleaned.length > 30) return null;
  return QUICK_REPLIES[cleaned] ?? null;
}

export function inferDocType(text: string): string | null {
  for (const [pattern, docType] of DOC_TYPE_PATTERNS) {
    if (pattern.test(text)) return docType;
  }
  return null;
}

export function isBotMentioned(
  message: Partial<Pick<Message, "text" | "entities">>,
  botId: number,
  botUsername: string,
): boolean {
  const entities = message.entities;
  if (!entities || entities.length === 0) return false;
  const text = message.text ?? "";

  for (const entity of entities) {
    if (entity.type === "mention") {
      const mentioned = text.slice(entity.offset + 1, entity.offset + entity.length);
      if (mentioned.toLowerCase() === botUsername.toLowerCase()) return true;
    }
    if (entity.type === "text_mention" && (entity as MessageEntity.TextMentionMessageEntity).user) {
      if ((entity as MessageEntity.TextMentionMessageEntity).user.id === botId) return true;
    }
  }
  return false;
}

export function extractUserText(
  message: Partial<Pick<Message, "text" | "entities">>,
  botId: number,
  botUsername: string,
): string {
  const text = message.text ?? "";
  const entities = message.entities;
  if (!entities || entities.length === 0) return text;

  for (const entity of entities) {
    let match = false;
    if (entity.type === "mention") {
      const mentioned = text.slice(entity.offset + 1, entity.offset + entity.length);
      match = mentioned.toLowerCase() === botUsername.toLowerCase();
    }
    if (entity.type === "text_mention" && (entity as MessageEntity.TextMentionMessageEntity).user) {
      match = (entity as MessageEntity.TextMentionMessageEntity).user.id === botId;
    }
    if (match) {
      const before = text.slice(0, entity.offset);
      const after = text.slice(entity.offset + entity.length);
      return (before + after).replace(/\s+/g, " ").trim();
    }
  }
  return text;
}

// ---------------------------------------------------------------------------
// processMessage
// ---------------------------------------------------------------------------

export async function processMessage(
  ctx: Context,
  chatId: number,
  rootId: number,
  replyToMsgId: number | undefined,
  userText: string,
  conversationStore: ConversationStore,
  claudeClient: ClaudeClient,
  config: Config,
): Promise<void> {
  // 1. Quick reply check — skip Claude when idle + greeting
  const conv = await conversationStore.getOrCreate(chatId, rootId);

  if (conv.sessionState === SessionState.Idle) {
    const quick = getQuickReply(userText);
    if (quick) {
      await ctx.reply(quick, { reply_to_message_id: replyToMsgId });
      return;
    }
  }

  // 2. Stale session check
  if (conv.sessionState !== SessionState.Idle && isStale(conv.lastActivity)) {
    await ctx.reply(
      "⏰ Pasaron más de 15 minutos desde tu último mensaje. ¿Quieres continuar o iniciar uno nuevo con /nuevo?",
      { reply_to_message_id: replyToMsgId },
    );
    return;
  }

  // 3. Infer doc type
  const detectedDocType = inferDocType(userText);
  if (detectedDocType && !conv.docType) {
    conv.docType = detectedDocType;
  }

  // 4. Build per-turn system context
  const year = new Date().getFullYear();
  let docNumber: string | undefined;
  if (conv.docType) {
    docNumber = await conversationStore.nextDocumentNumber(conv.docType, year);
  }

  const systemParts: string[] = [COMPANY_INFO];
  if (conv.docType) systemParts.push(`Tipo de documento: ${conv.docType}`);
  if (docNumber) systemParts.push(`Número de documento: ${docNumber}`);
  systemParts.push(`Estado de sesión: ${conv.sessionState}`);
  const systemExtra = systemParts.join("\n");

  // 5. Append user message to conversation history
  conv.messages.push({ role: "user", content: userText });

  // 6. Call Claude
  let response: ClaudeResponse;
  try {
    response = await claudeClient.sendMessage(
      conv.messages as Parameters<ClaudeClient["sendMessage"]>[0],
      config.RK_SKILL_ID,
      systemExtra,
      conv.containerId ?? undefined,
    );
  } catch (err) {
    log.error({ err, chatId, rootId }, "Claude API error");
    await ctx.reply("❌ Error al comunicarme con Claude. Intenta de nuevo.", {
      reply_to_message_id: replyToMsgId,
    });
    return;
  }

  // 7. Guard: if "generate" but no files, downgrade to "continue"
  let { sessionAction } = response;
  if (sessionAction === SessionAction.Generate && response.fileIds.length === 0) {
    log.warn({ chatId, rootId }, "Generate action with no files — downgrading to continue");
    sessionAction = SessionAction.Continue;
  }

  // 8. Map action to state transition
  conv.sessionState = mapActionToState(sessionAction, conv.sessionState);
  conv.containerId = response.containerId;
  if (response.docType) conv.docType = response.docType;

  // Append assistant message
  conv.messages.push({ role: "assistant", content: response.text });

  // 9. Save conversation
  await conversationStore.save(chatId, rootId, conv);

  // 10. Send response text
  if (response.text) {
    const sent = await ctx.reply(response.text, {
      reply_to_message_id: replyToMsgId,
      parse_mode: "Markdown",
    });
    // Register the bot's reply so future replies to it are tracked
    await conversationStore.registerMessage(chatId, sent.message_id, rootId);
  }

  // 11. Send files
  for (const fileId of response.fileIds) {
    try {
      const fileBuffer = await claudeClient.downloadFile(fileId);
      const fileName = conv.docType
        ? `${conv.docType}-${Date.now()}.pdf`
        : `documento-${Date.now()}.pdf`;
      const sent = await ctx.replyWithDocument(new InputFile(fileBuffer, fileName), {
        reply_to_message_id: replyToMsgId,
      });
      await conversationStore.registerMessage(chatId, sent.message_id, rootId);
    } catch (err) {
      log.error({ err, fileId }, "Failed to download/send file");
      await ctx.reply("❌ No pude enviar el archivo generado.", {
        reply_to_message_id: replyToMsgId,
      });
    }
  }

  // 12. Send pending question after file delivery
  if (response.pendingQuestion && response.fileIds.length > 0) {
    const sent = await ctx.reply(response.pendingQuestion, {
      reply_to_message_id: replyToMsgId,
      parse_mode: "Markdown",
    });
    await conversationStore.registerMessage(chatId, sent.message_id, rootId);
  }
}

// ---------------------------------------------------------------------------
// registerHandlers
// ---------------------------------------------------------------------------

export function registerHandlers(
  bot: Bot,
  conversationStore: ConversationStore,
  claudeClient: ClaudeClient,
  config: Config,
): void {
  const botInfo = () => bot.botInfo;

  // Handle voice messages
  bot.on("message:voice", async (ctx) => {
    const msg = ctx.message;
    const chatId = msg.chat.id;
    const botId = botInfo().id;
    const isGroup = msg.chat.type === "group" || msg.chat.type === "supergroup";

    // In groups, voice must be a reply to the bot or there must be an active session
    let rootId: number | undefined;

    if (isGroup) {
      // Check if reply to bot message
      if (msg.reply_to_message) {
        const replyRoot = await conversationStore.findRoot(chatId, msg.reply_to_message.message_id);
        if (replyRoot != null) {
          rootId = replyRoot;
        } else if (msg.reply_to_message.from?.id === botId) {
          rootId = msg.reply_to_message.message_id;
        } else {
          return; // Voice reply to non-bot message, ignore
        }
      } else {
        // No reply — check for active session
        const active = await conversationStore.findActiveForChat(chatId);
        if (active) {
          rootId = active.rootMessageId;
        } else {
          return; // No active session, ignore voice in group
        }
      }
    } else {
      // DM: use reply root or message itself as root
      if (msg.reply_to_message) {
        rootId =
          (await conversationStore.findRoot(chatId, msg.reply_to_message.message_id)) ??
          msg.message_id;
      } else {
        rootId = msg.message_id;
      }
    }

    // Transcribe voice
    await ctx.reply("🎙️ Transcribiendo audio...", { reply_to_message_id: msg.message_id });
    const transcript = await transcribeVoice(
      config.TELEGRAM_BOT_TOKEN,
      config.SONIOX_API_KEY,
      msg.voice.file_id,
    );
    if (!transcript) {
      await ctx.reply("❌ No pude transcribir el audio. Intenta de nuevo o escribe tu mensaje.", {
        reply_to_message_id: msg.message_id,
      });
      return;
    }

    await conversationStore.registerMessage(chatId, msg.message_id, rootId);
    await processMessage(
      ctx,
      chatId,
      rootId,
      msg.message_id,
      transcript,
      conversationStore,
      claudeClient,
      config,
    );
  });

  // Handle text messages (non-command)
  bot.on("message:text", async (ctx) => {
    const msg = ctx.message;
    const chatId = msg.chat.id;
    const botId = botInfo().id;
    const botUsername = botInfo().username ?? "";
    const isGroup = msg.chat.type === "group" || msg.chat.type === "supergroup";
    const text = msg.text ?? "";

    // Skip commands — they are handled by bot.command()
    if (text.startsWith("/")) return;

    let rootId: number;
    let userText: string;

    if (isGroup) {
      // --- GROUP ROUTING ---

      // 1. Is reply to a bot message?
      if (msg.reply_to_message) {
        const replyRoot = await conversationStore.findRoot(chatId, msg.reply_to_message.message_id);
        if (replyRoot != null) {
          rootId = replyRoot;
          userText = extractUserText(msg, botId, botUsername);
        } else if (msg.reply_to_message.from?.id === botId) {
          // Direct reply to bot but not in registry — use the replied message as root
          rootId = msg.reply_to_message.message_id;
          userText = extractUserText(msg, botId, botUsername);
        } else {
          // Reply to non-bot message — only process if bot is mentioned
          if (!isBotMentioned(msg, botId, botUsername)) return;
          rootId = msg.message_id;
          userText = extractUserText(msg, botId, botUsername);
        }
      }
      // 2. Is @mention?
      else if (isBotMentioned(msg, botId, botUsername)) {
        userText = extractUserText(msg, botId, botUsername);

        // Check for active session
        const active = await conversationStore.findActiveForChat(chatId);
        if (active) {
          rootId = active.rootMessageId;
        } else {
          rootId = msg.message_id;
        }
      }
      // 3. Not directed at bot → ignore
      else {
        return;
      }
    } else {
      // --- DM ROUTING ---
      userText = text;

      if (msg.reply_to_message) {
        rootId =
          (await conversationStore.findRoot(chatId, msg.reply_to_message.message_id)) ??
          msg.message_id;
      } else {
        // Check for active session
        const active = await conversationStore.findActiveForChat(chatId);
        rootId = active?.rootMessageId ?? msg.message_id;
      }
    }

    // Register the user's message
    await conversationStore.registerMessage(chatId, msg.message_id, rootId);

    await processMessage(
      ctx,
      chatId,
      rootId,
      msg.message_id,
      userText,
      conversationStore,
      claudeClient,
      config,
    );
  });
}
