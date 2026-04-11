import { describe, expect, it } from "vitest";
import {
  extractUserText,
  getQuickReply,
  inferDocType,
  isBotMentioned,
  isStale,
  normalizeDocType,
} from "../src/bot/handler";

describe("isBotMentioned", () => {
  const botId = 12345;
  const botUsername = "rk_bot";

  it("detects @username mention in entities", () => {
    const message = {
      text: "@rk_bot hazme una cotización",
      entities: [{ type: "mention", offset: 0, length: 7 }],
    };
    expect(isBotMentioned(message, botId, botUsername)).toBe(true);
  });

  it("detects text_mention by user ID", () => {
    const message = {
      text: "Bot hazme una cotización",
      entities: [{ type: "text_mention", offset: 0, length: 3, user: { id: 12345 } }],
    };
    expect(isBotMentioned(message, botId, botUsername)).toBe(true);
  });

  it("returns false when not mentioned", () => {
    const message = {
      text: "@other_bot hazme una cotización",
      entities: [{ type: "mention", offset: 0, length: 10 }],
    };
    expect(isBotMentioned(message, botId, botUsername)).toBe(false);
  });

  it("returns false with no entities", () => {
    const message = { text: "hello world" };
    expect(isBotMentioned(message, botId, botUsername)).toBe(false);
  });

  it("case-insensitive username matching", () => {
    const message = {
      text: "@RK_Bot hazme una cotización",
      entities: [{ type: "mention", offset: 0, length: 7 }],
    };
    expect(isBotMentioned(message, botId, botUsername)).toBe(true);
  });
});

describe("extractUserText", () => {
  const botId = 12345;
  const botUsername = "rk_bot";

  it("removes @mention from beginning of text", () => {
    const message = {
      text: "@rk_bot hazme una cotización",
      entities: [{ type: "mention", offset: 0, length: 7 }],
    };
    expect(extractUserText(message, botId, botUsername)).toBe("hazme una cotización");
  });

  it("returns full text when no mention", () => {
    const message = { text: "hazme una cotización" };
    expect(extractUserText(message, botId, botUsername)).toBe("hazme una cotización");
  });

  it("handles mention in middle of text", () => {
    const message = {
      text: "oye @rk_bot hazme una cotización",
      entities: [{ type: "mention", offset: 4, length: 7 }],
    };
    expect(extractUserText(message, botId, botUsername)).toBe("oye hazme una cotización");
  });

  it("handles text_mention removal", () => {
    const message = {
      text: "Bot hazme una cotización",
      entities: [{ type: "text_mention", offset: 0, length: 3, user: { id: 12345 } }],
    };
    expect(extractUserText(message, botId, botUsername)).toBe("hazme una cotización");
  });
});

describe("inferDocType", () => {
  it("detects cotización (with accent)", () => {
    expect(inferDocType("Necesito una cotización")).toBe("COT");
  });

  it("detects cotizacion (without accent)", () => {
    expect(inferDocType("hazme una cotizacion")).toBe("COT");
  });

  it("detects presupuesto", () => {
    expect(inferDocType("Quiero un presupuesto")).toBe("PRES");
  });

  it("detects recibo", () => {
    expect(inferDocType("dame un recibo")).toBe("REC");
  });

  it("detects carta de compromiso", () => {
    expect(inferDocType("necesito una carta de compromiso")).toBe("CARTA");
  });

  it("returns null for unknown text", () => {
    expect(inferDocType("hola qué tal")).toBeNull();
  });

  it("case insensitive", () => {
    expect(inferDocType("COTIZACIÓN PARA MAÑANA")).toBe("COT");
    expect(inferDocType("PRESUPUESTO urgente")).toBe("PRES");
  });
});

describe("normalizeDocType", () => {
  it("maps Claude snake_case carta_compromiso to CARTA", () => {
    expect(normalizeDocType("carta_compromiso")).toBe("CARTA");
  });

  it("maps cotizacion variants to COT", () => {
    expect(normalizeDocType("cotizacion")).toBe("COT");
    expect(normalizeDocType("Cotización")).toBe("COT");
  });

  it("maps presupuesto to PRES", () => {
    expect(normalizeDocType("presupuesto")).toBe("PRES");
  });

  it("maps recibo to REC", () => {
    expect(normalizeDocType("recibo_de_pago")).toBe("REC");
  });

  it("preserves short codes unchanged", () => {
    expect(normalizeDocType("CARTA")).toBe("CARTA");
    expect(normalizeDocType("COT")).toBe("COT");
  });

  it("strips underscores and uppercases unknown types", () => {
    expect(normalizeDocType("contrato_servicio")).toBe("CONTRATOSERVICIO");
  });

  it("falls back to DOC when stripping leaves empty", () => {
    expect(normalizeDocType("___")).toBe("DOC");
  });
});

describe("isStale", () => {
  it("returns true for 20 min ago", () => {
    const date = new Date(Date.now() - 20 * 60 * 1000);
    expect(isStale(date)).toBe(true);
  });

  it("returns false for 5 min ago", () => {
    const date = new Date(Date.now() - 5 * 60 * 1000);
    expect(isStale(date)).toBe(false);
  });

  it("boundary: exactly 15 min is not stale", () => {
    const date = new Date(Date.now() - 15 * 60 * 1000);
    expect(isStale(date)).toBe(false);
  });
});

describe("getQuickReply", () => {
  it("returns greeting for hola", () => {
    const reply = getQuickReply("hola");
    expect(reply).toBeTruthy();
    expect(reply).toContain("/nuevo");
  });

  it("returns greeting for ¡Hola! (with punctuation)", () => {
    const reply = getQuickReply("¡Hola!");
    expect(reply).toBeTruthy();
    expect(reply).toContain("/nuevo");
  });

  it("returns thanks reply", () => {
    const reply = getQuickReply("gracias");
    expect(reply).toBeTruthy();
    expect(reply!.toLowerCase()).toContain("nada");
  });

  it("returns null for long messages", () => {
    expect(getQuickReply("necesito una cotización para un servicio de diseño gráfico")).toBeNull();
  });

  it("returns null for unknown short messages", () => {
    expect(getQuickReply("dame")).toBeNull();
  });
});
