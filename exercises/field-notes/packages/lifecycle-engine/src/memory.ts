import type {
  NotificationInstallationRegistryPort,
  NotificationStateRepository,
} from "./ports.ts";
import type {
  AccountReadinessState,
  ConflictReadinessState,
  InstallationRegistryRemoveResult,
  InstallationRegistryUpsertResult,
  NotificationInstallationBinding,
  RecordReadinessState,
} from "./types.ts";

export class InMemoryNotificationState implements NotificationStateRepository {
  account: AccountReadinessState = { kind: "none" };
  syncBlocked = false;
  readonly records = new Map<string, RecordReadinessState>();
  readonly conflicts = new Map<string, ConflictReadinessState>();
  readyCalls = 0;

  async ready(): Promise<void> {
    this.readyCalls += 1;
  }
  async currentAccount(): Promise<AccountReadinessState> {
    return structuredClone(this.account);
  }
  async recordState(recordId: string): Promise<RecordReadinessState> {
    return this.records.get(recordId) ?? "missing";
  }
  async conflictState(recordId: string): Promise<ConflictReadinessState> {
    return this.conflicts.get(recordId) ?? "missing";
  }
  async isSyncBlocked(): Promise<boolean> {
    return this.syncBlocked;
  }
}

export class InMemoryInstallationRegistry implements NotificationInstallationRegistryPort {
  readonly #bindings = new Map<string, NotificationInstallationBinding>();
  failNextUpsert: string | null = null;
  failNextRemove: string | null = null;

  async upsert(input: NotificationInstallationBinding): Promise<InstallationRegistryUpsertResult> {
    if (this.failNextUpsert) {
      const reason = this.failNextUpsert;
      this.failNextUpsert = null;
      return { kind: "failed", reason };
    }
    const previous = this.#bindings.get(input.installationId) ?? null;
    this.#bindings.set(input.installationId, structuredClone(input));
    return { kind: "stored", previous: structuredClone(previous) };
  }

  async remove(input: {
    installationId: string;
    accountId: string;
  }): Promise<InstallationRegistryRemoveResult> {
    if (this.failNextRemove) {
      const reason = this.failNextRemove;
      this.failNextRemove = null;
      return { kind: "failed", reason };
    }
    const binding = this.#bindings.get(input.installationId);
    if (!binding) return { kind: "absent" };
    if (binding.accountId !== input.accountId) {
      return { kind: "account-mismatch", boundAccountId: binding.accountId };
    }
    this.#bindings.delete(input.installationId);
    return { kind: "removed", previous: structuredClone(binding) };
  }

  read(installationId: string): NotificationInstallationBinding | null {
    const value = this.#bindings.get(installationId);
    return value ? structuredClone(value) : null;
  }
}
