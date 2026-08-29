import type {
  Fault,
  FaultPlan,
  HistoryEvent,
  HistoryEventInput,
  MemoizedResponse,
  RecordCommand,
  RemoteRecord,
  ServerSnapshot,
  WireResponse,
} from "./types.ts";

function clone<T>(value: T): T {
  return structuredClone(value);
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, stableValue(child)]),
    );
  }
  return value;
}

function commandFingerprint(command: RecordCommand): string {
  return JSON.stringify(stableValue(command));
}

function isRecordCommand(value: unknown): value is RecordCommand {
  if (!value || typeof value !== "object") return false;
  const command = value as Partial<RecordCommand>;
  if (typeof command.commandId !== "string" || command.commandId.length === 0) return false;
  if (typeof command.recordId !== "string" || command.recordId.length === 0) return false;
  if (command.operation !== "upsert" && command.operation !== "delete") return false;
  if (
    command.baseVersion !== null
    && (
      command.baseVersion === undefined
      || !Number.isInteger(command.baseVersion)
      || command.baseVersion < 1
    )
  ) return false;
  if (!Number.isInteger(command.localRevision) || (command.localRevision ?? 0) < 1) return false;
  if (typeof command.createdAt !== "string" || Number.isNaN(Date.parse(command.createdAt))) return false;
  if (command.operation === "delete") return command.payload === null;
  if (!command.payload || typeof command.payload !== "object") return false;
  return typeof command.payload.title === "string"
    && typeof command.payload.notes === "string"
    && ["draft", "open", "resolved"].includes(command.payload.status ?? "")
    && typeof command.payload.observedAt === "string"
    && !Number.isNaN(Date.parse(command.payload.observedAt));
}

function replayed(response: MemoizedResponse): MemoizedResponse {
  return {
    status: response.status,
    body: { ...clone(response.body), replayed: true },
  } as MemoizedResponse;
}

async function delay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (milliseconds <= 0) return;
  if (signal?.aborted) throw signal.reason ?? new DOMException("Aborted", "AbortError");
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", abort, { once: true });
    (timer as typeof timer & { unref?: () => void }).unref?.();
  });
}

export class ResponseLostError extends Error {
  readonly commandId: string;

  constructor(commandId: string) {
    super(`response lost after remote processing: ${commandId}`);
    this.name = "ResponseLostError";
    this.commandId = commandId;
  }
}

// [Implementation 5]
// 각 명령을 한 번만 적용하고 원격 처리 실패를 결정적으로 재현합니다.
export class DeterministicFaultServer {
  readonly #records = new Map<string, RemoteRecord>();
  readonly #memoized = new Map<string, { fingerprint: string; response: MemoizedResponse }>();
  readonly #applyCount = new Map<string, number>();
  readonly #faults: FaultPlan[] = [];
  readonly #history: HistoryEvent[] = [];
  #sequence = 0;

  enqueueFault(plan: FaultPlan): void {
    this.#faults.push(clone(plan));
  }

  replaceRecord(record: RemoteRecord): void {
    this.#records.set(record.recordId, clone(record));
  }

  reset(): void {
    this.#records.clear();
    this.#memoized.clear();
    this.#applyCount.clear();
    this.#faults.length = 0;
    this.#history.length = 0;
    this.#sequence = 0;
  }

  async execute(input: unknown, signal?: AbortSignal): Promise<WireResponse> {
    if (signal?.aborted) throw signal.reason ?? new DOMException("Aborted", "AbortError");
    if (!isRecordCommand(input)) {
      const candidate = input && typeof input === "object"
        ? input as { commandId?: unknown }
        : null;
      return {
        status: 400,
        body: {
          kind: "validation-failure",
          commandId: typeof candidate?.commandId === "string" ? candidate.commandId : null,
          reason: "invalid-command",
        },
      };
    }
    const command = input;

    const fingerprint = commandFingerprint(command);
    // 같은 `commandId`에 다른 내용을 넣으면 첫 결과를 안전하게 재사용할 수 없으므로 거부합니다.
    const stored = this.#memoized.get(command.commandId);
    if (stored) {
      if (stored.fingerprint !== fingerprint) {
        this.#push({ kind: "identity-reuse-rejected", commandId: command.commandId });
        return {
          status: 409,
          body: {
            kind: "command-identity-reuse",
            commandId: command.commandId,
            reason: "same-command-id-different-attempted-command",
          },
        };
      }
      this.#push({ kind: "replayed", commandId: command.commandId });
      return replayed(stored.response);
    }

    const fault = this.#consumeFault(command.commandId);
    if (fault?.kind === "delay") await delay(fault.milliseconds, signal);
    if (fault?.kind === "unauthorized") {
      this.#push({ kind: "unauthorized", commandId: command.commandId });
      return { status: 401, body: { kind: "unauthorized", commandId: command.commandId } };
    }
    if (fault?.kind === "permanent-validation") {
      const response: MemoizedResponse = {
        status: 422,
        body: {
          kind: "permanent-failure",
          commandId: command.commandId,
          reason: fault.reason,
          replayed: false,
        },
      };
      this.#memoize(command, fingerprint, response, "permanent-failure");
      return clone(response);
    }

    const current = this.#records.get(command.recordId) ?? null;
    const expectedBaseVersion = current?.version ?? null;
    let canonical: MemoizedResponse;

    if (command.baseVersion !== expectedBaseVersion) {
      canonical = {
        status: 409,
        body: {
          kind: "conflict",
          commandId: command.commandId,
          recordId: command.recordId,
          expectedBaseVersion,
          current: current ? clone(current) : null,
          replayed: false,
        },
      };
      this.#memoize(command, fingerprint, canonical, "conflict");
    } else {
      const record: RemoteRecord = {
        recordId: command.recordId,
        payload: command.operation === "delete" ? null : clone(command.payload),
        version: (current?.version ?? 0) + 1,
        deleted: command.operation === "delete",
      };
      this.#records.set(command.recordId, record);
      this.#applyCount.set(command.commandId, (this.#applyCount.get(command.commandId) ?? 0) + 1);
      this.#push({
        kind: "applied",
        commandId: command.commandId,
        recordId: command.recordId,
        version: record.version,
      });
      canonical = {
        status: 200,
        body: {
          kind: "success",
          commandId: command.commandId,
          record: clone(record),
          replayed: false,
        },
      };
      this.#memoize(command, fingerprint, canonical, "success");
    }

    if (fault?.kind === "response-loss") {
      // 서버 변경과 결과 저장을 끝낸 뒤 응답만 잃게 해 처리 여부를 모르는 상황을 재현합니다.
      this.#push({ kind: "response-lost", commandId: command.commandId });
      throw new ResponseLostError(command.commandId);
    }
    if (fault?.kind === "malformed-success") {
      this.#push({ kind: "malformed-sent", commandId: command.commandId });
      return { status: 200, body: fault.body ?? { kind: "success", commandId: command.commandId } };
    }
    if (fault?.kind === "version-regression" && canonical.status === 200) {
      const by = Math.max(1, fault.by ?? 1);
      const version = Math.max(0, canonical.body.record.version - by);
      this.#push({ kind: "version-regression-sent", commandId: command.commandId, version });
      return {
        status: 200,
        body: {
          ...clone(canonical.body),
          record: { ...clone(canonical.body.record), version },
        },
      };
    }

    return clone(canonical);
  }

  snapshot(): ServerSnapshot {
    return {
      records: [...this.#records.values()].map(clone).sort((a, b) => a.recordId.localeCompare(b.recordId)),
      memoizedCommandIds: [...this.#memoized.keys()].sort(),
      applyCountByCommand: Object.fromEntries([...this.#applyCount.entries()].sort()),
      pendingFaults: this.#faults.map(clone),
      history: this.#history.map(clone),
    };
  }

  #consumeFault(commandId: string): Fault | null {
    const index = this.#faults.findIndex((plan) => plan.commandId === undefined || plan.commandId === commandId);
    if (index < 0) return null;
    const [plan] = this.#faults.splice(index, 1);
    this.#push({ kind: "fault-consumed", commandId, fault: plan.fault.kind });
    return plan.fault;
  }

  #memoize(
    command: RecordCommand,
    fingerprint: string,
    response: MemoizedResponse,
    result: "success" | "conflict" | "permanent-failure",
  ): void {
    this.#memoized.set(command.commandId, { fingerprint, response: clone(response) });
    this.#push({ kind: "memoized", commandId: command.commandId, result });
  }

  #push(event: HistoryEventInput): void {
    this.#history.push({ sequence: ++this.#sequence, ...event } as HistoryEvent);
  }
}
