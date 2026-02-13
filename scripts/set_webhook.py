"""Register the Telegram webhook. Run once after deploying.

Usage: uv run python scripts/set_webhook.py <APP_URL>
Example: uv run python scripts/set_webhook.py https://rkbot-xyz.koyeb.app
"""
import sys
import os
import httpx


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <APP_URL>")
        sys.exit(1)

    app_url = sys.argv[1].rstrip("/")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    secret = os.environ.get("WEBHOOK_SECRET")

    if not token or not secret:
        print("Error: Set TELEGRAM_BOT_TOKEN and WEBHOOK_SECRET env vars")
        sys.exit(1)

    response = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": f"{app_url}/webhook",
            "secret_token": secret,
            "allowed_updates": ["message"],
        },
    )

    result = response.json()
    if result.get("ok"):
        print(f"Webhook set to {app_url}/webhook")
    else:
        print(f"Error: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
