import type {
  LifecycleClock,
  NotificationOwnerIdGenerator,
  NotificationStateRepository,
  ProcessedIntentClaimPort,
  ProcessedIntentClaimResult,
} from "./ports.ts";
import type {
  NotificationEnvelope,
  NotificationNavigationIntent,
  NotificationParseResult,
  NotificationPrepareResult,
  ProcessedIntentClaim,
  ProcessedIntentCompletion,
} from "./types.ts";

const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

function plainObject(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, expected: string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === [...expected].sort()[index]);
}

export function parseNotificationEnvelope(value: unknown): NotificationParseResult {
  const envelope = plainObject(value);
  if (!envelope) return { kind: "invalid", reason: "not-an-object" };
  if (!exactKeys(envelope, ["schemaVersion", "messageId", "accountId", "intent"])) {
    return { kind: "invalid", reason: "unexpected-field" };
  }
  if (envelope.schemaVersion !== 1) return { kind: "invalid", reason: "unsupported-schema" };
  if (typeof envelope.messageId !== "string" || !ID.test(envelope.messageId)) {
    return { kind: "invalid", reason: "invalid-message-id" };
  }
  if (typeof envelope.accountId !== "string" || !ID.test(envelope.accountId)) {
    return { kind: "invalid", reason: "invalid-account-id" };
  }

  const intent = plainObject(envelope.intent);
  if (!intent || typeof intent.kind !== "string") {
    return { kind: "invalid", reason: "invalid-intent" };
  }
  if (intent.kind === "sync-blocked") {
    if (!exactKeys(intent, ["kind"])) return { kind: "invalid", reason: "invalid-intent" };
  } else if (intent.kind === "record-conflict" || intent.kind === "record-updated") {
    if (!exactKeys(intent, ["kind", "recordId"])) {
      return { kind: "invalid", reason: "invalid-intent" };
    }
    if (typeof intent.recordId !== "string" || !ID.test(intent.recordId)) {
      return { kind: "invalid", reason: "invalid-record-id" };
    }
  } else {
    return { kind: "invalid", reason: "invalid-intent" };
  }

  return { kind: "valid", envelope: value as NotificationEnvelope };
}

export class SequentialNotificationOwnerIds implements NotificationOwnerIdGenerator {
  #sequence = 0;
  next(messageId: string): string {
    return `${messageId}:owner:${++this.#sequence}`;
  }
}

export class InMemoryProcessedIntentClaims implements ProcessedIntentClaimPort {
  readonly #entries = new Map<string, {
    state: "claimed" | "completed";
    claim?: ProcessedIntentClaim;
    outcome?: ProcessedIntentCompletion;
  }>();
  #sequence = 0;

  async claim(input: {
    messageId: string;
    ownerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ProcessedIntentClaimResult> {
    const existing = this.#entries.get(input.messageId);
    if (existing?.state === "completed") return { kind: "duplicate" };
    if (existing?.state === "claimed" && existing.claim && existing.claim.expiresAt > input.now) {
      return { kind: "busy" };
    }
    const claim = {
      messageId: input.messageId,
      token: `${input.messageId}:claim:${++this.#sequence}`,
      ownerId: input.ownerId,
      expiresAt: input.now + input.leaseDurationMs,
    };
    this.#entries.set(input.messageId, { state: "claimed", claim });
    return { kind: "claimed", claim: structuredClone(claim) };
  }

  async complete(claim: ProcessedIntentClaim, outcome: ProcessedIntentCompletion = { kind: "completed" }): Promise<void> {
    const existing = this.#entries.get(claim.messageId);
    if (existing?.state !== "claimed" || existing.claim?.token !== claim.token) {
      throw new Error("stale processed-intent claim");
    }
    this.#entries.set(claim.messageId, { state: "completed", outcome: structuredClone(outcome) });
  }

  async release(claim: ProcessedIntentClaim): Promise<void> {
    const existing = this.#entries.get(claim.messageId);
    if (existing?.state === "claimed" && existing.claim?.token === claim.token) {
      this.#entries.delete(claim.messageId);
    }
  }
}

// [Implementation 8-1]
// 알림 ID를 먼저 저장하고 현재 저장 상태를 조회해 이동할 화면을 정합니다.
export class NotificationCoordinator {
  readonly #state: NotificationStateRepository;
  readonly #claims: ProcessedIntentClaimPort;
  readonly #clock: LifecycleClock;
  readonly #owners: NotificationOwnerIdGenerator;
  readonly #leaseDurationMs: number;

  constructor(input: {
    state: NotificationStateRepository;
    claims: ProcessedIntentClaimPort;
    clock: LifecycleClock;
    owners: NotificationOwnerIdGenerator;
    leaseDurationMs?: number;
  }) {
    this.#state = input.state;
    this.#claims = input.claims;
    this.#clock = input.clock;
    this.#owners = input.owners;
    this.#leaseDurationMs = input.leaseDurationMs ?? 30_000;
  }

  async prepare(raw: unknown): Promise<NotificationPrepareResult> {
    const parsed = parseNotificationEnvelope(raw);
    if (parsed.kind === "invalid") {
      return { kind: "rejected", reason: "malformed", parseReason: parsed.reason };
    }

    await this.#state.ready();
    const account = await this.#state.currentAccount();
    if (account.kind === "none") return { kind: "rejected", reason: "account-unavailable" };
    if (account.kind === "deleted") return { kind: "rejected", reason: "account-deleted" };
    if (account.accountId !== parsed.envelope.accountId) {
      return { kind: "rejected", reason: "account-mismatch" };
    }

    // `messageId` 사용권을 먼저 저장해 여러 실행이 같은 알림을 동시에 적용하지 않게 합니다.
    const claimed = await this.#claims.claim({
      messageId: parsed.envelope.messageId,
      ownerId: this.#owners.next(parsed.envelope.messageId),
      now: this.#clock.now(),
      leaseDurationMs: this.#leaseDurationMs,
    });
    if (claimed.kind === "duplicate") return { kind: "rejected", reason: "duplicate" };
    if (claimed.kind === "busy") return { kind: "rejected", reason: "in-progress" };

    return this.#route(parsed.envelope, claimed.claim);
  }

  async acknowledge(result: NotificationPrepareResult): Promise<void> {
    // 실제 화면 이동을 적용한 뒤 완료 처리해야 프로세스가 중간에 종료돼도 다시 시도할 수 있습니다.
    if (result.kind === "prepared") {
      await this.#claims.complete(result.claim, { kind: "completed" });
      return;
    }
    if (result.claim) {
      await this.#claims.complete(result.claim, { kind: "terminal", code: result.reason });
    }
  }

  async release(result: NotificationPrepareResult): Promise<void> {
    const claim = result.kind === "prepared" ? result.claim : result.claim;
    if (claim) await this.#claims.release(claim);
  }

  async #route(
    envelope: NotificationEnvelope,
    claim: ProcessedIntentClaim,
  ): Promise<NotificationPrepareResult> {
    const intent = envelope.intent;
    if (intent.kind === "sync-blocked") {
      if (!await this.#state.isSyncBlocked()) {
        return this.#terminal("stale", claim, { kind: "open-records" });
      }
      return this.#prepared(envelope, claim, { kind: "open-sync", focus: "blocked" });
    }

    const recordState = await this.#state.recordState(intent.recordId);
    if (recordState === "deleted") {
      return this.#terminal("record-deleted", claim, { kind: "open-records" });
    }
    if (recordState === "missing") {
      return this.#terminal("record-missing", claim, { kind: "open-records" });
    }

    if (intent.kind === "record-updated") {
      return this.#prepared(envelope, claim, { kind: "open-record", recordId: intent.recordId });
    }

    const conflict = await this.#state.conflictState(intent.recordId);
    if (conflict === "active") {
      return this.#prepared(envelope, claim, {
        kind: "open-sync",
        focus: "conflict",
        recordId: intent.recordId,
      });
    }
    return this.#terminal("stale", claim, { kind: "open-record", recordId: intent.recordId });
  }

  #prepared(
    envelope: NotificationEnvelope,
    claim: ProcessedIntentClaim,
    navigation: NotificationNavigationIntent,
  ): NotificationPrepareResult {
    return { kind: "prepared", envelope, claim, navigation };
  }

  #terminal(
    reason: "stale" | "record-deleted" | "record-missing",
    claim: ProcessedIntentClaim,
    safeNavigation: NotificationNavigationIntent,
  ): NotificationPrepareResult {
    return { kind: "rejected", reason, claim, safeNavigation };
  }
}
