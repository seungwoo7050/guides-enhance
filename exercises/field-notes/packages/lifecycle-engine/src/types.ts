export type LifecycleSyncTrigger =
  | "manual"
  | "app-active"
  | "background"
  | "notification";

export type BoundedWorkerObservation = {
  trigger: string;
  workerId: string;
  claimed: number;
  checkpoints: readonly unknown[];
  stopped: "budget" | "idle" | "aborted" | "checkpoint-failed" | "auth-blocked";
  checkpointError?: string;
};

export type SyncExecution =
  | {
      kind: "ran";
      trigger: LifecycleSyncTrigger;
      workerId: string;
      worker: BoundedWorkerObservation;
    }
  | {
      kind: "not-started";
      trigger: LifecycleSyncTrigger;
      reason: "aborted" | "deadline";
    };

export type SyncOpportunityResult =
  | SyncExecution
  | {
      kind: "coalesced";
      trigger: LifecycleSyncTrigger;
      leaderTrigger: LifecycleSyncTrigger;
      execution: SyncExecution;
    };

export type NotificationEnvelope = {
  schemaVersion: 1;
  messageId: string;
  accountId: string;
  intent: NotificationEnvelopeIntent;
};

export type NotificationEnvelopeIntent =
  | { kind: "record-conflict"; recordId: string }
  | { kind: "record-updated"; recordId: string }
  | { kind: "sync-blocked" };

export type NotificationParseResult =
  | { kind: "valid"; envelope: NotificationEnvelope }
  | {
      kind: "invalid";
      reason:
        | "not-an-object"
        | "unexpected-field"
        | "unsupported-schema"
        | "invalid-message-id"
        | "invalid-account-id"
        | "invalid-intent"
        | "invalid-record-id";
    };

export type AccountReadinessState =
  | { kind: "active"; accountId: string }
  | { kind: "none" }
  | { kind: "deleted" };

export type RecordReadinessState = "active" | "deleted" | "missing";
export type ConflictReadinessState = "active" | "resolved" | "missing";

export type NotificationNavigationIntent =
  | { kind: "open-record"; recordId: string }
  | { kind: "open-sync"; focus: "conflict" | "blocked"; recordId?: string }
  | { kind: "open-records" };

export type ProcessedIntentClaim = {
  messageId: string;
  token: string;
  ownerId: string;
  expiresAt: number;
};

export type ProcessedIntentCompletion =
  | { kind: "completed" }
  | { kind: "terminal"; code: string };

export type NotificationPrepareResult =
  | {
      kind: "prepared";
      envelope: NotificationEnvelope;
      claim: ProcessedIntentClaim;
      navigation: NotificationNavigationIntent;
    }
  | {
      kind: "rejected";
      reason:
        | "malformed"
        | "account-unavailable"
        | "account-deleted"
        | "account-mismatch"
        | "duplicate"
        | "in-progress"
        | "stale"
        | "record-deleted"
        | "record-missing";
      parseReason?: Exclude<NotificationParseResult, { kind: "valid" }>["reason"];
      safeNavigation?: NotificationNavigationIntent;
      claim?: ProcessedIntentClaim;
    };

export type NotificationPermissionState =
  | { kind: "not-required" }
  | { kind: "not-determined" }
  | { kind: "granted" }
  | { kind: "denied"; canAskAgain: boolean }
  | { kind: "restricted"; reason: string };

export type PushTokenResult =
  | { kind: "token"; token: string }
  | { kind: "failed"; reason: string };

export type AndroidNotificationRegistrationResult =
  | { kind: "channel-failed"; reason: string }
  | { kind: "permission-required" }
  | { kind: "permission-denied"; canAskAgain: boolean }
  | { kind: "permission-restricted"; reason: string }
  | { kind: "token-failed"; permission: "granted" | "not-required"; reason: string }
  | { kind: "token-ready"; permission: "granted" | "not-required"; token: string };

export type NotificationInstallationBinding = {
  installationId: string;
  accountId: string;
  token: string;
  updatedAt: number;
};

export type InstallationRegistryUpsertResult =
  | { kind: "stored"; previous: NotificationInstallationBinding | null }
  | { kind: "failed"; reason: string };

export type InstallationRegistryRemoveResult =
  | { kind: "removed"; previous: NotificationInstallationBinding }
  | { kind: "absent" }
  | { kind: "account-mismatch"; boundAccountId: string }
  | { kind: "failed"; reason: string };

export type NotificationInstallationRegistrationResult =
  | {
      kind: "registered";
      installationId: string;
      accountId: string;
      updatedAt: number;
      change:
        | { kind: "created" }
        | { kind: "unchanged" }
        | { kind: "rotated" }
        | { kind: "account-switched"; previousAccountId: string };
    }
  | { kind: "token-unavailable"; installationId: string; accountId: string; reason: string }
  | {
      kind: "registry-failed";
      operation: "upsert";
      installationId: string;
      accountId: string;
      reason: string;
    };

export type NotificationInstallationLogoutResult =
  | { kind: "logged-out"; installationId: string; accountId: string }
  | { kind: "already-logged-out"; installationId: string; accountId: string }
  | {
      kind: "account-mismatch";
      installationId: string;
      accountId: string;
      boundAccountId: string;
    }
  | {
      kind: "registry-failed";
      operation: "remove";
      installationId: string;
      accountId: string;
      reason: string;
    };
