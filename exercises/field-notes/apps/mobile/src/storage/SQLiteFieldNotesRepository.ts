import type {
  Attachment,
  ExternalMediaOperation,
  FieldRecord,
  OutboxEntry,
  RecordCommand,
  RecordConflict,
  RecordPayload,
  RecordRepository,
} from "@field-notes/core";
import { openDatabaseAsync, type SQLiteDatabase } from "expo-sqlite";

const SCHEMA_VERSION = 2;

function parseJson<T>(value: string | null): T | undefined {
  if (value === null) return undefined;
  return JSON.parse(value) as T;
}

function createOpaqueId(prefix: string): string {
  const cryptoObject = globalThis.crypto as { randomUUID?: () => string } | undefined;
  const value = cryptoObject?.randomUUID?.()
    ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${value}`;
}

type RecordRow = {
  id: string;
  title: string;
  notes: string;
  status: FieldRecord["status"];
  observed_at: string;
  location_json: string | null;
  local_revision: number;
  remote_version: number | null;
  sync_state: FieldRecord["syncState"];
  deleted_at_local: string | null;
};

type AttachmentRow = {
  id: string;
  record_id: string;
  local_uri: string;
  checksum: string;
  byte_size: number;
  mime_type: string;
  state: Attachment["state"];
  remote_id: string | null;
};

type ExternalMediaOperationRow = {
  operation_id: string;
  record_id: string;
  source: ExternalMediaOperation["source"];
  state: ExternalMediaOperation["state"];
  created_at: string;
  expires_at: string;
  completed_at: string | null;
  attachment_id: string | null;
  failure_reason: string | null;
};

type OutboxRow = {
  command_id: string;
  record_id: string;
  operation: RecordCommand["operation"];
  base_version: number | null;
  local_revision: number;
  payload_json: string | null;
  created_at: string;
  state: OutboxEntry["state"];
  attempt_count: number;
  attempted_json: string | null;
  lease_token: string | null;
  lease_owner: string | null;
  lease_expires_at: number | null;
  next_attempt_at: number | null;
  last_error: string | null;
  completed_at: number | null;
  completed_remote_version: number | null;
  conflict_id: string | null;
  superseded_by: string | null;
  sequence: number;
};

type ConflictRow = {
  conflict_id: string;
  command_id: string;
  record_id: string;
  attempted_json: string;
  local_payload_json: string | null;
  local_revision: number;
  remote_json: string | null;
  created_at: number;
  resolution_json: string | null;
};

function recordFromRow(row: RecordRow): FieldRecord {
  return {
    id: row.id,
    title: row.title,
    notes: row.notes,
    status: row.status,
    observedAt: row.observed_at,
    ...(parseJson<RecordPayload["location"]>(row.location_json)
      ? { location: parseJson<RecordPayload["location"]>(row.location_json) }
      : {}),
    localRevision: row.local_revision,
    remoteVersion: row.remote_version,
    syncState: row.sync_state,
    ...(row.deleted_at_local ? { deletedAtLocal: row.deleted_at_local } : {}),
  };
}

function attachmentFromRow(row: AttachmentRow): Attachment {
  return {
    id: row.id,
    recordId: row.record_id,
    localUri: row.local_uri,
    checksum: row.checksum,
    byteSize: row.byte_size,
    mimeType: row.mime_type,
    state: row.state,
    ...(row.remote_id ? { remoteId: row.remote_id } : {}),
  };
}

function externalMediaOperationFromRow(
  row: ExternalMediaOperationRow,
): ExternalMediaOperation {
  return {
    operationId: row.operation_id,
    recordId: row.record_id,
    source: row.source,
    state: row.state,
    createdAt: row.created_at,
    expiresAt: row.expires_at,
    ...(row.completed_at ? { completedAt: row.completed_at } : {}),
    ...(row.attachment_id ? { attachmentId: row.attachment_id } : {}),
    ...(row.failure_reason ? { failureReason: row.failure_reason } : {}),
  };
}

function outboxFromRow(row: OutboxRow): OutboxEntry {
  const attempted = parseJson<RecordCommand>(row.attempted_json);
  return {
    commandId: row.command_id,
    recordId: row.record_id,
    operation: row.operation,
    baseVersion: row.base_version,
    localRevision: row.local_revision,
    payload: parseJson<RecordPayload>(row.payload_json) ?? null,
    createdAt: row.created_at,
    state: row.state,
    attemptCount: row.attempt_count,
    payloadVersion: 1,
    ...(attempted ? { attempted } : {}),
    ...(row.lease_token && row.lease_owner && row.lease_expires_at !== null
      ? {
          lease: {
            token: row.lease_token,
            owner: row.lease_owner,
            expiresAt: row.lease_expires_at,
          },
        }
      : {}),
    ...(row.next_attempt_at !== null ? { nextAttemptAt: row.next_attempt_at } : {}),
    ...(row.last_error ? { lastError: row.last_error } : {}),
    ...(row.completed_at !== null ? { completedAt: row.completed_at } : {}),
    ...(row.completed_remote_version !== null
      ? { completedRemoteVersion: row.completed_remote_version }
      : {}),
    ...(row.conflict_id ? { conflictId: row.conflict_id } : {}),
    ...(row.superseded_by ? { supersededBy: row.superseded_by } : {}),
    sequence: row.sequence,
  };
}

function conflictFromRow(row: ConflictRow): RecordConflict {
  return {
    conflictId: row.conflict_id,
    commandId: row.command_id,
    recordId: row.record_id,
    attempted: JSON.parse(row.attempted_json) as RecordCommand,
    local: {
      payload: parseJson<RecordPayload>(row.local_payload_json) ?? null,
      localRevision: row.local_revision,
    },
    remote: parseJson<RecordConflict["remote"]>(row.remote_json) ?? null,
    createdAt: row.created_at,
    ...(parseJson<RecordConflict["resolution"]>(row.resolution_json)
      ? { resolution: parseJson<RecordConflict["resolution"]>(row.resolution_json) }
      : {}),
  };
}

export class SQLiteFieldNotesRepository implements RecordRepository {
  readonly #db: SQLiteDatabase;
  #readyPromise: Promise<void> | null = null;

  private constructor(database: SQLiteDatabase) {
    this.#db = database;
  }

  static async open(name = "field-notes.db"): Promise<SQLiteFieldNotesRepository> {
    const database = await openDatabaseAsync(name);
    const repository = new SQLiteFieldNotesRepository(database);
    await repository.ready();
    return repository;
  }

  database(): SQLiteDatabase {
    return this.#db;
  }

  close(): Promise<void> {
    return this.#db.closeAsync();
  }

  ready(): Promise<void> {
    this.#readyPromise ??= this.#migrate();
    return this.#readyPromise;
  }

  // [Implementation 3]
  // 프로세스 재시작 뒤 복원할 SQLite 테이블을 만들고 마이그레이션합니다.
  async #migrate(): Promise<void> {
    await this.#db.execAsync(`
      PRAGMA journal_mode = WAL;
      PRAGMA foreign_keys = ON;
      CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY NOT NULL,
        title TEXT NOT NULL,
        notes TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('draft', 'open', 'resolved')),
        observed_at TEXT NOT NULL,
        location_json TEXT,
        local_revision INTEGER NOT NULL CHECK (local_revision >= 1),
        remote_version INTEGER,
        sync_state TEXT NOT NULL,
        deleted_at_local TEXT,
        updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY NOT NULL,
        record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
        local_uri TEXT NOT NULL UNIQUE,
        checksum TEXT NOT NULL,
        byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
        mime_type TEXT NOT NULL,
        state TEXT NOT NULL,
        remote_id TEXT,
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS outbox (
        command_id TEXT PRIMARY KEY NOT NULL,
        record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
        operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete')),
        base_version INTEGER,
        local_revision INTEGER NOT NULL,
        payload_json TEXT,
        created_at TEXT NOT NULL,
        state TEXT NOT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        attempted_json TEXT,
        lease_token TEXT,
        lease_owner TEXT,
        lease_expires_at INTEGER,
        next_attempt_at INTEGER,
        last_error TEXT,
        completed_at INTEGER,
        completed_remote_version INTEGER,
        conflict_id TEXT,
        superseded_by TEXT,
        sequence INTEGER NOT NULL UNIQUE
      );
      CREATE TABLE IF NOT EXISTS conflicts (
        conflict_id TEXT PRIMARY KEY NOT NULL,
        command_id TEXT NOT NULL UNIQUE,
        record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
        attempted_json TEXT NOT NULL,
        local_payload_json TEXT,
        local_revision INTEGER NOT NULL,
        remote_json TEXT,
        created_at INTEGER NOT NULL,
        resolution_json TEXT
      );
      CREATE TABLE IF NOT EXISTS sync_checkpoints (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
        command_id TEXT NOT NULL,
        lease_token TEXT NOT NULL,
        outcome TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS external_media_operations (
        operation_id TEXT PRIMARY KEY NOT NULL,
        record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
        source TEXT NOT NULL CHECK (source IN ('camera', 'photo-picker')),
        state TEXT NOT NULL CHECK (
          state IN ('launched', 'copying', 'completed', 'cancelled', 'failed', 'interrupted')
        ),
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        completed_at TEXT,
        attachment_id TEXT REFERENCES attachments(id),
        failure_reason TEXT
      );
      CREATE INDEX IF NOT EXISTS external_media_active_idx
        ON external_media_operations(state, created_at);
      CREATE TABLE IF NOT EXISTS processed_intents (
        message_id TEXT PRIMARY KEY NOT NULL,
        state TEXT NOT NULL,
        token TEXT,
        owner_id TEXT,
        expires_at INTEGER,
        outcome_json TEXT
      );
      CREATE TABLE IF NOT EXISTS notification_installations (
        installation_id TEXT PRIMARY KEY NOT NULL,
        account_id TEXT NOT NULL,
        token TEXT NOT NULL,
        updated_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS outbox_eligible_idx
        ON outbox(state, next_attempt_at, lease_expires_at, sequence);
      CREATE INDEX IF NOT EXISTS outbox_record_sequence_idx
        ON outbox(record_id, sequence);
      CREATE INDEX IF NOT EXISTS attachments_record_idx
        ON attachments(record_id, state);
    `);
    const version = await this.#db.getFirstAsync<{ user_version: number }>("PRAGMA user_version");
    if ((version?.user_version ?? 0) > SCHEMA_VERSION) {
      throw new Error(`database schema ${version?.user_version} is newer than supported ${SCHEMA_VERSION}`);
    }
    const outboxColumns = await this.#db.getAllAsync<{ name: string }>("PRAGMA table_info(outbox)");
    if (!outboxColumns.some((column) => column.name === "superseded_by")) {
      await this.#db.execAsync("ALTER TABLE outbox ADD COLUMN superseded_by TEXT");
    }
    await this.#db.execAsync(`PRAGMA user_version = ${SCHEMA_VERSION}`);
  }

  async list(): Promise<FieldRecord[]> {
    await this.ready();
    const rows = await this.#db.getAllAsync<RecordRow>(
      "SELECT * FROM records WHERE deleted_at_local IS NULL ORDER BY observed_at DESC, id ASC",
    );
    return rows.map(recordFromRow);
  }

  async get(id: string): Promise<FieldRecord | null> {
    await this.ready();
    const row = await this.#db.getFirstAsync<RecordRow>(
      "SELECT * FROM records WHERE id = ?",
      id,
    );
    return row ? recordFromRow(row) : null;
  }

  // [Implementation 3-1]
  // 기록 변경과 outbox 명령 추가를 하나의 트랜잭션으로 커밋합니다.
  async saveWithCommand(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<{ record: FieldRecord; command: RecordCommand }> {
    await this.ready();
    const now = new Date().toISOString();
    const commandId = createOpaqueId("cmd");
    let result: { record: FieldRecord; command: RecordCommand } | null = null;

    // 기록 변경이나 outbox 명령 추가 중 하나라도 실패하면 트랜잭션 전체를 되돌립니다.
    await this.#db.withTransactionAsync(async () => {
      const current = await this.#db.getFirstAsync<RecordRow>(
        "SELECT * FROM records WHERE id = ?",
        input.id,
      );
      const revision = current?.local_revision ?? 0;
      if (input.expectedLocalRevision !== null && input.expectedLocalRevision !== revision) {
        throw new Error(`record revision changed: expected ${input.expectedLocalRevision}, got ${revision}`);
      }
      const localRevision = revision + 1;
      const remoteVersion = current?.remote_version ?? null;
      await this.#db.runAsync(
        `INSERT INTO records (
          id, title, notes, status, observed_at, location_json, local_revision,
          remote_version, sync_state, deleted_at_local, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?)
        ON CONFLICT(id) DO UPDATE SET
          title = excluded.title,
          notes = excluded.notes,
          status = excluded.status,
          observed_at = excluded.observed_at,
          location_json = excluded.location_json,
          local_revision = excluded.local_revision,
          sync_state = 'pending',
          deleted_at_local = NULL,
          updated_at = excluded.updated_at`,
        input.id,
        input.payload.title,
        input.payload.notes,
        input.payload.status,
        input.payload.observedAt,
        input.payload.location ? JSON.stringify(input.payload.location) : null,
        localRevision,
        remoteVersion,
        now,
      );
      const command: RecordCommand = {
        commandId,
        recordId: input.id,
        operation: "upsert",
        baseVersion: remoteVersion,
        localRevision,
        payload: structuredClone(input.payload),
        createdAt: now,
      };
      await this.#insertCommand(command);
      result = {
        record: {
          id: input.id,
          ...structuredClone(input.payload),
          localRevision,
          remoteVersion,
          syncState: "pending",
        },
        command,
      };
    });

    if (!result) throw new Error("record transaction did not produce a result");
    return result;
  }

  async deleteWithCommand(input: {
    id: string;
    expectedLocalRevision: number;
  }): Promise<{ record: FieldRecord; command: RecordCommand }> {
    await this.ready();
    const now = new Date().toISOString();
    const commandId = createOpaqueId("cmd");
    let result: { record: FieldRecord; command: RecordCommand } | null = null;

    await this.#db.withTransactionAsync(async () => {
      const current = await this.#db.getFirstAsync<RecordRow>(
        "SELECT * FROM records WHERE id = ?",
        input.id,
      );
      if (!current) throw new Error(`record not found: ${input.id}`);
      if (current.local_revision !== input.expectedLocalRevision) {
        throw new Error(`record revision changed: expected ${input.expectedLocalRevision}, got ${current.local_revision}`);
      }
      const localRevision = current.local_revision + 1;
      await this.#db.runAsync(
        `UPDATE records SET local_revision = ?, sync_state = 'pending',
          deleted_at_local = ?, updated_at = ? WHERE id = ?`,
        localRevision,
        now,
        now,
        input.id,
      );
      const command: RecordCommand = {
        commandId,
        recordId: input.id,
        operation: "delete",
        baseVersion: current.remote_version,
        localRevision,
        payload: null,
        createdAt: now,
      };
      await this.#insertCommand(command);
      result = {
        record: {
          ...recordFromRow(current),
          localRevision,
          syncState: "pending",
          deletedAtLocal: now,
        },
        command,
      };
    });
    if (!result) throw new Error("delete transaction did not produce a result");
    return result;
  }

  async attachOwnedFile(input: Omit<Attachment, "state">): Promise<Attachment> {
    await this.ready();
    const attachment: Attachment = { ...structuredClone(input), state: "upload-pending" };
    await this.#insertAttachment(attachment, new Date().toISOString());
    return attachment;
  }

  async listAttachments(recordId?: string): Promise<Attachment[]> {
    await this.ready();
    const rows = recordId
      ? await this.#db.getAllAsync<AttachmentRow>(
          "SELECT * FROM attachments WHERE record_id = ? ORDER BY created_at, id",
          recordId,
        )
      : await this.#db.getAllAsync<AttachmentRow>(
          "SELECT * FROM attachments ORDER BY record_id, created_at, id",
        );
    return rows.map(attachmentFromRow);
  }

  async beginExternalMediaOperation(input: {
    operationId: string;
    recordId: string;
    source: ExternalMediaOperation["source"];
    createdAt: string;
    expiresAt: string;
  }): Promise<ExternalMediaOperation> {
    await this.ready();
    let operation: ExternalMediaOperation | null = null;
    await this.#db.withTransactionAsync(async () => {
      const active = await this.#db.getFirstAsync<{ operation_id: string }>(
        `SELECT operation_id FROM external_media_operations
         WHERE state IN ('launched', 'copying') LIMIT 1`,
      );
      if (active) throw new Error(`external media operation is already active: ${active.operation_id}`);
      await this.#db.runAsync(
        `INSERT INTO external_media_operations (
          operation_id, record_id, source, state, created_at, expires_at
        ) VALUES (?, ?, ?, 'launched', ?, ?)`,
        input.operationId,
        input.recordId,
        input.source,
        input.createdAt,
        input.expiresAt,
      );
      operation = { ...structuredClone(input), state: "launched" };
    });
    if (!operation) throw new Error("external media transaction did not create an operation");
    return operation;
  }

  async activeExternalMediaOperation(): Promise<ExternalMediaOperation | null> {
    await this.ready();
    const row = await this.#db.getFirstAsync<ExternalMediaOperationRow>(
      `SELECT * FROM external_media_operations
       WHERE state IN ('launched', 'copying')
       ORDER BY created_at DESC, operation_id DESC LIMIT 1`,
    );
    return row ? externalMediaOperationFromRow(row) : null;
  }

  async claimExternalMediaResult(operationId: string): Promise<boolean> {
    await this.ready();
    const update = await this.#db.runAsync(
      `UPDATE external_media_operations SET state = 'copying'
       WHERE operation_id = ? AND state = 'launched'`,
      operationId,
    );
    return update.changes === 1;
  }

  async completeExternalMediaWithAttachment(input: {
    operationId: string;
    completedAt: string;
    attachment: Omit<Attachment, "state">;
  }): Promise<
    | { kind: "completed"; attachment: Attachment }
    | { kind: "stale" }
  > {
    await this.ready();
    let result: { kind: "completed"; attachment: Attachment } | { kind: "stale" } = {
      kind: "stale",
    };
    await this.#db.withTransactionAsync(async () => {
      const operation = await this.#db.getFirstAsync<ExternalMediaOperationRow>(
        "SELECT * FROM external_media_operations WHERE operation_id = ?",
        input.operationId,
      );
      if (!operation || operation.state !== "copying") return;
      const attachment: Attachment = {
        ...structuredClone(input.attachment),
        state: "upload-pending",
      };
      await this.#insertAttachment(attachment, input.completedAt);
      const update = await this.#db.runAsync(
        `UPDATE external_media_operations SET state = 'completed', completed_at = ?,
          attachment_id = ?, failure_reason = NULL
         WHERE operation_id = ? AND state = 'copying'`,
        input.completedAt,
        attachment.id,
        input.operationId,
      );
      if (update.changes !== 1) throw new Error("external media completion lost its claim");
      result = { kind: "completed", attachment };
    });
    return result;
  }

  async finishExternalMediaOperation(input: {
    operationId: string;
    state: "cancelled" | "failed" | "interrupted";
    completedAt: string;
    failureReason?: string;
  }): Promise<boolean> {
    await this.ready();
    const update = await this.#db.runAsync(
      `UPDATE external_media_operations SET state = ?, completed_at = ?, failure_reason = ?
       WHERE operation_id = ? AND state IN ('launched', 'copying')`,
      input.state,
      input.completedAt,
      input.failureReason ?? null,
      input.operationId,
    );
    return update.changes === 1;
  }

  async markAttachmentMissing(id: string): Promise<void> {
    await this.#db.runAsync(
      "UPDATE attachments SET state = 'missing-local-file' WHERE id = ? AND state != 'removed'",
      id,
    );
  }

  async markAttachmentRemoved(id: string): Promise<void> {
    await this.#db.runAsync("UPDATE attachments SET state = 'removed' WHERE id = ?", id);
  }

  async syncDashboard(): Promise<{
    outbox: OutboxEntry[];
    conflicts: RecordConflict[];
    attachments: Attachment[];
  }> {
    await this.ready();
    const [outboxRows, conflictRows, attachments] = await Promise.all([
      this.#db.getAllAsync<OutboxRow>("SELECT * FROM outbox ORDER BY sequence"),
      this.#db.getAllAsync<ConflictRow>("SELECT * FROM conflicts ORDER BY created_at"),
      this.listAttachments(),
    ]);
    return {
      outbox: outboxRows.map(outboxFromRow),
      conflicts: conflictRows.map(conflictFromRow),
      attachments,
    };
  }

  async #insertAttachment(attachment: Attachment, createdAt: string): Promise<void> {
    await this.#db.runAsync(
      `INSERT INTO attachments (
        id, record_id, local_uri, checksum, byte_size, mime_type, state, remote_id, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      attachment.id,
      attachment.recordId,
      attachment.localUri,
      attachment.checksum,
      attachment.byteSize,
      attachment.mimeType,
      attachment.state,
      attachment.remoteId ?? null,
      createdAt,
    );
  }

  async #insertCommand(command: RecordCommand): Promise<void> {
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
  }
}

export { createOpaqueId };
export type { ConflictRow, OutboxRow, RecordRow };
