import type { Update } from "grammy/types";
import { Hono } from "hono";
import { createLogger } from "./logger.js";

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
    beginShutdown: () => {
      shuttingDown = true;
    },
  };
}
