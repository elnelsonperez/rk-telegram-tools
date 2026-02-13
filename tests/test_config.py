import os
import pytest
from config import load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("RK_SKILL_ID", "skill_123")
    monkeypatch.setenv("WEBHOOK_SECRET", "secret123")

    cfg = load_config()
    assert cfg.telegram_bot_token == "test-token"
    assert cfg.anthropic_api_key == "test-key"
    assert cfg.rk_skill_id == "skill_123"
    assert cfg.webhook_secret == "secret123"


def test_load_config_missing_var_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RK_SKILL_ID", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        load_config()
