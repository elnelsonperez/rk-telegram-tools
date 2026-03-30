import { describe, expect, it } from "vitest";
import { mapActionToState, SessionAction, SessionState, transition } from "../src/bot/session";

describe("transition", () => {
  it("allows idle → collecting", () => {
    expect(transition(SessionState.Idle, SessionState.Collecting)).toBe(SessionState.Collecting);
  });

  it("allows collecting → confirming", () => {
    expect(transition(SessionState.Collecting, SessionState.Confirming)).toBe(
      SessionState.Confirming,
    );
  });

  it("allows collecting → generated", () => {
    expect(transition(SessionState.Collecting, SessionState.Generated)).toBe(
      SessionState.Generated,
    );
  });

  it("allows confirming → generated", () => {
    expect(transition(SessionState.Confirming, SessionState.Generated)).toBe(
      SessionState.Generated,
    );
  });

  it("allows generated → collecting (revision)", () => {
    expect(transition(SessionState.Generated, SessionState.Collecting)).toBe(
      SessionState.Collecting,
    );
  });

  it("allows any state → idle", () => {
    expect(transition(SessionState.Collecting, SessionState.Idle)).toBe(SessionState.Idle);
    expect(transition(SessionState.Confirming, SessionState.Idle)).toBe(SessionState.Idle);
    expect(transition(SessionState.Generated, SessionState.Idle)).toBe(SessionState.Idle);
  });

  it("rejects idle → generated", () => {
    expect(() => transition(SessionState.Idle, SessionState.Generated)).toThrow(
      "Invalid transition",
    );
  });

  it("rejects idle → confirming", () => {
    expect(() => transition(SessionState.Idle, SessionState.Confirming)).toThrow(
      "Invalid transition",
    );
  });
});

describe("mapActionToState", () => {
  it("continue from idle → collecting", () => {
    expect(mapActionToState(SessionAction.Continue, SessionState.Idle)).toBe(
      SessionState.Collecting,
    );
  });

  it("continue from collecting stays collecting", () => {
    expect(mapActionToState(SessionAction.Continue, SessionState.Collecting)).toBe(
      SessionState.Collecting,
    );
  });

  it("confirm from collecting → confirming", () => {
    expect(mapActionToState(SessionAction.Confirm, SessionState.Collecting)).toBe(
      SessionState.Confirming,
    );
  });

  it("generate from collecting → generated", () => {
    expect(mapActionToState(SessionAction.Generate, SessionState.Collecting)).toBe(
      SessionState.Generated,
    );
  });

  it("generate from confirming → generated", () => {
    expect(mapActionToState(SessionAction.Generate, SessionState.Confirming)).toBe(
      SessionState.Generated,
    );
  });

  it("new from any state → idle", () => {
    expect(mapActionToState(SessionAction.New, SessionState.Collecting)).toBe(SessionState.Idle);
    expect(mapActionToState(SessionAction.New, SessionState.Confirming)).toBe(SessionState.Idle);
    expect(mapActionToState(SessionAction.New, SessionState.Generated)).toBe(SessionState.Idle);
  });

  it("invalid transition preserves current state", () => {
    expect(mapActionToState(SessionAction.Confirm, SessionState.Idle)).toBe(SessionState.Idle);
    expect(mapActionToState(SessionAction.Generate, SessionState.Idle)).toBe(SessionState.Idle);
  });
});
