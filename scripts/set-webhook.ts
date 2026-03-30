/**
 * Register the Telegram webhook endpoint.
 *
 * Usage:
 *   npx tsx scripts/set-webhook.ts <RENDER_URL>
 *
 * Example:
 *   npx tsx scripts/set-webhook.ts https://rk-bot.onrender.com
 *
 * Reads TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET from .env or environment.
 */

const url = process.argv[2];
if (!url) {
  console.error("Usage: npx tsx scripts/set-webhook.ts <BASE_URL>");
  console.error("Example: npx tsx scripts/set-webhook.ts https://rk-bot.onrender.com");
  process.exit(1);
}

const token = process.env.TELEGRAM_BOT_TOKEN;
const secret = process.env.TELEGRAM_WEBHOOK_SECRET;

if (!token) {
  console.error("Missing TELEGRAM_BOT_TOKEN env var");
  process.exit(1);
}
if (!secret) {
  console.error("Missing TELEGRAM_WEBHOOK_SECRET env var");
  process.exit(1);
}

const webhookUrl = `${url.replace(/\/$/, "")}/webhook`;

const res = await fetch(`https://api.telegram.org/bot${token}/setWebhook`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    url: webhookUrl,
    secret_token: secret,
    allowed_updates: ["message", "callback_query"],
  }),
});

const data = await res.json();

if (data.ok) {
  console.log(`Webhook set to: ${webhookUrl}`);
  console.log("Response:", JSON.stringify(data, null, 2));
} else {
  console.error("Failed to set webhook:", JSON.stringify(data, null, 2));
  process.exit(1);
}
