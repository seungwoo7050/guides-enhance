import type {
  NavigationDecision,
  NavigationIntent,
  NavigationIntentSource,
} from "./contracts.ts";

export const MAX_RECORD_ID_LENGTH = 64;
const MAX_INPUT_LENGTH = 2048;
const RECORD_ID = /^[a-z0-9][a-z0-9_-]*$/;

export type RecordIdResult =
  | { kind: "valid"; recordId: string }
  | { kind: "invalid"; reason: "empty" | "too-long" | "unsupported-characters" };

type RawPathResult =
  | { kind: "segments"; segments: string[] }
  | { kind: "invalid"; reason: "invalid-input-length" | "malformed-encoding" | "unexpected-scheme" };

// [Implementation 2]
// 화면 이동 입력을 검증하고 중복 요청을 거른 뒤 안전한 경로를 선택합니다.
export function normalizeRecordId(input: string): RecordIdResult {
  const recordId = input.trim().toLocaleLowerCase("en-US");
  if (recordId.length === 0) return { kind: "invalid", reason: "empty" };
  if ([...recordId].length > MAX_RECORD_ID_LENGTH) {
    return { kind: "invalid", reason: "too-long" };
  }
  if (!RECORD_ID.test(recordId)) {
    return { kind: "invalid", reason: "unsupported-characters" };
  }
  return { kind: "valid", recordId };
}

function rawPathSegments(input: string, expectedScheme: string): RawPathResult {
  if (input.length === 0 || input.length > MAX_INPUT_LENGTH) {
    return { kind: "invalid", reason: "invalid-input-length" };
  }

  try {
    if (input.startsWith("/")) {
      const url = new URL(input, "https://field-notes.invalid");
      return {
        kind: "segments",
        segments: url.pathname
          .split("/")
          .filter(Boolean)
          .map((segment) => decodeURIComponent(segment)),
      };
    }

    const url = new URL(input);
    const actualScheme = url.protocol.slice(0, -1).toLocaleLowerCase("en-US");
    const normalizedExpectedScheme = expectedScheme.toLocaleLowerCase("en-US");
    const isExpoDevelopmentLink = actualScheme === "exp" || actualScheme === "exps";
    if (actualScheme !== normalizedExpectedScheme && !isExpoDevelopmentLink) {
      return { kind: "invalid", reason: "unexpected-scheme" };
    }

    const hostSegments = actualScheme === normalizedExpectedScheme && url.hostname
      ? [url.hostname]
      : [];
    const encodedSegments = url.pathname.split("/").filter(Boolean);
    let segments = [...hostSegments, ...encodedSegments].map((segment) =>
      decodeURIComponent(segment),
    );
    const expoSeparator = segments.indexOf("--");
    if (isExpoDevelopmentLink) {
      if (expoSeparator < 0) {
        return { kind: "invalid", reason: "unexpected-scheme" };
      }
      segments = segments.slice(expoSeparator + 1);
    }
    if (segments[0] === "app") segments = segments.slice(1);
    return { kind: "segments", segments };
  } catch {
    return { kind: "invalid", reason: "malformed-encoding" };
  }
}

export function parseNavigationIntent(
  input: string,
  source: NavigationIntentSource = "link",
  expectedScheme = "fieldnotes",
): NavigationIntent {
  const result = rawPathSegments(input, expectedScheme);
  if (result.kind === "invalid") {
    return { kind: "invalid", reason: result.reason, source };
  }

  const { segments } = result;
  if (segments.length === 0 || (segments.length === 1 && segments[0] === "records")) {
    return { kind: "records", source };
  }
  if (segments.length === 1 && segments[0] === "sync") {
    return { kind: "open-sync", source };
  }
  if (segments.length === 1 && segments[0] === "settings") {
    return { kind: "open-settings", source };
  }
  if (
    segments[0] === "records"
    && (segments.length === 2 || (segments.length === 3 && segments[2] === "edit"))
  ) {
    const normalized = normalizeRecordId(segments[1] ?? "");
    if (normalized.kind === "invalid") {
      return { kind: "invalid", reason: `invalid-record-id:${normalized.reason}`, source };
    }
    return {
      kind: "open-record",
      recordId: normalized.recordId,
      destination: segments[2] === "edit" ? "edit" : "detail",
      source,
    };
  }
  return { kind: "invalid", reason: "unsupported-route", source };
}

/** 같은 화면 요청은 전달 경로가 달라도 중복으로 판단하도록 `source`를 키에서 제외합니다. */
export function navigationIntentKey(intent: NavigationIntent): string {
  switch (intent.kind) {
    case "records":
      return "records";
    case "open-record":
      return `record:${intent.recordId}:${intent.destination}`;
    case "open-sync":
      return "sync";
    case "open-settings":
      return "settings";
    case "invalid":
      return `invalid:${intent.reason}`;
  }
}

export async function decideNavigation(input: {
  intent: NavigationIntent;
  alreadyProcessed: boolean;
  recordExists(recordId: string): Promise<boolean>;
}): Promise<NavigationDecision> {
  if (input.alreadyProcessed) return { kind: "duplicate" };
  const { intent } = input;
  switch (intent.kind) {
    case "records":
      return { kind: "navigate", href: "/records" };
    case "open-sync":
      return { kind: "navigate", href: "/sync" };
    case "open-settings":
      return { kind: "navigate", href: "/settings" };
    case "invalid":
      return { kind: "invalid", reason: intent.reason, fallbackHref: "/records" };
    case "open-record":
      if (!await input.recordExists(intent.recordId)) {
        return { kind: "missing-record", recordId: intent.recordId, fallbackHref: "/records" };
      }
      return {
        kind: "navigate",
        href: intent.destination === "edit"
          ? `/records/${encodeURIComponent(intent.recordId)}/edit`
          : `/records/${encodeURIComponent(intent.recordId)}`,
      };
  }
}

export class RecentIntentSet {
  readonly #keys = new Set<string>();
  readonly #capacity: number;

  public constructor(capacity = 32) {
    if (!Number.isInteger(capacity) || capacity <= 0) {
      throw new RangeError("recent intent capacity must be a positive integer");
    }
    this.#capacity = capacity;
  }

  public accept(key: string): boolean {
    if (this.#keys.has(key)) return false;
    this.#keys.add(key);
    if (this.#keys.size > this.#capacity) {
      const oldest = this.#keys.values().next().value as string | undefined;
      if (oldest !== undefined) this.#keys.delete(oldest);
    }
    return true;
  }

  public has(key: string): boolean {
    return this.#keys.has(key);
  }

  public forget(key: string): void {
    this.#keys.delete(key);
  }
}

/** 첫 화면을 정하는 동안 들어온 요청은 가장 최근 항목 하나만 보관합니다. */
export class LatestNavigationIntentBuffer {
  #latest: NavigationIntent | null = null;

  public offer(intent: NavigationIntent): void {
    this.#latest = intent;
  }

  public take(): NavigationIntent | null {
    const intent = this.#latest;
    this.#latest = null;
    return intent;
  }
}

export type RouteReservation = {
  commit(): void;
  release(): void;
};

/** 검증을 마친 이동 요청을 제한된 개수만 기억해 같은 프로세스에서 중복 적용되지 않게 합니다. */
export class CrossSourceRouteArbiter {
  readonly #recent: RecentIntentSet;
  readonly #pending = new Set<string>();

  public constructor(capacity = 32) {
    this.#recent = new RecentIntentSet(capacity);
  }

  public reserve(routeKey: string): RouteReservation | null {
    if (routeKey.length === 0) throw new RangeError("route key must not be empty");
    if (this.#pending.has(routeKey) || this.#recent.has(routeKey)) return null;
    this.#pending.add(routeKey);
    let settled = false;
    return {
      commit: () => {
        if (settled) return;
        settled = true;
        this.#pending.delete(routeKey);
        this.#recent.accept(routeKey);
      },
      release: () => {
        if (settled) return;
        settled = true;
        this.#pending.delete(routeKey);
      },
    };
  }
}

export function applyReservedRoute(
  reservation: RouteReservation,
  apply: () => void,
): void {
  try {
    apply();
    reservation.commit();
  } catch (error) {
    reservation.release();
    throw error;
  }
}

export function decideDraftBack(dirty: boolean): "leave" | "confirm-discard" {
  return dirty ? "confirm-discard" : "leave";
}

export class OneShotNavigationPermit {
  #granted = false;

  public grant(): void {
    this.#granted = true;
  }

  public consume(): boolean {
    const granted = this.#granted;
    this.#granted = false;
    return granted;
  }

  public revoke(): void {
    this.#granted = false;
  }
}

export function handlePreventedDraftNavigation(
  permit: OneShotNavigationPermit,
  confirmDiscard: (discard: () => void) => void,
  dispatch: () => void,
): "bypassed" | "confirmation-requested" {
  if (permit.consume()) {
    dispatch();
    return "bypassed";
  }
  confirmDiscard(() => {
    permit.grant();
    try {
      dispatch();
    } finally {
      permit.revoke();
    }
  });
  return "confirmation-requested";
}

export function requestDraftLeave(
  dirty: boolean,
  confirmDiscard: (discard: () => void) => void,
  leave: () => void,
): "left" | "confirmation-requested" {
  if (decideDraftBack(dirty) === "leave") {
    leave();
    return "left";
  }
  confirmDiscard(leave);
  return "confirmation-requested";
}
