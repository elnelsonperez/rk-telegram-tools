import { serve } from "@hono/node-server";
import { Bot } from "grammy";
import { createWebhookApp } from "./app.js";
import { registerCallbacks } from "./bot/callbacks.js";
import { registerCommands } from "./bot/commands.js";
import { registerHandlers } from "./bot/handler.js";
import { loadConfig } from "./config.js";
import { createPool, runMigrations } from "./db/client.js";
import { createLogger } from "./logger.js";
import { ClaudeClient } from "./services/claude.js";
import { ConversationStore } from "./services/conversation.js";

const log = createLogger("server");
const config = loadConfig();

const pool = createPool(config.DATABASE_URL);
const conversationStore = new ConversationStore(pool);
const claudeClient = new ClaudeClient(config.ANTHROPIC_API_KEY);

const bot = new Bot(config.TELEGRAM_BOT_TOKEN);

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

registerCallbacks(bot, conversationStore, claudeClient, config);
registerCommands(bot, conversationStore);
registerHandlers(bot, conversationStore, claudeClient, config);

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
    log.info({ signal }, "Shutdown signal received");
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
