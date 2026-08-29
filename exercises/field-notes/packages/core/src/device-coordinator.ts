import type {
  Attachment,
  CapabilityAvailability,
  ExternalMediaOperation,
  MediaAcquisitionResult,
  MediaSource,
  PermissionState,
  RecordLocation,
} from "./contracts.ts";
import type {
  AttachmentFileStore,
  CameraPort,
  Clock,
  ExternalMediaOperationRepository,
  IdGenerator,
  LocationPort,
  PendingMediaResultPort,
  PhotoPickerPort,
} from "./ports.ts";

const OPERATION_LIFETIME_MS = 15 * 60 * 1000;
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const SUPPORTED_IMAGE_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/heic",
  "image/heif",
  "image/webp",
]);

type MediaPort = Pick<
  CameraPort | PhotoPickerPort,
  "availability" | "permission" | "requestPermission"
>;

export type MediaActionOutcome =
  | { kind: "attached"; attachment: Attachment; recovered: boolean }
  | { kind: "cancelled" }
  | { kind: "denied"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; code: string; reason: string }
  | { kind: "interrupted"; reason: string }
  | { kind: "duplicate" }
  | { kind: "busy" }
  | { kind: "none" };

export type LocationActionOutcome =
  | { kind: "preview"; location: RecordLocation }
  | { kind: "denied"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; reason: string }
  | { kind: "interrupted" };

export function permissionAllowsUse(permission: PermissionState): boolean {
  return permission.kind === "granted" || permission.kind === "limited";
}

// [Implementation 4]
// 카메라·사진 선택기·위치·권한·중단 결과를 앱이 처리할 상태로 변환합니다.
export class DeviceFeatureCoordinator {
  readonly #camera: CameraPort;
  readonly #photoPicker: PhotoPickerPort;
  readonly #location: LocationPort;
  readonly #pendingMedia: PendingMediaResultPort;
  readonly #operations: ExternalMediaOperationRepository;
  readonly #files: AttachmentFileStore;
  readonly #clock: Clock;
  readonly #ids: IdGenerator;
  #launchInFlightOperationId: string | null = null;
  #locationGeneration = 0;

  constructor(input: {
    camera: CameraPort;
    photoPicker: PhotoPickerPort;
    location: LocationPort;
    pendingMedia: PendingMediaResultPort;
    operations: ExternalMediaOperationRepository;
    files: AttachmentFileStore;
    clock: Clock;
    ids: IdGenerator;
  }) {
    this.#camera = input.camera;
    this.#photoPicker = input.photoPicker;
    this.#location = input.location;
    this.#pendingMedia = input.pendingMedia;
    this.#operations = input.operations;
    this.#files = input.files;
    this.#clock = input.clock;
    this.#ids = input.ids;
  }

  async attachMedia(input: {
    recordId: string;
    source: MediaSource;
  }): Promise<MediaActionOutcome> {
    return input.source === "camera"
      ? this.#launchMedia(input.recordId, input.source, this.#camera, () => this.#camera.capture())
      : this.#launchMedia(
          input.recordId,
          input.source,
          this.#photoPicker,
          () => this.#photoPicker.choose(),
        );
  }

  async #permissionForExplicitAction(
    port: MediaPort | LocationPort,
    current: PermissionState,
  ): Promise<PermissionState> {
    if (permissionAllowsUse(current) || current.kind === "not-required") return current;
    if (
      current.kind === "not-determined"
      || (current.kind === "denied" && current.canAskAgain)
    ) {
      return port.requestPermission();
    }
    return current;
  }

  async #launchMedia(
    recordId: string,
    source: MediaSource,
    port: MediaPort,
    launch: () => Promise<MediaAcquisitionResult>,
  ): Promise<MediaActionOutcome> {
    if (this.#launchInFlightOperationId !== null) return { kind: "busy" };
    const availability = await port.availability().catch(
      (): CapabilityAvailability => ({
        kind: "unavailable",
        reason: `${source} availability query failed`,
      }),
    );
    if (availability.kind === "unavailable") return availability;

    let permission: PermissionState;
    try {
      permission = await this.#permissionForExplicitAction(port, await port.permission());
    } catch {
      return {
        kind: "failed",
        code: "permission-query-failed",
        reason: `${source} permission could not be resolved`,
      };
    }
    if (!(permissionAllowsUse(permission) || permission.kind === "not-required")) {
      return { kind: "denied", permission };
    }

    const createdAt = this.#clock.now();
    const operationId = this.#ids.externalOperationId();
    const expiresAt = new Date(Date.parse(createdAt) + OPERATION_LIFETIME_MS).toISOString();
    let operation: ExternalMediaOperation;
    try {
      operation = await this.#operations.beginExternalMediaOperation({
        operationId,
        recordId,
        source,
        createdAt,
        expiresAt,
      });
    } catch {
      return { kind: "busy" };
    }

    this.#launchInFlightOperationId = operation.operationId;
    try {
      let result: MediaAcquisitionResult;
      try {
        result = await launch();
      } catch {
        await this.#terminate(operation, "interrupted", "external-ui-threw").catch(() => undefined);
        return {
          kind: "interrupted",
          reason: `${source} external UI failed before returning a result`,
        };
      }
      return await this.#consumeMediaResult(operation, result, false);
    } finally {
      this.#launchInFlightOperationId = null;
    }
  }

  async #terminate(
    operation: ExternalMediaOperation,
    state: "cancelled" | "failed" | "interrupted",
    failureReason?: string,
  ): Promise<boolean> {
    return this.#operations.finishExternalMediaOperation({
      operationId: operation.operationId,
      state,
      completedAt: this.#clock.now(),
      ...(failureReason ? { failureReason } : {}),
    });
  }

  #normalizedMimeType(result: MediaAcquisitionResult & { kind: "acquired" }):
    | { kind: "accepted"; mimeType: string }
    | { kind: "rejected" } {
    if (!result.mimeType || result.mimeType.trim() === "") {
      return { kind: "accepted", mimeType: "application/octet-stream" };
    }
    const mimeType = result.mimeType.toLowerCase();
    return SUPPORTED_IMAGE_MIME_TYPES.has(mimeType)
      ? { kind: "accepted", mimeType }
      : { kind: "rejected" };
  }

  async #consumeMediaResult(
    operation: ExternalMediaOperation,
    result: MediaAcquisitionResult,
    recovered: boolean,
  ): Promise<MediaActionOutcome> {
    if (result.kind === "cancelled") {
      return await this.#terminate(operation, "cancelled")
        ? { kind: "cancelled" }
        : { kind: "duplicate" };
    }
    if (result.kind === "failed") {
      const state = result.code === "interrupted" ? "interrupted" : "failed";
      const completed = await this.#terminate(operation, state, result.code);
      if (!completed) return { kind: "duplicate" };
      return state === "interrupted"
        ? { kind: "interrupted", reason: result.reason }
        : { kind: "failed", code: result.code, reason: result.reason };
    }

    const mime = this.#normalizedMimeType(result);
    if (mime.kind === "rejected") {
      await this.#terminate(operation, "failed", "unsupported-media-type");
      return {
        kind: "failed",
        code: "unsupported-media-type",
        reason: "selected result is not a supported image type",
      };
    }
    if (!await this.#operations.claimExternalMediaResult(operation.operationId)) {
      return { kind: "duplicate" };
    }

    let owned: Awaited<ReturnType<AttachmentFileStore["takeOwnership"]>>;
    try {
      owned = await this.#files.takeOwnership(result.temporaryUri);
    } catch {
      await this.#files.cleanupStaging().catch(() => undefined);
      await this.#terminate(operation, "failed", "copy-failed");
      return {
        kind: "failed",
        code: "copy-failed",
        reason: "selected image could not be copied into app-owned storage",
      };
    }
    if (owned.byteSize > MAX_IMAGE_BYTES) {
      await this.#files.remove(owned.ownedUri).catch(() => undefined);
      await this.#terminate(operation, "failed", "file-too-large");
      return {
        kind: "failed",
        code: "file-too-large",
        reason: "selected image exceeds the 20 MiB local safety limit",
      };
    }

    try {
      const completion = await this.#operations.completeExternalMediaWithAttachment({
        operationId: operation.operationId,
        completedAt: this.#clock.now(),
        attachment: {
          id: this.#ids.attachmentId(),
          recordId: operation.recordId,
          localUri: owned.ownedUri,
          checksum: owned.checksum,
          byteSize: owned.byteSize,
          mimeType: mime.mimeType,
        },
      });
      if (completion.kind === "stale") {
        await this.#files.remove(owned.ownedUri).catch(() => undefined);
        return { kind: "duplicate" };
      }
      return { kind: "attached", attachment: completion.attachment, recovered };
    } catch {
      // 첨부 정보 저장이 실패한 파일은 다음 시작 시 미참조 파일 정리에서 처리하도록 남겨 둡니다.
      await this.#terminate(operation, "failed", "metadata-commit-failed").catch(() => undefined);
      return {
        kind: "failed",
        code: "metadata-commit-failed",
        reason: "owned image metadata could not be committed",
      };
    }
  }

  async recoverPendingMedia(): Promise<MediaActionOutcome> {
    if (this.#launchInFlightOperationId !== null) return { kind: "busy" };
    const operation = await this.#operations.activeExternalMediaOperation();
    if (!operation) {
      const stale = await this.#pendingMedia.recoverPending();
      return stale === null ? { kind: "none" } : { kind: "duplicate" };
    }
    if (
      operation.state === "copying"
      || Date.parse(operation.expiresAt) <= Date.parse(this.#clock.now())
    ) {
      await this.#terminate(operation, "interrupted", "expired-or-partial-operation");
      return {
        kind: "interrupted",
        reason: "external media operation was interrupted; choose or capture again",
      };
    }
    const result = await this.#pendingMedia.recoverPending();
    if (result === null) {
      await this.#terminate(operation, "interrupted", "pending-result-unavailable");
      return {
        kind: "interrupted",
        reason: "platform supplied no recoverable result; choose or capture again",
      };
    }
    return this.#consumeMediaResult(operation, result, true);
  }

  invalidateLocationMeasurement(): void {
    this.#locationGeneration += 1;
  }

  async measureLocation(): Promise<LocationActionOutcome> {
    const availability = await this.#location.availability().catch(
      (): CapabilityAvailability => ({
        kind: "unavailable",
        reason: "location availability query failed",
      }),
    );
    if (availability.kind === "unavailable") return availability;

    let permission: PermissionState;
    try {
      permission = await this.#permissionForExplicitAction(
        this.#location,
        await this.#location.permission(),
      );
    } catch {
      return { kind: "failed", reason: "location permission could not be resolved" };
    }
    if (!permissionAllowsUse(permission)) return { kind: "denied", permission };

    const generation = ++this.#locationGeneration;
    let result: Awaited<ReturnType<LocationPort["current"]>>;
    try {
      result = await this.#location.current();
    } catch {
      return { kind: "failed", reason: "foreground location adapter failed" };
    }
    if (generation !== this.#locationGeneration) return { kind: "interrupted" };
    if (result.kind === "measured") {
      const { kind: _, ...location } = result;
      return { kind: "preview", location };
    }
    if (result.kind === "permission-revoked") {
      return { kind: "denied", permission: result.permission };
    }
    return result.kind === "unavailable"
      ? { kind: "unavailable", reason: result.reason }
      : { kind: "failed", reason: result.reason };
  }
}
