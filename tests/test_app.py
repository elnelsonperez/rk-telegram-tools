import pytest
import os
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("RK_SKILL_ID", "skill_123")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")


@pytest.fixture
def client():
    from app import app
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_rejects_missing_secret(client):
    response = client.post("/webhook", json={"update_id": 1})
    assert response.status_code == 403


def test_webhook_rejects_wrong_secret(client):
    response = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 403


def test_webhook_accepts_correct_secret(client):
    response = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )
    assert response.status_code == 200
