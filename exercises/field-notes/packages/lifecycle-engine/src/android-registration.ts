import type {
  AndroidNotificationChannelPort,
  NotificationPermissionPort,
  PushTokenPort,
} from "./ports.ts";
import type {
  AndroidNotificationRegistrationResult,
  NotificationPermissionState,
} from "./types.ts";

// [Implementation 8-2]
// Android 알림 채널 생성·권한 확인·푸시 토큰 요청 순서를 고정합니다.
export class AndroidNotificationRegistrationCoordinator {
  readonly #channel: AndroidNotificationChannelPort;
  readonly #permission: NotificationPermissionPort;
  readonly #tokens: PushTokenPort;

  constructor(input: {
    channel: AndroidNotificationChannelPort;
    permission: NotificationPermissionPort;
    tokens: PushTokenPort;
  }) {
    this.#channel = input.channel;
    this.#permission = input.permission;
    this.#tokens = input.tokens;
  }

  async register(input: { requestPermission: boolean }): Promise<AndroidNotificationRegistrationResult> {
    const channel = await this.#channel.ensureChannel();
    if (channel.kind === "failed") return { kind: "channel-failed", reason: channel.reason };

    let permission = await this.#permission.current();
    if (permission.kind === "not-determined") {
      if (!input.requestPermission) return { kind: "permission-required" };
      permission = await this.#permission.request();
    }
    const terminal = this.#permissionResult(permission);
    if (terminal) return terminal;

    const normalized = permission.kind as "granted" | "not-required";
    const token = await this.#tokens.getToken();
    if (token.kind === "failed") {
      return { kind: "token-failed", permission: normalized, reason: token.reason };
    }
    return { kind: "token-ready", permission: normalized, token: token.token };
  }

  #permissionResult(
    permission: NotificationPermissionState,
  ): AndroidNotificationRegistrationResult | null {
    if (permission.kind === "denied") {
      return { kind: "permission-denied", canAskAgain: permission.canAskAgain };
    }
    if (permission.kind === "restricted") {
      return { kind: "permission-restricted", reason: permission.reason };
    }
    if (permission.kind === "not-determined") return { kind: "permission-required" };
    return null;
  }
}
