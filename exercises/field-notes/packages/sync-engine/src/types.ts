import type { WireResponse } from "../../fault-server/src/types.ts";
import type {
  RecordCommand,
  RecordPayload,
  RemoteRecord,
} from "../../core/src/contracts.ts";

export type { RecordCommand, RecordPayload, RemoteRecord, WireResponse };

export type AttemptedCommand = RecordCommand;

export type Lease = {
  token: string;
  owner: string;
  expiresAt: number;
};

export type DurableCommandState =
  | { kind: "pending" }
  | { kind: "in_flight"; attempted: AttemptedCommand; attempt: number; lease: Lease }
  | {
      kind: "retry_wait";
      attempted: AttemptedCommand;
      attempt: number;
      nextAttemptAt: number;
      reason: string;
    }
  | { kind: "blocked_auth"; attempted: AttemptedCommand; attempt: number; reason: string }
  | { kind: "conflict"; attempted: AttemptedCommand; attempt: number; conflictId: string }
  | { kind: "permanent"; attempted: AttemptedCommand; attempt: number; reason: string }
  | {
      kind: "superseded";
      supersededBy: string | null;
      completedAt: number;
    }
  | {
      kind: "completed";
      attempted: AttemptedCommand;
      attempt: number;
      remoteVersion: number | null;
      completedAt: number;
    };

export type DurableCommand = {
  command: RecordCommand;
  state: DurableCommandState;
  sequence: number;
};

export type LocalRecord = {
  recordId: string;
  payload: RecordPayload | null;
  deleted: boolean;
  localRevision: number;
  knownRemoteVersion: number | null;
  syncState:
    | "pending"
    | "in_flight"
    | "retry_wait"
    | "blocked_auth"
    | "conflict"
    | "permanent"
    | "synced";
};

export type DurableConflict = {
  conflictId: string;
  commandId: string;
  recordId: string;
  attempted: AttemptedCommand;
  local: { payload: RecordPayload | null; localRevision: number };
  remote: RemoteRecord | null;
  createdAt: number;
  resolution?:
    | { kind: "remote"; resolvedAt: number }
    | { kind: "local" | "merge"; resolvedAt: number; resolutionCommandId: string };
};

export type ClaimedCommand = {
  commandId: string;
  attempted: AttemptedCommand;
  attempt: number;
  lease: Lease;
  knownRemoteVersion: number | null;
};

export type ParsedTransportResult =
  | { kind: "success"; remote: RemoteRecord }
  | { kind: "conflict"; remote: RemoteRecord | null }
  | { kind: "blocked_auth"; reason: string }
  | { kind: "permanent"; reason: string }
  | { kind: "invalid_response"; reason: string };

export type CheckpointOutcome =
  | { kind: "success"; remote: RemoteRecord; completedAt: number }
  | { kind: "conflict"; remote: RemoteRecord | null; createdAt: number }
  | { kind: "retry_wait"; reason: string; nextAttemptAt: number }
  | { kind: "blocked_auth"; reason: string }
  | { kind: "permanent"; reason: string };

export type CheckpointResult = {
  commandId: string;
  state: DurableCommandState["kind"];
  rebased: Array<{ previousCommandId: string; commandId: string; baseVersion: number }>;
};

export type ConflictResolution =
  | { kind: "remote"; resolvedAt: number }
  | { kind: "local"; commandId: string; createdAt: string; resolvedAt: number }
  | {
      kind: "merge";
      commandId: string;
      payload: RecordPayload;
      createdAt: string;
      resolvedAt: number;
    };

export type ConflictResolutionResult = {
  conflict: DurableConflict;
  command: DurableCommand | null;
};

export type RepositorySnapshot = {
  records: LocalRecord[];
  commands: DurableCommand[];
  conflicts: DurableConflict[];
  checkpoints: Array<{
    sequence: number;
    commandId: string;
    leaseToken: string;
    outcome: CheckpointOutcome["kind"];
  }>;
};

export type SyncTrigger =
  | "manual"
  | "app-active"
  | "foreground"
  | "background"
  | "notification";

export type WorkerRunResult = {
  trigger: SyncTrigger;
  workerId: string;
  claimed: number;
  checkpoints: CheckpointResult[];
  stopped: "budget" | "idle" | "aborted" | "checkpoint-failed" | "auth-blocked";
  checkpointError?: string;
};
