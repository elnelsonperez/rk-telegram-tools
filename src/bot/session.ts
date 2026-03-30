export enum SessionState {
  Idle = "idle",
  Collecting = "collecting",
  Confirming = "confirming",
  Generated = "generated",
}

export enum SessionAction {
  Continue = "continue",
  Confirm = "confirm",
  Generate = "generate",
  New = "new",
}

const VALID_TRANSITIONS: Record<SessionState, SessionState[]> = {
  [SessionState.Idle]: [SessionState.Collecting],
  [SessionState.Collecting]: [SessionState.Confirming, SessionState.Generated, SessionState.Idle],
  [SessionState.Confirming]: [SessionState.Generated, SessionState.Collecting, SessionState.Idle],
  [SessionState.Generated]: [SessionState.Collecting, SessionState.Idle],
};

export function transition(current: SessionState, next: SessionState): SessionState {
  if (!VALID_TRANSITIONS[current].includes(next)) {
    throw new Error(`Invalid transition: ${current} → ${next}`);
  }
  return next;
}

export function mapActionToState(action: SessionAction, current: SessionState): SessionState {
  const target = actionToTarget(action, current);
  if (!VALID_TRANSITIONS[current].includes(target)) {
    return current;
  }
  return target;
}

function actionToTarget(action: SessionAction, current: SessionState): SessionState {
  switch (action) {
    case SessionAction.Continue:
      return current === SessionState.Idle ? SessionState.Collecting : current;
    case SessionAction.Confirm:
      return SessionState.Confirming;
    case SessionAction.Generate:
      return SessionState.Generated;
    case SessionAction.New:
      return SessionState.Idle;
  }
}
