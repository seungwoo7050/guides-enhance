import { CrossSourceRouteArbiter } from "@field-notes/core";
import type {
  Attachment,
  DeviceFeatureCoordinator,
  FieldRecord,
  OutboxEntry,
  RecordConflict,
  RecordLocation,
  RecordPayload,
} from "@field-notes/core";
import { usePathname, useRouter } from "expo-router";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";
import { createMobileDeviceFeatureCoordinator } from "../device/device-adapters";
import {
  createNotificationCoordinator,
  inspectBackgroundSyncRegistration,
  installMobileLifecycle,
  registerBackgroundSync,
  registerNotificationInstallation,
  subscribeNotificationResponses,
  subscribePushTokenRotations,
  unregisterBackgroundSync,
} from "../lifecycle/mobile-lifecycle";
import { installLinkNavigation } from "../navigation/mobile-navigation";
import { resolvedSyncEndpoint } from "./runtime-config";
import {
  AttachmentStorageMaintenance,
  ExpoAttachmentFileStore,
} from "../storage/attachment-files";
import {
  createOpaqueId,
  SQLiteFieldNotesRepository,
} from "../storage/SQLiteFieldNotesRepository";
import {
  createProductionSyncRuntime,
  type ProductionSyncRuntime,
} from "../sync/production-sync";

const ACCOUNT_ID = "local-account";
const INSTALLATION_ID = "field-notes-local-installation";

export type RuntimeSnapshot = {
  ready: boolean;
  busy: boolean;
  error: string | null;
  records: FieldRecord[];
  outbox: OutboxEntry[];
  conflicts: RecordConflict[];
  attachments: Attachment[];
};

type RuntimeServices = {
  repository: SQLiteFieldNotesRepository;
  devices: DeviceFeatureCoordinator;
  sync: ProductionSyncRuntime;
};

export type FieldNotesContextValue = RuntimeSnapshot & {
  refresh(): Promise<void>;
  record(id: string): FieldRecord | null;
  attachmentsFor(recordId: string): Attachment[];
  createRecord(payload: RecordPayload): Promise<FieldRecord>;
  updateRecord(id: string, expectedRevision: number, payload: RecordPayload): Promise<FieldRecord>;
  deleteRecord(id: string, expectedRevision: number): Promise<void>;
  attachMedia(recordId: string, source: "camera" | "photo-picker"): Promise<string>;
  measureLocation(): Promise<RecordLocation>;
  syncNow(): Promise<void>;
  resumeAuthentication(): Promise<void>;
  resolveConflict(input: {
    conflictId: string;
    kind: "remote" | "local" | "merge";
    payload?: RecordPayload;
  }): Promise<void>;
  registerNotifications(requestPermission: boolean): Promise<string>;
  setDraftActive(active: boolean): void;
  inspectBackgroundSync(): Promise<string>;
  setBackgroundSync(enabled: boolean): Promise<string>;
};

const FieldNotesContext = createContext<FieldNotesContextValue | null>(null);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

// [Implementation 0]
// 프로세스가 사용할 저장소·파일·기기 기능·동기화 서비스를 생성합니다.
async function createRuntimeServices(): Promise<RuntimeServices> {
  const repository = await SQLiteFieldNotesRepository.open();
  const files = new ExpoAttachmentFileStore();
  const attachmentMaintenance = new AttachmentStorageMaintenance(repository, files);
  await attachmentMaintenance.reconcile();
  const devices = createMobileDeviceFeatureCoordinator({ repository, files });
  await devices.recoverPendingMedia();
  const sync = createProductionSyncRuntime({
    repository,
    endpoint: resolvedSyncEndpoint(),
    credential: async () => null,
  });
  return { repository, devices, sync };
}

const emptySnapshot: RuntimeSnapshot = {
  ready: false,
  busy: false,
  error: null,
  records: [],
  outbox: [],
  conflicts: [],
  attachments: [],
};

// [Implementation 9]
// 화면에서 저장·사진·동기화·백그라운드·알림 기능을 호출할 수 있게 제공합니다.
export function FieldNotesProvider({ children }: PropsWithChildren) {
  const router = useRouter();
  const pathname = usePathname();
  const initialPathname = useRef(pathname).current;
  const servicesRef = useRef<RuntimeServices | null>(null);
  const operationTailRef = useRef<Promise<void>>(Promise.resolve());
  const linkRetryRef = useRef<(() => void) | null>(null);
  const notificationRetryRef = useRef<(() => Promise<void>) | null>(null);
  const draftActiveRef = useRef(false);
  const routeArbiter = useRef(new CrossSourceRouteArbiter()).current;
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot>(emptySnapshot);

  const refresh = useCallback(async () => {
    const services = servicesRef.current;
    if (!services) return;
    const [records, dashboard] = await Promise.all([
      services.repository.list(),
      services.repository.syncDashboard(),
    ]);
    setSnapshot((current) => ({
      ...current,
      ready: true,
      error: null,
      records,
      outbox: dashboard.outbox,
      conflicts: dashboard.conflicts,
      attachments: dashboard.attachments,
    }));
  }, []);

  const setDraftActive = useCallback((active: boolean) => {
    draftActiveRef.current = active;
    if (!active) {
      linkRetryRef.current?.();
      void notificationRetryRef.current?.().catch((error) => {
        setSnapshot((current) => ({ ...current, error: errorMessage(error) }));
      });
    }
  }, []);

  const execute = useCallback(<T,>(
    operation: (services: RuntimeServices) => Promise<T>,
  ): Promise<T> => {
    const run = operationTailRef.current
      .catch(() => undefined)
      .then(async () => {
        const services = servicesRef.current;
        if (!services) throw new Error("Field Notes runtime is not ready");
        setSnapshot((current) => ({ ...current, busy: true, error: null }));
        try {
          const value = await operation(services);
          await refresh();
          return value;
        } catch (error) {
          setSnapshot((current) => ({ ...current, error: errorMessage(error) }));
          throw error;
        } finally {
          setSnapshot((current) => ({ ...current, busy: false }));
        }
      });
    operationTailRef.current = run.then(() => undefined, () => undefined);
    return run;
  }, [refresh]);

  useEffect(() => {
    let active = true;
    const disposers: Array<() => void> = [];
    void (async () => {
      try {
        const services = await createRuntimeServices();
        if (!active) {
          await services.repository.close();
          return;
        }
        servicesRef.current = services;
        disposers.push(installMobileLifecycle(services.sync));
        const linkNavigation = installLinkNavigation({
          initialPathname,
          arbiter: routeArbiter,
          isDraftActive: () => draftActiveRef.current,
          recordExists: async (recordId) => (await services.repository.get(recordId)) !== null,
          navigate: (href) => router.replace(href as never),
          reportFailure: (error) => {
            if (active) {
              setSnapshot((current) => ({ ...current, error: errorMessage(error) }));
            }
          },
        });
        linkRetryRef.current = linkNavigation.retryDeferred;
        disposers.push(() => {
          linkNavigation.dispose();
          if (linkRetryRef.current === linkNavigation.retryDeferred) linkRetryRef.current = null;
        });
        const notificationCoordinator = createNotificationCoordinator({
          database: services.repository.database(),
          accountId: ACCOUNT_ID,
        });
        const notificationResponses = subscribeNotificationResponses({
          coordinator: notificationCoordinator,
          reserve: (href) => routeArbiter.reserve(href),
          isDraftActive: () => draftActiveRef.current,
          navigate: async (href) => {
            router.push(href as never);
            await services.sync.onNotification();
          },
          afterPrepared: refresh,
          onFailure: (error) => {
            if (active) {
              setSnapshot((current) => ({ ...current, error: errorMessage(error) }));
            }
          },
        });
        notificationRetryRef.current = notificationResponses.retry;
        disposers.push(() => {
          notificationResponses.dispose();
          if (notificationRetryRef.current === notificationResponses.retry) {
            notificationRetryRef.current = null;
          }
        });
        disposers.push(subscribePushTokenRotations({
          database: services.repository.database(),
          installationId: INSTALLATION_ID,
          accountId: ACCOUNT_ID,
        }));
        await refresh();
        void services.sync.onAppActive()
          .then(refresh)
          .catch((error) => {
            if (active) {
              setSnapshot((current) => ({ ...current, error: errorMessage(error) }));
            }
          });
      } catch (error) {
        if (active) {
          setSnapshot((current) => ({
            ...current,
            ready: false,
            error: errorMessage(error),
          }));
        }
      }
    })();
    return () => {
      active = false;
      for (const dispose of disposers.reverse()) dispose();
      const services = servicesRef.current;
      servicesRef.current = null;
      void services?.repository.close().catch(() => undefined);
    };
  }, [initialPathname, refresh, routeArbiter, router]);

  const value = useMemo<FieldNotesContextValue>(() => ({
    ...snapshot,
    refresh,
    record: (id) => snapshot.records.find((record) => record.id === id) ?? null,
    attachmentsFor: (recordId) => snapshot.attachments.filter((item) => item.recordId === recordId),
    createRecord: (payload) => execute(async ({ repository }) => {
      const id = createOpaqueId("record");
      return (await repository.saveWithCommand({
        id,
        expectedLocalRevision: null,
        payload,
      })).record;
    }),
    updateRecord: (id, expectedRevision, payload) => execute(async ({ repository }) =>
      (await repository.saveWithCommand({
        id,
        expectedLocalRevision: expectedRevision,
        payload,
      })).record),
    deleteRecord: (id, expectedRevision) => execute(async ({ repository }) => {
      await repository.deleteWithCommand({ id, expectedLocalRevision: expectedRevision });
    }),
    attachMedia: (recordId, source) => execute(async ({ devices }) => {
      const result = await devices.attachMedia({ recordId, source });
      if (result.kind === "attached") return result.attachment.id;
      if (result.kind === "cancelled") return "cancelled";
      if (result.kind === "denied") throw new Error(`media permission: ${result.permission.kind}`);
      if (result.kind === "busy") throw new Error("another media operation is active");
      if (result.kind === "duplicate") throw new Error("media result was already consumed");
      if (result.kind === "none") throw new Error("no media result is available");
      throw new Error(result.reason);
    }),
    measureLocation: () => execute(async ({ devices }) => {
      const result = await devices.measureLocation();
      if (result.kind === "preview") return result.location;
      if (result.kind === "denied") throw new Error(`location permission: ${result.permission.kind}`);
      if (result.kind === "interrupted") throw new Error("location measurement was interrupted");
      throw new Error(result.reason);
    }),
    syncNow: () => execute(async ({ sync }) => {
      await sync.syncNow();
    }),
    resumeAuthentication: () => execute(async ({ sync }) => {
      await sync.resumeAuthentication();
    }),
    resolveConflict: (input) => execute(async ({ sync }) => {
      const now = Date.now();
      if (input.kind === "remote") {
        await sync.repository.resolveConflict(input.conflictId, { kind: "remote", resolvedAt: now });
        return;
      }
      const commandId = createOpaqueId("cmd-resolution");
      const createdAt = new Date(now).toISOString();
      if (input.kind === "local") {
        await sync.repository.resolveConflict(input.conflictId, {
          kind: "local",
          commandId,
          createdAt,
          resolvedAt: now,
        });
        return;
      }
      if (!input.payload) throw new Error("merge resolution requires a payload");
      await sync.repository.resolveConflict(input.conflictId, {
        kind: "merge",
        commandId,
        payload: input.payload,
        createdAt,
        resolvedAt: now,
      });
    }),
    setDraftActive,
    registerNotifications: (requestPermission) => execute(async ({ repository }) => {
      const result = await registerNotificationInstallation({
        database: repository.database(),
        installationId: INSTALLATION_ID,
        accountId: ACCOUNT_ID,
        requestPermission,
      });
      if (result.installation.kind === "registered") {
        return `registered:${result.installation.change.kind}`;
      }
      return `${result.token.kind}:${result.installation.kind}`;
    }),
    inspectBackgroundSync: () => execute(async () => {
      const result = await inspectBackgroundSyncRegistration();
      return `${result.availability}:${result.registered ? "registered" : "unregistered"}`;
    }),
    setBackgroundSync: (enabled) => execute(async () => {
      const result = enabled
        ? await registerBackgroundSync()
        : await unregisterBackgroundSync();
      return `${result.availability}:${result.registered ? "registered" : "unregistered"}`;
    }),
  }), [execute, refresh, setDraftActive, snapshot]);

  return <FieldNotesContext.Provider value={value}>{children}</FieldNotesContext.Provider>;
}

export function useFieldNotes(): FieldNotesContextValue {
  const value = useContext(FieldNotesContext);
  if (!value) throw new Error("useFieldNotes must be used inside FieldNotesProvider");
  return value;
}
