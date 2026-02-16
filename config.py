import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    anthropic_api_key: str
    rk_skill_id: str
    webhook_secret: str
    database_url: str
    soniox_api_key: str


_REQUIRED = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "RK_SKILL_ID", "WEBHOOK_SECRET", "SONIOX_API_KEY", "DATABASE_URL"]


def load_config() -> Config:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        rk_skill_id=os.environ["RK_SKILL_ID"],
        webhook_secret=os.environ["WEBHOOK_SECRET"],
        database_url=os.environ["DATABASE_URL"],
        soniox_api_key=os.environ["SONIOX_API_KEY"],
    )
