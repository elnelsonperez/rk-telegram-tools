import { describe, expect, it } from "vitest";
import { SessionAction } from "../src/bot/session";
import { extractResponse, needsContinuation, RESPOND_TOOL } from "../src/services/claude";

describe("needsContinuation", () => {
  it("returns true for pause_turn", () => {
    expect(needsContinuation("pause_turn")).toBe(true);
  });
  it("returns false for end_turn", () => {
    expect(needsContinuation("end_turn")).toBe(false);
  });
  it("returns false for null", () => {
    expect(needsContinuation(null)).toBe(false);
  });
});

describe("extractResponse", () => {
  it("extracts respond tool call", () => {
    const content = [
      { type: "text", text: "Internal thinking..." },
      {
        type: "tool_use",
        name: "respond",
        input: { text: "Hello user", session_action: "continue" },
      },
    ];
    const result = extractResponse(content);
    expect(result.text).toBe("Hello user");
    expect(result.sessionAction).toBe(SessionAction.Continue);
    expect(result.fileIds).toEqual([]);
  });

  it("extracts file IDs from code execution results", () => {
    const content = [
      {
        type: "bash_code_execution_tool_result",
        content: {
          type: "bash_code_execution_result",
          content: [{ file_id: "file-abc123" }, { file_id: "file-def456" }],
        },
      },
      {
        type: "tool_use",
        name: "respond",
        input: { text: "Here's your doc", session_action: "generate" },
      },
    ];
    const result = extractResponse(content);
    expect(result.fileIds).toEqual(["file-abc123", "file-def456"]);
    expect(result.sessionAction).toBe(SessionAction.Generate);
  });

  it("falls back to last text block when no respond tool", () => {
    const content = [
      { type: "text", text: "Thinking..." },
      { type: "text", text: "Here is my answer" },
    ];
    const result = extractResponse(content);
    expect(result.text).toBe("Here is my answer");
    expect(result.sessionAction).toBe(SessionAction.Continue);
  });

  it("returns empty text when no content", () => {
    const result = extractResponse([]);
    expect(result.text).toBe("");
  });

  it("has correct respond tool schema", () => {
    expect(RESPOND_TOOL.name).toBe("respond");
    expect(RESPOND_TOOL.input_schema.required).toContain("text");
    expect(RESPOND_TOOL.input_schema.required).toContain("session_action");
  });
});
