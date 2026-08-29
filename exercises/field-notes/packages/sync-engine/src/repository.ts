import type { RecordCommand, RecordPayload, RemoteRecord } from "../../core/src/contracts.ts";
import type { SyncRepository } from "./ports.ts";
import type {
  AttemptedCommand,
  CheckpointOutcome,
  CheckpointResult,
  ClaimedCommand,
  ConflictResolution,
  ConflictResolutionResult,
  DurableCommand,
  DurableCommandState,
  DurableConflict,
  LocalRecord,
  RepositorySnapshot,
} from "./types.ts";

function clone<T>(value: T): T {
  return structuredClone(value);
}

function same(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function terminal(state: DurableCommandState): boolean {
  return state.kind === "completed"
    || state.kind === "permanent"
    || state.kind === "superseded";
}

export type LocalMutationInput = {
  commandId: string;
  recordId: string;
  operation: "upsert" | "delete";
  payload: RecordPayload | null;
  createdAt: string;
  expectedLocalRevision?: number | null;
};

// [Implementation 6]
// 명령의 최초 시도 사본·lease·재시도·처리 결과·충돌을 저장합니다.
export class InMemorySyncRepository implements SyncRepository {
  readonly #records: LocalRecord[];
  readonly #commands: DurableCommand[];
  readonly #conflicts: DurableConflict[];
  readonly #checkpoints: RepositorySnapshot["checkpoints"];
  #sequence: number;
  #leaseSequence = 0;
  #generatedCommandSequence = 0;
  #generatedConflictSequence = 0;
  #failNextCheckpointReason: string | null = null;

  constructor(snapshot?: RepositorySnapshot) {
    this.#records = clone(snapshot?.records ?? []);
    this.#commands = clone(snapshot?.commands ?? []);
    this.#conflicts = clone(snapshot?.conflicts ?? []);
    this.#checkpoints = clone(snapshot?.checkpoints ?? []);
    this.#sequence = this.#commands.reduce((maximum, command) => Math.max(maximum, command.sequence), 0);
  }

  saveLocalMutation(input: LocalMutationInput): { record: LocalRecord; command: DurableCommand } {
    if (input.operation === "upsert" && input.payload === null) {
      throw new Error("upsert requires a payload");
    }
    if (input.operation === "delete" && input.payload !== null) {
      throw new Error("delete requires a null payload");
    }

    const existing = this.#records.find((record) => record.recordId === input.recordId);
    const currentRevision = existing?.localRevision ?? 0;
    if (input.expectedLocalRevision !== undefined
      && input.expectedLocalRevision !== null
      && input.expectedLocalRevision !== currentRevision) {
      throw new Error(`local revision mismatch: expected ${input.expectedLocalRevision}, got ${currentRevision}`);
    }
    if (this.#commands.some((entry) => entry.command.commandId === input.commandId)) {
      throw new Error(`duplicate command id: ${input.commandId}`);
    }

    const localRevision = currentRevision + 1;
    const record: LocalRecord = existing ?? {
      recordId: input.recordId,
      payload: null,
      deleted: false,
      localRevision: 0,
      knownRemoteVersion: null,
      syncState: "pending",
    };
    record.payload = clone(input.payload);
    record.deleted = input.operation === "delete";
    record.localRevision = localRevision;
    record.syncState = "pending";
    if (!existing) this.#records.push(record);

    const command: DurableCommand = {
      command: {
        commandId: input.commandId,
        recordId: input.recordId,
        operation: input.operation,
        baseVersion: record.knownRemoteVersion,
        localRevision,
        payload: clone(input.payload),
        createdAt: input.createdAt,
      },
      state: { kind: "pending" },
      sequence: ++this.#sequence,
    };
    this.#commands.push(command);
    return { record: clone(record), command: clone(command) };
  }

  async claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null> {
    const candidates = this.#commands
      .filter((entry) => this.#eligible(entry, input.now))
      .sort((left, right) => left.sequence - right.sequence);

    for (const entry of candidates) {
      const earlierBlocks = this.#commands.some((candidate) =>
        candidate.command.recordId === entry.command.recordId
        && candidate.sequence < entry.sequence
        && !terminal(candidate.state),
      );
      if (earlierBlocks) continue;

      let attempted: AttemptedCommand;
      let attempt: number;
      if (entry.state.kind === "pending") {
        attempted = clone(entry.command);
        attempt = 1;
      } else if (entry.state.kind === "retry_wait" || entry.state.kind === "in_flight") {
        attempted = clone(entry.state.attempted);
        attempt = entry.state.attempt + 1;
      } else {
        continue;
      }

      // 재시도할 때도 최초 시도 사본은 유지하고 lease 토큰만 새로 발급합니다.
      const lease = {
        token: `${input.workerId}:${entry.command.commandId}:${attempt}:${++this.#leaseSequence}`,
        owner: input.workerId,
        expiresAt: input.now + input.leaseDurationMs,
      };
      entry.state = { kind: "in_flight", attempted: clone(attempted), attempt, lease };
      const record = this.#record(entry.command.recordId);
      record.syncState = "in_flight";
      return {
        commandId: entry.command.commandId,
        attempted,
        attempt,
        lease: clone(lease),
        knownRemoteVersion: record.knownRemoteVersion,
      };
    }
    return null;
  }

  async checkpoint(
    claim: ClaimedCommand,
    outcome: CheckpointOutcome,
  ): Promise<CheckpointResult> {
    if (this.#failNextCheckpointReason !== null) {
      const reason = this.#failNextCheckpointReason;
      this.#failNextCheckpointReason = null;
      throw new Error(reason);
    }

    const entry = this.#commands.find((candidate) => candidate.command.commandId === claim.commandId);
    if (!entry || entry.state.kind !== "in_flight") throw new Error("command is not in flight");
    if (entry.state.lease.token !== claim.lease.token) throw new Error("stale lease token");
    if (!same(entry.state.attempted, claim.attempted)) throw new Error("attempted command changed");

    const attempt = entry.state.attempt;
    const record = this.#record(entry.command.recordId);
    const rebased: CheckpointResult["rebased"] = [];

    switch (outcome.kind) {
      case "success": {
        if (outcome.remote.recordId !== entry.command.recordId) throw new Error("remote record mismatch");
        entry.state = {
          kind: "completed",
          attempted: clone(claim.attempted),
          attempt,
          remoteVersion: outcome.remote.version,
          completedAt: outcome.completedAt,
        };
        record.knownRemoteVersion = outcome.remote.version;

        if (record.localRevision === claim.attempted.localRevision) {
          record.payload = clone(outcome.remote.payload);
          record.deleted = outcome.remote.deleted;
          record.syncState = "synced";
        } else {
          record.syncState = "pending";
        }
        rebased.push(...this.#rebasePending(entry, outcome.remote.version));
        break;
      }
      case "conflict": {
        const conflictId = `conflict-${++this.#generatedConflictSequence}`;
        const conflict: DurableConflict = {
          conflictId,
          commandId: entry.command.commandId,
          recordId: entry.command.recordId,
          attempted: clone(claim.attempted),
          local: { payload: clone(record.payload), localRevision: record.localRevision },
          remote: clone(outcome.remote),
          createdAt: outcome.createdAt,
        };
        this.#conflicts.push(conflict);
        entry.state = {
          kind: "conflict",
          attempted: clone(claim.attempted),
          attempt,
          conflictId,
        };
        record.syncState = "conflict";
        break;
      }
      case "retry_wait":
        entry.state = {
          kind: "retry_wait",
          attempted: clone(claim.attempted),
          attempt,
          nextAttemptAt: outcome.nextAttemptAt,
          reason: outcome.reason,
        };
        record.syncState = "retry_wait";
        break;
      case "blocked_auth":
        entry.state = {
          kind: "blocked_auth",
          attempted: clone(claim.attempted),
          attempt,
          reason: outcome.reason,
        };
        record.syncState = "blocked_auth";
        break;
      case "permanent":
        entry.state = {
          kind: "permanent",
          attempted: clone(claim.attempted),
          attempt,
          reason: outcome.reason,
        };
        record.syncState = "permanent";
        break;
    }

    this.#checkpoints.push({
      sequence: this.#checkpoints.length + 1,
      commandId: entry.command.commandId,
      leaseToken: claim.lease.token,
      outcome: outcome.kind,
    });
    return { commandId: entry.command.commandId, state: entry.state.kind, rebased };
  }

  async resumeBlockedAuth(now: number): Promise<number> {
    let resumed = 0;
    for (const entry of this.#commands) {
      if (entry.state.kind !== "blocked_auth") continue;
      entry.state = {
        kind: "retry_wait",
        attempted: clone(entry.state.attempted),
        attempt: entry.state.attempt,
        nextAttemptAt: now,
        reason: "credential-restored",
      };
      this.#record(entry.command.recordId).syncState = "retry_wait";
      resumed += 1;
    }
    return resumed;
  }

  // [Implementation 6-3]
  // 새 명령으로 충돌을 해결하고 아직 보내지 않은 명령만 새 기준 버전으로 바꿉니다.
  async resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult> {
    const conflict = this.#conflicts.find((candidate) => candidate.conflictId === conflictId);
    if (!conflict) throw new Error(`unknown conflict: ${conflictId}`);
    if (conflict.resolution) throw new Error(`conflict already resolved: ${conflictId}`);
    const original = this.#commands.find((entry) => entry.command.commandId === conflict.commandId);
    if (!original || original.state.kind !== "conflict") throw new Error("conflict command is unavailable");
    const record = this.#record(conflict.recordId);

    const later = this.#pendingCommandsAfter(original);

    if (resolution.kind === "remote") {
      this.#supersede(later, null, resolution.resolvedAt);
      conflict.resolution = { kind: "remote", resolvedAt: resolution.resolvedAt };
      original.state = {
        kind: "completed",
        attempted: clone(original.state.attempted),
        attempt: original.state.attempt,
        remoteVersion: conflict.remote?.version ?? null,
        completedAt: resolution.resolvedAt,
      };
      record.payload = clone(conflict.remote?.payload ?? null);
      record.deleted = conflict.remote?.deleted ?? true;
      record.knownRemoteVersion = conflict.remote?.version ?? null;
      record.syncState = "synced";
      return { conflict: clone(conflict), command: null };
    }

    const payload = resolution.kind === "merge" ? clone(resolution.payload) : clone(record.payload);
    if (resolution.kind === "merge") {
      record.payload = clone(payload);
      record.deleted = false;
      record.localRevision += 1;
    }
    const operation = record.deleted ? "delete" : "upsert";
    if (operation === "upsert" && payload === null) throw new Error("local resolution has no payload");
    if (this.#commands.some((entry) => entry.command.commandId === resolution.commandId)) {
      throw new Error(`duplicate resolution command: ${resolution.commandId}`);
    }

    const command: DurableCommand = {
      command: {
        commandId: resolution.commandId,
        recordId: record.recordId,
        operation,
        baseVersion: conflict.remote?.version ?? null,
        localRevision: record.localRevision,
        payload: operation === "delete" ? null : clone(payload),
        createdAt: resolution.createdAt,
      },
      state: { kind: "pending" },
      sequence: ++this.#sequence,
    };
    this.#supersede(later, resolution.commandId, resolution.resolvedAt);
    this.#commands.push(command);
    original.state = {
      kind: "completed",
      attempted: clone(original.state.attempted),
      attempt: original.state.attempt,
      remoteVersion: conflict.remote?.version ?? null,
      completedAt: resolution.resolvedAt,
    };
    conflict.resolution = {
      kind: resolution.kind,
      resolvedAt: resolution.resolvedAt,
      resolutionCommandId: resolution.commandId,
    };
    record.knownRemoteVersion = conflict.remote?.version ?? null;
    record.syncState = "pending";
    return { conflict: clone(conflict), command: clone(command) };
  }

  async snapshot(): Promise<RepositorySnapshot> {
    return {
      records: clone(this.#records).sort((a, b) => a.recordId.localeCompare(b.recordId)),
      commands: clone(this.#commands).sort((a, b) => a.sequence - b.sequence),
      conflicts: clone(this.#conflicts),
      checkpoints: clone(this.#checkpoints),
    };
  }

  failNextCheckpoint(reason = "injected checkpoint failure"): void {
    this.#failNextCheckpointReason = reason;
  }

  #eligible(entry: DurableCommand, now: number): boolean {
    if (entry.state.kind === "pending") return true;
    if (entry.state.kind === "retry_wait") return entry.state.nextAttemptAt <= now;
    if (entry.state.kind === "in_flight") return entry.state.lease.expiresAt <= now;
    return false;
  }

  #record(recordId: string): LocalRecord {
    const record = this.#records.find((candidate) => candidate.recordId === recordId);
    if (!record) throw new Error(`missing local record: ${recordId}`);
    return record;
  }

  #pendingCommandsAfter(original: DurableCommand): DurableCommand[] {
    const later = this.#commands.filter((entry) =>
      entry.command.recordId === original.command.recordId
      && entry.sequence > original.sequence
      && !terminal(entry.state),
    );
    const invalid = later.find((entry) => entry.state.kind !== "pending");
    if (invalid) {
      throw new Error(
        `conflict resolution found an attempted later command: ${invalid.command.commandId}`,
      );
    }
    return later;
  }

  #supersede(
    commands: DurableCommand[],
    supersededBy: string | null,
    completedAt: number,
  ): void {
    for (const entry of commands) {
      entry.state = { kind: "superseded", supersededBy, completedAt };
    }
  }

  #rebasePending(
    completed: DurableCommand,
    baseVersion: number,
  ): CheckpointResult["rebased"] {
    const result: CheckpointResult["rebased"] = [];
    for (const entry of this.#commands) {
      if (entry.sequence <= completed.sequence
        || entry.command.recordId !== completed.command.recordId
        || entry.state.kind !== "pending") continue;
      const previousCommandId = entry.command.commandId;
      // 아직 보내지 않은 명령만 새 기준 버전과 새 ID로 바꿉니다. 이미 시도한 명령은 수정하지 않습니다.
      const commandId = `${previousCommandId}-rebase-${++this.#generatedCommandSequence}`;
      entry.command = { ...clone(entry.command), commandId, baseVersion };
      result.push({ previousCommandId, commandId, baseVersion });
    }
    return result;
  }
}
