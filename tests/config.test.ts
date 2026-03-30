import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("loadConfig", () => {
  const VALID_ENV = {
    TELEGRAM_BOT_TOKEN: "test-token",
    TELEGRAM_WEBHOOK_SECRET: "test-secret",
    ANTHROPIC_API_KEY: "test-api-key",
    RK_SKILL_ID: "test-skill-id",
    DATABASE_URL: "postgresql://localhost/test",
    SONIOX_API_KEY: "test-soniox",
  };

  beforeEach(() => {
    for (const [key, val] of Object.entries(VALID_ENV)) {
      vi.stubEnv(key, val);
    }
    // Remove NODE_ENV so the schema default ("development") kicks in
    delete process.env.NODE_ENV;
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("loads valid config from environment", async () => {
    const { loadConfig } = await import("../src/config");
    const config = loadConfig();
    expect(config.TELEGRAM_BOT_TOKEN).toBe("test-token");
    expect(config.NODE_ENV).toBe("development");
  });

  it("throws on missing required var", async () => {
    vi.stubEnv("TELEGRAM_BOT_TOKEN", "");
    const { loadConfig } = await import("../src/config");
    expect(() => loadConfig()).toThrow();
  });
});
