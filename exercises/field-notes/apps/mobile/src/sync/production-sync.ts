import type {
  RecordCommand,
  RecordPayload,
  RemoteRecord,
} from "@field-notes/core";
import {
  BoundedSyncWorker,
  FixedSyncBudget,
  type CheckpointOutcome,
  type CheckpointResult,
  type ClaimedCommand,
  type ConflictResolution,
  type ConflictResolutionResult,
  type DurableCommand,
  type DurableCommandState,
  type DurableConflict,
  type LocalRecord,
  type RepositorySnapshot,
  type SyncRepository,
  type SyncTransport,
  type WireResponse,
} from "@field-notes/sync-engine";
import {
  LifecycleSyncCoordinator,
  SequentialWorkerIdGenerator,
  SystemLifecycleClock,
  TimerDeadlineScheduler,
} from "@field-notes/lifecycle-engine";
import type { SQLiteDatabase } from "expo-sqlite";
import type {
  ConflictRow,
  OutboxRow,
  RecordRow,
  SQLiteFieldNotesRepository,
} from "../storage/SQLiteFieldNotesRepository";
import { createOpaqueId } from "../storage/SQLiteFieldNotesRepository";

function clone<T>(value: T): T {
  return structuredClone(value);
}

function parseJson<T>(value: string | null): T | null {
  return value === null ? null : JSON.parse(value) as T;
}

function recordCommand(row: OutboxRow): RecordCommand {
  return {
    commandId: row.command_id,
    recordId: row.record_id,
    operation: row.operation,
    baseVersion: row.base_version,
    localRevision: row.local_revision,
    payload: parseJson<RecordPayload>(row.payload_json),
    createdAt: row.created_at,
  };
}

function durableState(row: OutboxRow): DurableCommandState {
  const attempted = parseJson<RecordCommand>(row.attempted_json) ?? recordCommand(row);
  switch (row.state) {
    case "pending":
      return { kind: "pending" };
    case "claimed":
      if (!row.lease_token || !row.lease_owner || row.lease_expires_at === null) {
        return {
          kind: "retry_wait",
          attempted,
          attempt: row.attempt_count,
          nextAttemptAt: 0,
          reason: "incomplete-lease",
        };
      }
      return {
        kind: "in_flight",
        attempted,
        attempt: row.attempt_count,
        lease: {
          token: row.lease_token,
          owner: row.lease_owner,
          expiresAt: row.lease_expires_at,
        },
      };
    case "retry-wait":
      return {
        kind: "retry_wait",
        attempted,
        attempt: row.attempt_count,
        nextAttemptAt: row.next_attempt_at ?? 0,
        reason: row.last_error ?? "retry",
      };
    case "blocked-auth":
      return {
        kind: "blocked_auth",
        attempted,
        attempt: row.attempt_count,
        reason: row.last_error ?? "unauthorized",
      };
    case "conflict":
      return {
        kind: "conflict",
        attempted,
        attempt: row.attempt_count,
        conflictId: row.conflict_id ?? "missing-conflict-id",
      };
    case "permanent-failure":
      return {
        kind: "permanent",
        attempted,
        attempt: row.attempt_count,
        reason: row.last_error ?? "permanent-failure",
      };
    case "superseded":
      return {
        kind: "superseded",
        supersededBy: row.superseded_by,
        completedAt: row.completed_at ?? 0,
      };
    case "applied":
      return {
        kind: "completed",
        attempted,
        attempt: row.attempt_count,
        remoteVersion: row.completed_remote_version,
        completedAt: row.completed_at ?? 0,
      };
  }
}

function localRecord(row: RecordRow): LocalRecord {
  const payload: RecordPayload = {
    title: row.title,
    notes: row.notes,
    status: row.status,
    observedAt: row.observed_at,
    ...(row.location_json
      ? { location: JSON.parse(row.location_json) as RecordPayload["location"] }
      : {}),
  };
  const syncState: LocalRecord["syncState"] = row.sync_state === "syncing"
    ? "in_flight"
    : row.sync_state === "retry-wait"
      ? "retry_wait"
      : row.sync_state === "blocked-auth"
        ? "blocked_auth"
        : row.sync_state === "failed"
          ? "permanent"
          : row.sync_state === "conflict"
            ? "conflict"
            : row.sync_state === "synced"
              ? "synced"
              : "pending";
  return {
    recordId: row.id,
    payload: row.deleted_at_local ? null : payload,
    deleted: row.deleted_at_local !== null,
    localRevision: row.local_revision,
    knownRemoteVersion: row.remote_version,
    syncState,
  };
}

function durableConflict(row: ConflictRow): DurableConflict {
  return {
    conflictId: row.conflict_id,
    commandId: row.command_id,
    recordId: row.record_id,
    attempted: JSON.parse(row.attempted_json) as RecordCommand,
    local: {
      payload: parseJson<RecordPayload>(row.local_payload_json),
      localRevision: row.local_revision,
    },
    remote: parseJson<RemoteRecord>(row.remote_json),
    createdAt: row.created_at,
    ...(row.resolution_json
      ? { resolution: JSON.parse(row.resolution_json) as DurableConflict["resolution"] }
      : {}),
  };
}

function recordPayload(row: RecordRow): RecordPayload {
  return {
    title: row.title,
    notes: row.notes,
    status: row.status,
    observedAt: row.observed_at,
    ...(row.location_json
      ? { location: JSON.parse(row.location_json) as RecordPayload["location"] }
      : {}),
  };
}

export class FetchSyncTransport implements SyncTransport {
  readonly #endpoint: string;
  readonly #credential: () => Promise<string | null>;
  readonly #timeoutMs: number;

  constructor(input: {
    endpoint: string;
    credential: () => Promise<string | null>;
    timeoutMs?: number;
  }) {
    this.#endpoint = input.endpoint.replace(/\/$/, "");
    this.#credential = input.credential;
    this.#timeoutMs = input.timeoutMs ?? 15_000;
  }

  async send(command: RecordCommand, signal: AbortSignal): Promise<WireResponse> {
    const controller = new AbortController();
    const relay = () => controller.abort(signal.reason);
    signal.addEventListener("abort", relay, { once: true });
    const timer = setTimeout(
      () => controller.abort(new Error("sync transport timeout")),
      this.#timeoutMs,
    );
    try {
      const credential = await this.#credential();
      const response = await fetch(`${this.#endpoint}/commands`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(credential ? { authorization: `Bearer ${credential}` } : {}),
        },
        body: JSON.stringify(command),
        signal: controller.signal,
      });
      const text = await response.text();
      let body: unknown;
      try {
        body = text.length === 0 ? null : JSON.parse(text);
      } catch {
        body = { kind: "invalid-json", rawLength: text.length };
      }
      return { status: response.status, body };
    } finally {
      clearTimeout(timer);
      signal.removeEventListener("abort", relay);
    }
  }
}

export class SQLiteSyncRepositoryAdapter implements SyncRepository {
  readonly #db: SQLiteDatabase;

  constructor(database: SQLiteDatabase) {
    this.#db = database;
  }

  async claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null> {
    let result: ClaimedCommand | null = null;
    await this.#db.withTransactionAsync(async () => {
      const row = await this.#db.getFirstAsync<OutboxRow>(
        `SELECT candidate.* FROM outbox candidate
         WHERE (
           candidate.state = 'pending'
           OR (candidate.state = 'retry-wait' AND candidate.next_attempt_at <= ?)
           OR (candidate.state = 'claimed' AND candidate.lease_expires_at <= ?)
         )
         AND NOT EXISTS (
           SELECT 1 FROM outbox prior
           WHERE prior.record_id = candidate.record_id
             AND prior.sequence < candidate.sequence
             AND prior.state NOT IN ('applied', 'permanent-failure', 'superseded')
         )
         ORDER BY candidate.sequence
         LIMIT 1`,
        input.now,
        input.now,
      );
      if (!row) return;

      const attempted = parseJson<RecordCommand>(row.attempted_json) ?? recordCommand(row);
      const attempt = row.attempt_count + 1;
      const lease = {
        token: `${input.workerId}:${row.command_id}:${attempt}:${createOpaqueId("lease")}`,
        owner: input.workerId,
        expiresAt: input.now + input.leaseDurationMs,
      };
      const update = await this.#db.runAsync(
        `UPDATE outbox SET
           state = 'claimed',
           attempt_count = ?,
           attempted_json = ?,
           lease_token = ?,
           lease_owner = ?,
           lease_expires_at = ?,
           next_attempt_at = NULL,
           last_error = NULL
         WHERE command_id = ?
           AND (
             state = 'pending'
             OR (state = 'retry-wait' AND next_attempt_at <= ?)
             OR (state = 'claimed' AND lease_expires_at <= ?)
           )`,
        attempt,
        JSON.stringify(attempted),
        lease.token,
        lease.owner,
        lease.expiresAt,
        row.command_id,
        input.now,
        input.now,
      );
      if (update.changes !== 1) return;
      await this.#db.runAsync(
        "UPDATE records SET sync_state = 'syncing' WHERE id = ?",
        row.record_id,
      );
      const record = await this.#db.getFirstAsync<RecordRow>(
        "SELECT * FROM records WHERE id = ?",
        row.record_id,
      );
      result = {
        commandId: row.command_id,
        attempted,
        attempt,
        lease,
        knownRemoteVersion: record?.remote_version ?? null,
      };
    });
    return result;
  }

  async checkpoint(
    claim: ClaimedCommand,
    outcome: CheckpointOutcome,
  ): Promise<CheckpointResult> {
    let result: CheckpointResult | null = null;
    await this.#db.withTransactionAsync(async () => {
      const row = await this.#db.getFirstAsync<OutboxRow>(
        "SELECT * FROM outbox WHERE command_id = ?",
        claim.commandId,
      );
      if (!row || row.state !== "claimed") throw new Error("command is not claimed");
      if (row.lease_token !== claim.lease.token) throw new Error("stale sync lease");
      const attempted = parseJson<RecordCommand>(row.attempted_json);
      if (!attempted || JSON.stringify(attempted) !== JSON.stringify(claim.attempted)) {
        throw new Error("attempted command snapshot changed");
      }

      const rebased: CheckpointResult["rebased"] = [];
      switch (outcome.kind) {
        case "success":
          await this.#checkpointSuccess(row, claim, outcome.remote, outcome.completedAt, rebased);
          break;
        case "conflict":
          await this.#checkpointConflict(row, claim, outcome.remote, outcome.createdAt);
          break;
        case "retry_wait":
          await this.#db.runAsync(
            `UPDATE outbox SET state = 'retry-wait', next_attempt_at = ?, last_error = ?,
              lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
             WHERE command_id = ? AND lease_token = ?`,
            outcome.nextAttemptAt,
            outcome.reason,
            row.command_id,
            claim.lease.token,
          );
          await this.#db.runAsync(
            "UPDATE records SET sync_state = 'retry-wait' WHERE id = ?",
            row.record_id,
          );
          break;
        case "blocked_auth":
          await this.#db.runAsync(
            `UPDATE outbox SET state = 'blocked-auth', last_error = ?,
              lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
             WHERE command_id = ? AND lease_token = ?`,
            outcome.reason,
            row.command_id,
            claim.lease.token,
          );
          await this.#db.runAsync(
            "UPDATE records SET sync_state = 'blocked-auth' WHERE id = ?",
            row.record_id,
          );
          break;
        case "permanent":
          await this.#db.runAsync(
            `UPDATE outbox SET state = 'permanent-failure', last_error = ?,
              lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
             WHERE command_id = ? AND lease_token = ?`,
            outcome.reason,
            row.command_id,
            claim.lease.token,
          );
          await this.#db.runAsync(
            "UPDATE records SET sync_state = 'failed' WHERE id = ?",
            row.record_id,
          );
          break;
      }
      await this.#db.runAsync(
        `INSERT INTO sync_checkpoints (command_id, lease_token, outcome, created_at)
         VALUES (?, ?, ?, ?)`,
        row.command_id,
        claim.lease.token,
        outcome.kind,
        Date.now(),
      );
      const state: DurableCommandState["kind"] = outcome.kind === "success"
        ? "completed"
        : outcome.kind === "retry_wait"
          ? "retry_wait"
          : outcome.kind === "blocked_auth"
            ? "blocked_auth"
            : outcome.kind;
      result = { commandId: row.command_id, state, rebased };
    });
    if (!result) throw new Error("checkpoint transaction produced no result");
    return result;
  }

  async resumeBlockedAuth(now: number): Promise<number> {
    let changes = 0;
    await this.#db.withTransactionAsync(async () => {
      const result = await this.#db.runAsync(
        `UPDATE outbox SET state = 'retry-wait', next_attempt_at = ?,
          last_error = 'credential-restored'
         WHERE state = 'blocked-auth'`,
        now,
      );
      changes = result.changes;
      await this.#db.runAsync(
        `UPDATE records SET sync_state = 'retry-wait'
         WHERE id IN (SELECT record_id FROM outbox WHERE state = 'retry-wait')`,
      );
    });
    return changes;
  }

  async resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult> {
    let result: ConflictResolutionResult | null = null;
    await this.#db.withTransactionAsync(async () => {
      const conflictRow = await this.#db.getFirstAsync<ConflictRow>(
        "SELECT * FROM conflicts WHERE conflict_id = ?",
        conflictId,
      );
      if (!conflictRow) throw new Error(`unknown conflict: ${conflictId}`);
      if (conflictRow.resolution_json) throw new Error(`conflict already resolved: ${conflictId}`);
      const conflict = durableConflict(conflictRow);
      const original = await this.#db.getFirstAsync<OutboxRow>(
        "SELECT * FROM outbox WHERE command_id = ?",
        conflict.commandId,
      );
      const record = await this.#db.getFirstAsync<RecordRow>(
        "SELECT * FROM records WHERE id = ?",
        conflict.recordId,
      );
      if (!original || !record) throw new Error("conflict state is incomplete");
      const later = await this.#db.getAllAsync<OutboxRow>(
        `SELECT * FROM outbox
         WHERE record_id = ? AND sequence > ?
           AND state NOT IN ('applied', 'permanent-failure', 'superseded')
         ORDER BY sequence`,
        conflict.recordId,
        original.sequence,
      );
      const invalidLater = later.find((entry) => entry.state !== "pending");
      if (invalidLater) {
        throw new Error(
          `conflict resolution found an attempted later command: ${invalidLater.command_id}`,
        );
      }

      if (resolution.kind === "remote") {
        const remote = conflict.remote;
        if (remote?.payload) {
          await this.#db.runAsync(
            `UPDATE records SET title = ?, notes = ?, status = ?, observed_at = ?,
              location_json = ?, remote_version = ?, sync_state = 'synced',
              deleted_at_local = NULL, updated_at = ? WHERE id = ?`,
            remote.payload.title,
            remote.payload.notes,
            remote.payload.status,
            remote.payload.observedAt,
            remote.payload.location ? JSON.stringify(remote.payload.location) : null,
            remote.version,
            new Date(resolution.resolvedAt).toISOString(),
            record.id,
          );
        } else {
          await this.#db.runAsync(
            `UPDATE records SET remote_version = ?, sync_state = 'synced',
              deleted_at_local = ?, updated_at = ? WHERE id = ?`,
            remote?.version ?? null,
            new Date(resolution.resolvedAt).toISOString(),
            new Date(resolution.resolvedAt).toISOString(),
            record.id,
          );
        }
        await this.#supersedePending(
          conflict.recordId,
          original.sequence,
          null,
          resolution.resolvedAt,
        );
        await this.#db.runAsync(
          `UPDATE outbox SET state = 'applied', completed_at = ?,
            completed_remote_version = ?, last_error = NULL WHERE command_id = ?`,
          resolution.resolvedAt,
          remote?.version ?? null,
          conflict.commandId,
        );
        await this.#db.runAsync(
          "UPDATE conflicts SET resolution_json = ? WHERE conflict_id = ?",
          JSON.stringify({ kind: "remote", resolvedAt: resolution.resolvedAt }),
          conflictId,
        );
        conflict.resolution = { kind: "remote", resolvedAt: resolution.resolvedAt };
        result = { conflict, command: null };
        return;
      }

      const payload = resolution.kind === "merge"
        ? clone(resolution.payload)
        : record.deleted_at_local
          ? null
          : recordPayload(record);
      const localRevision = resolution.kind === "merge"
        ? record.local_revision + 1
        : record.local_revision;
      if (resolution.kind === "merge") {
        await this.#db.runAsync(
          `UPDATE records SET title = ?, notes = ?, status = ?, observed_at = ?,
            location_json = ?, local_revision = ?, sync_state = 'pending',
            deleted_at_local = NULL, updated_at = ? WHERE id = ?`,
          resolution.payload.title,
          resolution.payload.notes,
          resolution.payload.status,
          resolution.payload.observedAt,
          resolution.payload.location ? JSON.stringify(resolution.payload.location) : null,
          localRevision,
          resolution.createdAt,
          record.id,
        );
      } else {
        await this.#db.runAsync(
          "UPDATE records SET sync_state = 'pending', remote_version = ? WHERE id = ?",
          conflict.remote?.version ?? null,
          record.id,
        );
      }
      const command: RecordCommand = {
        commandId: resolution.commandId,
        recordId: record.id,
        operation: payload === null ? "delete" : "upsert",
        baseVersion: conflict.remote?.version ?? null,
        localRevision,
        payload,
        createdAt: resolution.createdAt,
      };
      await this.#supersedePending(
        conflict.recordId,
        original.sequence,
        resolution.commandId,
        resolution.resolvedAt,
      );
      const commandSequence = await this.#insertCommand(command);
      await this.#db.runAsync(
        `UPDATE outbox SET state = 'applied', completed_at = ?,
          completed_remote_version = ? WHERE command_id = ?`,
        resolution.resolvedAt,
        conflict.remote?.version ?? null,
        conflict.commandId,
      );
      const resolutionState = {
        kind: resolution.kind,
        resolvedAt: resolution.resolvedAt,
        resolutionCommandId: resolution.commandId,
      } as const;
      await this.#db.runAsync(
        "UPDATE conflicts SET resolution_json = ? WHERE conflict_id = ?",
        JSON.stringify(resolutionState),
        conflictId,
      );
      conflict.resolution = resolutionState;
      result = {
        conflict,
        command: { command, state: { kind: "pending" }, sequence: commandSequence },
      };
    });
    if (!result) throw new Error("conflict resolution transaction produced no result");
    return result;
  }

  async snapshot(): Promise<RepositorySnapshot> {
    const [recordRows, outboxRows, conflictRows, checkpointRows] = await Promise.all([
      this.#db.getAllAsync<RecordRow>("SELECT * FROM records ORDER BY id"),
      this.#db.getAllAsync<OutboxRow>("SELECT * FROM outbox ORDER BY sequence"),
      this.#db.getAllAsync<ConflictRow>("SELECT * FROM conflicts ORDER BY created_at"),
      this.#db.getAllAsync<{
        sequence: number;
        command_id: string;
        lease_token: string;
        outcome: CheckpointOutcome["kind"];
      }>("SELECT * FROM sync_checkpoints ORDER BY sequence"),
    ]);
    return {
      records: recordRows.map(localRecord),
      commands: outboxRows.map((row): DurableCommand => ({
        command: recordCommand(row),
        state: durableState(row),
        sequence: row.sequence,
      })),
      conflicts: conflictRows.map(durableConflict),
      checkpoints: checkpointRows.map((row) => ({
        sequence: row.sequence,
        commandId: row.command_id,
        leaseToken: row.lease_token,
        outcome: row.outcome,
      })),
    };
  }

  async #checkpointSuccess(
    row: OutboxRow,
    claim: ClaimedCommand,
    remote: RemoteRecord,
    completedAt: number,
    rebased: CheckpointResult["rebased"],
  ): Promise<void> {
    const local = await this.#db.getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      row.record_id,
    );
    if (!local) throw new Error("local record is missing");

    await this.#db.runAsync(
      `UPDATE outbox SET state = 'applied', completed_at = ?,
        completed_remote_version = ?, lease_token = NULL, lease_owner = NULL,
        lease_expires_at = NULL, next_attempt_at = NULL, last_error = NULL
       WHERE command_id = ? AND lease_token = ?`,
      completedAt,
      remote.version,
      row.command_id,
      claim.lease.token,
    );

    if (local.local_revision === claim.attempted.localRevision) {
      if (remote.payload) {
        await this.#db.runAsync(
          `UPDATE records SET title = ?, notes = ?, status = ?, observed_at = ?,
            location_json = ?, remote_version = ?, sync_state = 'synced',
            deleted_at_local = NULL, updated_at = ? WHERE id = ?`,
          remote.payload.title,
          remote.payload.notes,
          remote.payload.status,
          remote.payload.observedAt,
          remote.payload.location ? JSON.stringify(remote.payload.location) : null,
          remote.version,
          new Date(completedAt).toISOString(),
          row.record_id,
        );
      } else {
        await this.#db.runAsync(
          `UPDATE records SET remote_version = ?, sync_state = 'synced',
            deleted_at_local = COALESCE(deleted_at_local, ?), updated_at = ? WHERE id = ?`,
          remote.version,
          new Date(completedAt).toISOString(),
          new Date(completedAt).toISOString(),
          row.record_id,
        );
      }
    } else {
      await this.#db.runAsync(
        "UPDATE records SET remote_version = ?, sync_state = 'pending' WHERE id = ?",
        remote.version,
        row.record_id,
      );
    }

    const pending = await this.#db.getAllAsync<OutboxRow>(
      `SELECT * FROM outbox
       WHERE record_id = ? AND sequence > ? AND state = 'pending'
       ORDER BY sequence`,
      row.record_id,
      row.sequence,
    );
    for (const command of pending) {
      const nextCommandId = createOpaqueId("cmd-rebase");
      await this.#db.runAsync(
        "UPDATE outbox SET command_id = ?, base_version = ? WHERE command_id = ? AND state = 'pending'",
        nextCommandId,
        remote.version,
        command.command_id,
      );
      rebased.push({
        previousCommandId: command.command_id,
        commandId: nextCommandId,
        baseVersion: remote.version,
      });
    }
  }

  async #checkpointConflict(
    row: OutboxRow,
    claim: ClaimedCommand,
    remote: RemoteRecord | null,
    createdAt: number,
  ): Promise<void> {
    const local = await this.#db.getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      row.record_id,
    );
    if (!local) throw new Error("local record is missing");
    const conflictId = createOpaqueId("conflict");
    await this.#db.runAsync(
      `INSERT INTO conflicts (
        conflict_id, command_id, record_id, attempted_json, local_payload_json,
        local_revision, remote_json, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      conflictId,
      row.command_id,
      row.record_id,
      JSON.stringify(claim.attempted),
      local.deleted_at_local ? null : JSON.stringify(recordPayload(local)),
      local.local_revision,
      remote ? JSON.stringify(remote) : null,
      createdAt,
    );
    await this.#db.runAsync(
      `UPDATE outbox SET state = 'conflict', conflict_id = ?,
        lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
       WHERE command_id = ? AND lease_token = ?`,
      conflictId,
      row.command_id,
      claim.lease.token,
    );
    await this.#db.runAsync(
      "UPDATE records SET sync_state = 'conflict' WHERE id = ?",
      row.record_id,
    );
  }

  async #supersedePending(
    recordId: string,
    afterSequence: number,
    supersededBy: string | null,
    completedAt: number,
  ): Promise<void> {
    await this.#db.runAsync(
      `UPDATE outbox SET state = 'superseded', superseded_by = ?, completed_at = ?,
        last_error = 'superseded-by-conflict-resolution', next_attempt_at = NULL,
        lease_token = NULL, lease_owner = NULL, lease_expires_at = NULL
       WHERE record_id = ? AND sequence > ? AND state = 'pending'`,
      supersededBy,
      completedAt,
      recordId,
      afterSequence,
    );
  }

  async #insertCommand(command: RecordCommand): Promise<number> {
    await this.#db.runAsync(
      `INSERT INTO outbox (
        command_id, record_id, operation, base_version, local_revision,
        payload_json, created_at, state, attempt_count, sequence
      ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0,
        (SELECT COALESCE(MAX(sequence), 0) + 1 FROM outbox))`,
      command.commandId,
      command.recordId,
      command.operation,
      command.baseVersion,
      command.localRevision,
      command.payload ? JSON.stringify(command.payload) : null,
      command.createdAt,
    );
    const inserted = await this.#db.getFirstAsync<{ sequence: number }>(
      "SELECT sequence FROM outbox WHERE command_id = ?",
      command.commandId,
    );
    if (!inserted) throw new Error("resolution command insert was not observable");
    return inserted.sequence;
  }
}

export type ProductionSyncRuntime = ReturnType<typeof createProductionSyncRuntime>;

// [Implementation 7]
// 제한 시간형 동기화 작업자를 SQLite 저장소와 HTTP 전송에 연결합니다.
export function createProductionSyncRuntime(input: {
  repository: SQLiteFieldNotesRepository;
  endpoint: string;
  credential: () => Promise<string | null>;
}) {
  const clock = new SystemLifecycleClock();
  const syncRepository = new SQLiteSyncRepositoryAdapter(input.repository.database());
  const worker = new BoundedSyncWorker({
    repository: syncRepository,
    transport: new FetchSyncTransport({
      endpoint: input.endpoint,
      credential: input.credential,
    }),
    clock,
    budget: new FixedSyncBudget({
      maxCommands: 20,
      leaseDurationMs: 30_000,
      maxAttempts: 5,
      retryDelayMs: 5_000,
      wallTimeMs: 45_000,
    }),
  });
  const lifecycle = new LifecycleSyncCoordinator({
    worker,
    clock,
    scheduler: new TimerDeadlineScheduler(clock),
    ids: new SequentialWorkerIdGenerator(),
  });

  return {
    repository: syncRepository,
    worker,
    lifecycle,
    syncNow: () => lifecycle.run({ trigger: "manual" }),
    onAppActive: () => lifecycle.run({ trigger: "app-active" }),
    onNotification: () => lifecycle.run({ trigger: "notification" }),
    runBackground: (deadlineAt: number, signal?: AbortSignal) =>
      lifecycle.run({ trigger: "background", deadlineAt, signal }),
    resumeAuthentication: async () => {
      await syncRepository.resumeBlockedAuth(Date.now());
      return lifecycle.run({ trigger: "manual" });
    },
  };
}
