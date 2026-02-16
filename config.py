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


_REQUIRED = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "RK_SKILL_ID", "WEBHOOK_SECRET", "SONIOX_API_KEY"]
_DB_VARS = ["DATABASE_HOST", "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME"]


def load_config() -> Config:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    db_missing = [k for k in _DB_VARS if not os.environ.get(k)]
    if db_missing:
        raise ValueError(f"Missing required database environment variables: {', '.join(db_missing)}")

    db_user = os.environ["DATABASE_USER"]
    db_password = os.environ["DATABASE_PASSWORD"]
    db_host = os.environ["DATABASE_HOST"]
    db_name = os.environ["DATABASE_NAME"]
    endpoint_id = db_host.split(".")[0]
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}?sslmode=require&options=endpoint%3D{endpoint_id}"

    return Config(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        rk_skill_id=os.environ["RK_SKILL_ID"],
        webhook_secret=os.environ["WEBHOOK_SECRET"],
        database_url=database_url,
        soniox_api_key=os.environ["SONIOX_API_KEY"],
    )
