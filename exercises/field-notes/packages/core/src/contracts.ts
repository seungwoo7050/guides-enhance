// [Implementation 1]
// 기록·첨부 파일·outbox·충돌·화면 이동 상태를 정의합니다.
export type RecordStatus = "draft" | "open" | "resolved";

export type RecordSyncState =
  | "local-only"
  | "pending"
  | "syncing"
  | "synced"
  | "retry-wait"
  | "blocked-auth"
  | "conflict"
  | "failed";

export type RecordLocation = {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  measuredAt: string;
};

export type RecordPayload = {
  title: string;
  notes: string;
  status: RecordStatus;
  observedAt: string;
  location?: RecordLocation;
};

export type FieldRecord = RecordPayload & {
  id: string;
  localRevision: number;
  remoteVersion: number | null;
  syncState: RecordSyncState;
  deletedAtLocal?: string;
};

export type AttachmentState =
  | "staging"
  | "local-ready"
  | "upload-pending"
  | "uploading"
  | "uploaded"
  | "missing-local-file"
  | "cleanup-pending"
  | "removed"
  | "failed";

export type Attachment = {
  id: string;
  recordId: string;
  localUri: string;
  checksum: string;
  byteSize: number;
  mimeType: string;
  state: AttachmentState;
  remoteId?: string;
};

export type RecordCommand = {
  commandId: string;
  recordId: string;
  operation: "upsert" | "delete";
  baseVersion: number | null;
  localRevision: number;
  payload: RecordPayload | null;
  createdAt: string;
};

export type RemoteRecord = {
  recordId: string;
  payload: RecordPayload | null;
  version: number;
  deleted: boolean;
};

export type OutboxState =
  | "pending"
  | "claimed"
  | "retry-wait"
  | "blocked-auth"
  | "conflict"
  | "permanent-failure"
  | "superseded"
  | "applied";

export type OutboxEntry = RecordCommand & {
  state: OutboxState;
  attemptCount: number;
  payloadVersion: 1;
  attempted?: RecordCommand;
  claimedAt?: string;
  lastError?: string;
  lease?: { token: string; owner: string; expiresAt: number };
  nextAttemptAt?: number;
  completedAt?: number;
  completedRemoteVersion?: number | null;
  conflictId?: string;
  supersededBy?: string;
  sequence?: number;
};

export type RecordConflict = {
  conflictId: string;
  commandId: string;
  recordId: string;
  attempted: RecordCommand;
  local: { payload: RecordPayload | null; localRevision: number };
  remote: RemoteRecord | null;
  createdAt: number;
  resolution?:
    | { kind: "remote"; resolvedAt: number }
    | {
        kind: "local" | "merge";
        resolvedAt: number;
        resolutionCommandId: string;
      };
};

export type CapabilityAvailability =
  | { kind: "available" }
  | { kind: "limited"; description: string }
  | { kind: "unavailable"; reason: string };

export type PermissionState =
  | { kind: "not-required" }
  | { kind: "not-determined" }
  | { kind: "granted" }
  | { kind: "limited"; description: string }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "restricted"; reason: string };

export type MediaSource = "camera" | "photo-picker";

export type ExternalMediaOperationState =
  | "launched"
  | "copying"
  | "completed"
  | "cancelled"
  | "failed"
  | "interrupted";

export type ExternalMediaOperation = {
  operationId: string;
  recordId: string;
  source: MediaSource;
  state: ExternalMediaOperationState;
  createdAt: string;
  expiresAt: string;
  completedAt?: string;
  attachmentId?: string;
  failureReason?: string;
};

export type MediaAcquisitionResult =
  | { kind: "acquired"; temporaryUri: string; mimeType?: string }
  | { kind: "cancelled" }
  | {
      kind: "failed";
      code: "launch-failed" | "permission-revoked" | "interrupted" | "invalid-result";
      reason: string;
    };

export type LocationMeasurementResult =
  | ({ kind: "measured" } & RecordLocation)
  | { kind: "permission-revoked"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; reason: string };

export type NavigationIntentSource =
  | "internal"
  | "link"
  | "notification"
  | "restoration";

export type NavigationIntent =
  | { kind: "records"; source: NavigationIntentSource }
  | {
      kind: "open-record";
      recordId: string;
      destination: "detail" | "edit";
      source: NavigationIntentSource;
    }
  | { kind: "open-sync"; source: NavigationIntentSource }
  | { kind: "open-settings"; source: NavigationIntentSource }
  | { kind: "invalid"; reason: string; source: NavigationIntentSource };

export type NavigationDecision =
  | { kind: "navigate"; href: string }
  | { kind: "invalid"; reason: string; fallbackHref: "/records" }
  | { kind: "missing-record"; recordId: string; fallbackHref: "/records" }
  | { kind: "duplicate" };
