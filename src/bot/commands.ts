import type { Bot } from "grammy";
import { createLogger } from "../logger";
import type { ConversationStore } from "../services/conversation";
import { SessionState } from "./session";

const log = createLogger("commands");

export function registerCommands(bot: Bot, conversationStore: ConversationStore): void {
  bot.command("nuevo", async (ctx) => {
    const chatId = ctx.chat.id;
    log.info({ chatId }, "/nuevo command");
    const active = await conversationStore.findActiveForChat(chatId);
    if (active) {
      const conv = await conversationStore.getOrCreate(chatId, active.rootMessageId);
      conv.sessionState = SessionState.Idle;
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
    conv.sessionState = SessionState.Idle;
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
Mencióneme con @nombre y dígame qué necesita.`,
      { parse_mode: "Markdown" },
    );
  });
}
