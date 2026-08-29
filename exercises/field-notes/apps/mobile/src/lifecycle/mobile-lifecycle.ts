import {
  AndroidNotificationRegistrationCoordinator,
  NotificationCoordinator,
  backgroundInvocationSucceeded,
  observeBackgroundSync,
  NotificationInstallationCoordinator,
  SequentialNotificationOwnerIds,
  type AccountReadinessState,
  type AndroidNotificationRegistrationResult,
  type ConflictReadinessState,
  type InstallationRegistryRemoveResult,
  type InstallationRegistryUpsertResult,
  type NotificationInstallationBinding,
  type NotificationInstallationRegistrationResult,
  type NotificationNavigationIntent,
  type NotificationPermissionState,
  type NotificationPrepareResult,
  type ProcessedIntentClaim,
  type ProcessedIntentClaimResult,
  type ProcessedIntentCompletion,
  type PushTokenResult,
  type RecordReadinessState,
} from "@field-notes/lifecycle-engine";
import type { RouteReservation } from "@field-notes/core";
import * as BackgroundTask from "expo-background-task";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import * as TaskManager from "expo-task-manager";
import type { SQLiteDatabase } from "expo-sqlite";
import { AppState, Platform } from "react-native";
import { resolvedSyncEndpoint } from "../application/runtime-config";
import { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";
import {
  createProductionSyncRuntime,
  type ProductionSyncRuntime,
} from "../sync/production-sync";

export const FIELD_NOTES_BACKGROUND_SYNC_TASK = "field-notes-durable-sync-v1";
export const BACKGROUND_MINIMUM_INTERVAL_MINUTES = 15;
const BACKGROUND_BUDGET_MS = 25_000;

// 화면 없는 실행에서도 React보다 먼저 작업을 등록해야 하므로 모듈 범위에서 정의합니다.
TaskManager.defineTask(FIELD_NOTES_BACKGROUND_SYNC_TASK, async () => {
  const controller = new AbortController();
  const expiration = Platform.OS === "ios"
    ? BackgroundTask.addExpirationListener(() => controller.abort(new Error("OS expiration")))
    : { remove() {} };
  let repository: SQLiteFieldNotesRepository | null = null;
  try {
    repository = await SQLiteFieldNotesRepository.open();
    const runtime = createProductionSyncRuntime({
      repository,
      endpoint: resolvedSyncEndpoint(),
      credential: async () => null,
    });
    const result = await runtime.runBackground(
      Date.now() + BACKGROUND_BUDGET_MS,
      controller.signal,
    );
    const observation = observeBackgroundSync(result);
    return backgroundInvocationSucceeded(observation)
      ? BackgroundTask.BackgroundTaskResult.Success
      : BackgroundTask.BackgroundTaskResult.Failed;
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed;
  } finally {
    expiration.remove();
    await repository?.close().catch(() => undefined);
  }
});

export type BackgroundSyncRegistrationObservation = {
  availability: "available" | "restricted" | "error";
  registered: boolean;
};

export async function inspectBackgroundSyncRegistration(): Promise<
  BackgroundSyncRegistrationObservation
> {
  try {
    const status = await BackgroundTask.getStatusAsync();
    const registered = await TaskManager.isTaskRegisteredAsync(
      FIELD_NOTES_BACKGROUND_SYNC_TASK,
    );
    return {
      availability: status === BackgroundTask.BackgroundTaskStatus.Available
        ? "available"
        : "restricted",
      registered,
    };
  } catch {
    return { availability: "error", registered: false };
  }
}

export async function registerBackgroundSync(): Promise<
  BackgroundSyncRegistrationObservation
> {
  await BackgroundTask.registerTaskAsync(FIELD_NOTES_BACKGROUND_SYNC_TASK, {
    minimumInterval: BACKGROUND_MINIMUM_INTERVAL_MINUTES,
  });
  return inspectBackgroundSyncRegistration();
}

export async function unregisterBackgroundSync(): Promise<
  BackgroundSyncRegistrationObservation
> {
  await BackgroundTask.unregisterTaskAsync(FIELD_NOTES_BACKGROUND_SYNC_TASK);
  return inspectBackgroundSyncRegistration();
}

export function installMobileLifecycle(runtime: ProductionSyncRuntime): () => void {
  const subscription = AppState.addEventListener("change", (state) => {
    if (state === "active") void runtime.onAppActive().catch(() => undefined);
  });
  return () => subscription.remove();
}

function runtimeNotificationPermissionRequired(): boolean {
  if (Platform.OS === "ios") return true;
  if (Platform.OS !== "android") return false;
  const version = typeof Platform.Version === "number"
    ? Platform.Version
    : Number.parseInt(String(Platform.Version), 10);
  return Number.isFinite(version) && version >= 33;
}

function mapPermission(
  response: Notifications.NotificationPermissionsStatus,
  runtimePermissionRequired = runtimeNotificationPermissionRequired(),
): NotificationPermissionState {
  if (
    Platform.OS === "ios"
    && response.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL
  ) {
    return { kind: "granted" };
  }
  if (response.granted) {
    return runtimePermissionRequired ? { kind: "granted" } : { kind: "not-required" };
  }
  if (runtimePermissionRequired && response.status === "undetermined") {
    return { kind: "not-determined" };
  }
  return {
    kind: "denied",
    canAskAgain: runtimePermissionRequired && response.canAskAgain,
  };
}

export function createAndroidRegistrationCoordinator(): AndroidNotificationRegistrationCoordinator {
  return new AndroidNotificationRegistrationCoordinator({
    channel: {
      async ensureChannel() {
        if (Platform.OS !== "android") return { kind: "ready" };
        try {
          await Notifications.setNotificationChannelAsync("field-notes", {
            name: "Field Notes",
            importance: Notifications.AndroidImportance.DEFAULT,
          });
          return { kind: "ready" };
        } catch (error) {
          return {
            kind: "failed",
            reason: error instanceof Error ? error.message : String(error),
          };
        }
      },
    },
    permission: {
      async current() {
        if (Platform.OS !== "android" && Platform.OS !== "ios") {
          return { kind: "not-required" };
        }
        return mapPermission(await Notifications.getPermissionsAsync());
      },
      async request() {
        if (!runtimeNotificationPermissionRequired()) {
          return mapPermission(await Notifications.getPermissionsAsync(), false);
        }
        return mapPermission(await Notifications.requestPermissionsAsync(), true);
      },
    },
    tokens: {
      async getToken(): Promise<PushTokenResult> {
        try {
          const projectId = Constants.easConfig?.projectId
            ?? Constants.expoConfig?.extra?.eas?.projectId;
          if (!projectId) return { kind: "failed", reason: "EAS projectId is unavailable" };
          const token = await Notifications.getExpoPushTokenAsync({ projectId });
          return { kind: "token", token: token.data };
        } catch (error) {
          return {
            kind: "failed",
            reason: error instanceof Error ? error.message : String(error),
          };
        }
      },
    },
  });
}

export class SQLiteNotificationInstallationRegistry {
  readonly #db: SQLiteDatabase;

  constructor(database: SQLiteDatabase) {
    this.#db = database;
  }

  async upsert(input: NotificationInstallationBinding): Promise<InstallationRegistryUpsertResult> {
    let result: InstallationRegistryUpsertResult = { kind: "failed", reason: "transaction did not run" };
    await this.#db.withTransactionAsync(async () => {
      const previous = await this.#db.getFirstAsync<{
        installation_id: string;
        account_id: string;
        token: string;
        updated_at: number;
      }>(
        "SELECT * FROM notification_installations WHERE installation_id = ?",
        input.installationId,
      );
      await this.#db.runAsync(
        `INSERT INTO notification_installations (installation_id, account_id, token, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(installation_id) DO UPDATE SET
           account_id = excluded.account_id,
           token = excluded.token,
           updated_at = excluded.updated_at`,
        input.installationId,
        input.accountId,
        input.token,
        input.updatedAt,
      );
      result = {
        kind: "stored",
        previous: previous
          ? {
              installationId: previous.installation_id,
              accountId: previous.account_id,
              token: previous.token,
              updatedAt: previous.updated_at,
            }
          : null,
      };
    });
    return result;
  }

  async remove(input: {
    installationId: string;
    accountId: string;
  }): Promise<InstallationRegistryRemoveResult> {
    let result: InstallationRegistryRemoveResult = { kind: "failed", reason: "transaction did not run" };
    await this.#db.withTransactionAsync(async () => {
      const current = await this.#db.getFirstAsync<{
        installation_id: string;
        account_id: string;
        token: string;
        updated_at: number;
      }>(
        "SELECT * FROM notification_installations WHERE installation_id = ?",
        input.installationId,
      );
      if (!current) {
        result = { kind: "absent" };
        return;
      }
      if (current.account_id !== input.accountId) {
        result = { kind: "account-mismatch", boundAccountId: current.account_id };
        return;
      }
      await this.#db.runAsync(
        "DELETE FROM notification_installations WHERE installation_id = ? AND account_id = ?",
        input.installationId,
        input.accountId,
      );
      result = {
        kind: "removed",
        previous: {
          installationId: current.installation_id,
          accountId: current.account_id,
          token: current.token,
          updatedAt: current.updated_at,
        },
      };
    });
    return result;
  }
}

class SQLiteProcessedIntentClaims {
  readonly #db: SQLiteDatabase;

  constructor(database: SQLiteDatabase) {
    this.#db = database;
  }

  async claim(input: {
    messageId: string;
    ownerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ProcessedIntentClaimResult> {
    let result: ProcessedIntentClaimResult = { kind: "busy" };
    await this.#db.withTransactionAsync(async () => {
      const current = await this.#db.getFirstAsync<{
        state: string;
        token: string | null;
        expires_at: number | null;
      }>("SELECT state, token, expires_at FROM processed_intents WHERE message_id = ?", input.messageId);
      if (current?.state === "completed") {
        result = { kind: "duplicate" };
        return;
      }
      if (current?.state === "claimed" && (current.expires_at ?? 0) > input.now) {
        result = { kind: "busy" };
        return;
      }
      const claim: ProcessedIntentClaim = {
        messageId: input.messageId,
        token: `${input.messageId}:${input.ownerId}:${input.now}`,
        ownerId: input.ownerId,
        expiresAt: input.now + input.leaseDurationMs,
      };
      await this.#db.runAsync(
        `INSERT INTO processed_intents (message_id, state, token, owner_id, expires_at, outcome_json)
         VALUES (?, 'claimed', ?, ?, ?, NULL)
         ON CONFLICT(message_id) DO UPDATE SET
           state = 'claimed', token = excluded.token, owner_id = excluded.owner_id,
           expires_at = excluded.expires_at, outcome_json = NULL`,
        claim.messageId,
        claim.token,
        claim.ownerId,
        claim.expiresAt,
      );
      result = { kind: "claimed", claim };
    });
    return result;
  }

  async complete(
    claim: ProcessedIntentClaim,
    outcome: ProcessedIntentCompletion = { kind: "completed" },
  ): Promise<void> {
    const update = await this.#db.runAsync(
      `UPDATE processed_intents SET state = 'completed', outcome_json = ?,
        token = NULL, owner_id = NULL, expires_at = NULL
       WHERE message_id = ? AND state = 'claimed' AND token = ?`,
      JSON.stringify(outcome),
      claim.messageId,
      claim.token,
    );
    if (update.changes !== 1) throw new Error("stale notification claim");
  }

  async release(claim: ProcessedIntentClaim): Promise<void> {
    await this.#db.runAsync(
      "DELETE FROM processed_intents WHERE message_id = ? AND state = 'claimed' AND token = ?",
      claim.messageId,
      claim.token,
    );
  }
}

class SQLiteNotificationState {
  readonly #db: SQLiteDatabase;
  readonly #accountId: string;

  constructor(database: SQLiteDatabase, accountId: string) {
    this.#db = database;
    this.#accountId = accountId;
  }

  async ready(): Promise<void> {}

  async currentAccount(): Promise<AccountReadinessState> {
    return { kind: "active", accountId: this.#accountId };
  }

  async recordState(recordId: string): Promise<RecordReadinessState> {
    const row = await this.#db.getFirstAsync<{ deleted_at_local: string | null }>(
      "SELECT deleted_at_local FROM records WHERE id = ?",
      recordId,
    );
    if (!row) return "missing";
    return row.deleted_at_local ? "deleted" : "active";
  }

  async conflictState(recordId: string): Promise<ConflictReadinessState> {
    const row = await this.#db.getFirstAsync<{ resolution_json: string | null }>(
      "SELECT resolution_json FROM conflicts WHERE record_id = ? ORDER BY created_at DESC LIMIT 1",
      recordId,
    );
    if (!row) return "missing";
    return row.resolution_json ? "resolved" : "active";
  }

  async isSyncBlocked(): Promise<boolean> {
    const row = await this.#db.getFirstAsync<{ count: number }>(
      "SELECT COUNT(*) AS count FROM outbox WHERE state = 'blocked-auth'",
    );
    return (row?.count ?? 0) > 0;
  }
}

export function createNotificationCoordinator(input: {
  database: SQLiteDatabase;
  accountId: string;
}): NotificationCoordinator {
  return new NotificationCoordinator({
    state: new SQLiteNotificationState(input.database, input.accountId),
    claims: new SQLiteProcessedIntentClaims(input.database),
    clock: { now: () => Date.now() },
    owners: new SequentialNotificationOwnerIds(),
    leaseDurationMs: 30_000,
  });
}

export function navigationHref(intent: NotificationNavigationIntent): string {
  switch (intent.kind) {
    case "open-record":
      return `/records/${encodeURIComponent(intent.recordId)}`;
    case "open-sync":
      return intent.recordId
        ? `/sync?focus=${intent.focus}&recordId=${encodeURIComponent(intent.recordId)}`
        : `/sync?focus=${intent.focus}`;
    case "open-records":
      return "/records";
  }
}

export type NotificationResponseSubscription = {
  dispose(): void;
  retry(): Promise<void>;
};

export function subscribeNotificationResponses(input: {
  coordinator: NotificationCoordinator;
  reserve?(href: string): RouteReservation | null;
  isDraftActive?(): boolean;
  navigate(href: string): Promise<void> | void;
  afterPrepared?(): Promise<void> | void;
  onFailure?(error: unknown): void;
}): NotificationResponseSubscription {
  let active = true;
  let handlingTail: Promise<void> = Promise.resolve();

  const handle = async (response: Notifications.NotificationResponse): Promise<void> => {
    const prepared = await input.coordinator.prepare(response.notification.request.content.data);
    if (!active) {
      await input.coordinator.release(prepared);
      return;
    }
    const navigation = prepared.kind === "prepared"
      ? prepared.navigation
      : prepared.safeNavigation;
    if (navigation && input.isDraftActive?.()) {
      // 저장하지 않은 초안이 있으면 라우터가 예외 없이 이동을 막을 수 있습니다.
      // 알림 응답을 남기고 선점을 해제해 사용자가 다시 시도할 수 있게 합니다.
      await input.coordinator.release(prepared);
      return;
    }
    if (navigation) {
      const href = navigationHref(navigation);
      const reservation = input.reserve?.(href);
      if (input.reserve === undefined || reservation !== null) {
        try {
          await input.navigate(href);
          reservation?.commit();
        } catch (error) {
          reservation?.release();
          await input.coordinator.release(prepared).catch(() => undefined);
          throw error;
        }
      }
    }
    await input.coordinator.acknowledge(prepared);
    await input.afterPrepared?.();
    await Notifications.clearLastNotificationResponse();
  };

  const schedule = (response: Notifications.NotificationResponse): Promise<void> => {
    const run = handlingTail
      .catch(() => undefined)
      .then(() => handle(response));
    handlingTail = run.then(() => undefined, () => undefined);
    void run.catch((error) => input.onFailure?.(error));
    return run;
  };

  const retry = async (): Promise<void> => {
    const response = await Notifications.getLastNotificationResponse();
    if (response && active) await schedule(response);
  };

  void retry().catch((error) => input.onFailure?.(error));
  const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
    void schedule(response);
  });
  return {
    dispose() {
      active = false;
      subscription.remove();
    },
    retry,
  };
}

export type NotificationRegistrationObservation = {
  token: AndroidNotificationRegistrationResult;
  installation: NotificationInstallationRegistrationResult;
};

export async function registerNotificationInstallation(input: {
  database: SQLiteDatabase;
  installationId: string;
  accountId: string;
  requestPermission: boolean;
}): Promise<NotificationRegistrationObservation> {
  const token = await createAndroidRegistrationCoordinator().register({
    requestPermission: input.requestPermission,
  });
  const coordinator = new NotificationInstallationCoordinator(
    new SQLiteNotificationInstallationRegistry(input.database),
  );
  const installation = await coordinator.register({
    installationId: input.installationId,
    accountId: input.accountId,
    updatedAt: Date.now(),
    tokenResult: token,
  });
  return { token, installation };
}

export function subscribePushTokenRotations(input: {
  database: SQLiteDatabase;
  installationId: string;
  accountId: string;
}): () => void {
  const subscription = Notifications.addPushTokenListener(() => {
    // 네이티브 토큰 변경 이벤트는 토큰이 바뀌었다는 신호일 뿐입니다.
    // 최초 등록과 같은 형식의 Expo 토큰을 다시 조회해 저장합니다.
    void registerNotificationInstallation({
      ...input,
      requestPermission: false,
    }).catch(() => undefined);
  });
  return () => subscription.remove();
}
