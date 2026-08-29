import type { NotificationInstallationRegistryPort } from "./ports.ts";
import type {
  AndroidNotificationRegistrationResult,
  NotificationInstallationLogoutResult,
  NotificationInstallationRegistrationResult,
} from "./types.ts";

// [Implementation 8-3]
// 오래된 로그아웃이 새 계정을 지우지 않도록 설치·계정·토큰 연결을 갱신합니다.
export class NotificationInstallationCoordinator {
  readonly #registry: NotificationInstallationRegistryPort;

  constructor(registry: NotificationInstallationRegistryPort) {
    this.#registry = registry;
  }

  async register(input: {
    installationId: string;
    accountId: string;
    updatedAt: number;
    tokenResult: AndroidNotificationRegistrationResult;
  }): Promise<NotificationInstallationRegistrationResult> {
    if (input.tokenResult.kind !== "token-ready") {
      return {
        kind: "token-unavailable",
        installationId: input.installationId,
        accountId: input.accountId,
        reason: input.tokenResult.kind,
      };
    }

    const stored = await this.#registry.upsert({
      installationId: input.installationId,
      accountId: input.accountId,
      token: input.tokenResult.token,
      updatedAt: input.updatedAt,
    });
    if (stored.kind === "failed") {
      return {
        kind: "registry-failed",
        operation: "upsert",
        installationId: input.installationId,
        accountId: input.accountId,
        reason: stored.reason,
      };
    }

    const previous = stored.previous;
    const change = previous === null
      ? { kind: "created" as const }
      : previous.accountId !== input.accountId
        ? { kind: "account-switched" as const, previousAccountId: previous.accountId }
        : previous.token !== input.tokenResult.token
          ? { kind: "rotated" as const }
          : { kind: "unchanged" as const };
    return {
      kind: "registered",
      installationId: input.installationId,
      accountId: input.accountId,
      updatedAt: input.updatedAt,
      change,
    };
  }

  async logout(input: {
    installationId: string;
    accountId: string;
  }): Promise<NotificationInstallationLogoutResult> {
    const removed = await this.#registry.remove(input);
    switch (removed.kind) {
      case "removed":
        return { kind: "logged-out", ...input };
      case "absent":
        return { kind: "already-logged-out", ...input };
      case "account-mismatch":
        return { kind: "account-mismatch", ...input, boundAccountId: removed.boundAccountId };
      case "failed":
        return { kind: "registry-failed", operation: "remove", ...input, reason: removed.reason };
    }
  }
}
