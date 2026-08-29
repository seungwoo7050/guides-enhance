import assert from "node:assert/strict";
import test from "node:test";
import {
  DeviceFeatureCoordinator,
  type Attachment,
  type AttachmentFileStore,
  type CameraPort,
  type Clock,
  type ExternalMediaOperation,
  type ExternalMediaOperationRepository,
  type IdGenerator,
  type LocationMeasurementResult,
  type LocationPort,
  type MediaAcquisitionResult,
  type PendingMediaResultPort,
  type PermissionState,
  type PhotoPickerPort,
} from "../src/index.ts";

class FixedClock implements Clock {
  value = "2026-08-22T00:00:00.000Z";
  now(): string { return this.value; }
}

class SequentialIds implements IdGenerator {
  #value = 0;
  recordId(): string { return `record-${++this.#value}`; }
  attachmentId(): string { return `attachment-${++this.#value}`; }
  commandId(): string { return `command-${++this.#value}`; }
  externalOperationId(): string { return `operation-${++this.#value}`; }
}

class MemoryOperations implements ExternalMediaOperationRepository {
  operation: ExternalMediaOperation | null = null;
  attachments: Attachment[] = [];

  async beginExternalMediaOperation(input: Omit<ExternalMediaOperation, "state">): Promise<ExternalMediaOperation> {
    if (this.operation && ["launched", "copying"].includes(this.operation.state)) {
      throw new Error("active operation exists");
    }
    this.operation = { ...structuredClone(input), state: "launched" };
    return structuredClone(this.operation);
  }

  async activeExternalMediaOperation(): Promise<ExternalMediaOperation | null> {
    return this.operation && ["launched", "copying"].includes(this.operation.state)
      ? structuredClone(this.operation)
      : null;
  }

  async claimExternalMediaResult(operationId: string): Promise<boolean> {
    if (!this.operation || this.operation.operationId !== operationId || this.operation.state !== "launched") {
      return false;
    }
    this.operation.state = "copying";
    return true;
  }

  async completeExternalMediaWithAttachment(input: {
    operationId: string;
    completedAt: string;
    attachment: Omit<Attachment, "state">;
  }): Promise<{ kind: "completed"; attachment: Attachment } | { kind: "stale" }> {
    if (!this.operation || this.operation.operationId !== input.operationId || this.operation.state !== "copying") {
      return { kind: "stale" };
    }
    const attachment: Attachment = { ...structuredClone(input.attachment), state: "upload-pending" };
    this.attachments.push(attachment);
    this.operation = {
      ...this.operation,
      state: "completed",
      completedAt: input.completedAt,
      attachmentId: attachment.id,
    };
    return { kind: "completed", attachment: structuredClone(attachment) };
  }

  async finishExternalMediaOperation(input: {
    operationId: string;
    state: "cancelled" | "failed" | "interrupted";
    completedAt: string;
    failureReason?: string;
  }): Promise<boolean> {
    if (!this.operation || this.operation.operationId !== input.operationId
      || !["launched", "copying"].includes(this.operation.state)) return false;
    this.operation = { ...this.operation, ...structuredClone(input) };
    return true;
  }
}

class MemoryFiles implements AttachmentFileStore {
  byteSize = 128;
  removed: string[] = [];
  async takeOwnership(temporaryUri: string) {
    return {
      ownedUri: `owned://${temporaryUri}`,
      checksum: "checksum",
      byteSize: this.byteSize,
    };
  }
  async remove(ownedUri: string): Promise<void> { this.removed.push(ownedUri); }
  async listOrphans(): Promise<string[]> { return []; }
  async exists(): Promise<boolean> { return true; }
  async cleanupStaging(): Promise<number> { return 0; }
}

class MediaPort implements CameraPort, PhotoPickerPort {
  currentPermission: PermissionState = { kind: "not-determined" };
  result: MediaAcquisitionResult = {
    kind: "acquired",
    temporaryUri: "temporary.jpg",
    mimeType: "image/jpeg",
  };
  launches = 0;
  async availability() { return { kind: "available" } as const; }
  async permission() { return this.currentPermission; }
  async requestPermission() {
    this.currentPermission = { kind: "granted" };
    return this.currentPermission;
  }
  async capture() { this.launches += 1; return this.result; }
  async choose() { this.launches += 1; return this.result; }
}

class PendingMedia implements PendingMediaResultPort {
  result: MediaAcquisitionResult | null = null;
  async recoverPending() { return this.result; }
}

class DeferredLocation implements LocationPort {
  currentPermission: PermissionState = { kind: "granted" };
  resolve: ((value: LocationMeasurementResult) => void) | null = null;
  async availability() { return { kind: "available" } as const; }
  async permission() { return this.currentPermission; }
  async requestPermission() { return this.currentPermission; }
  async current(): Promise<LocationMeasurementResult> {
    return new Promise((resolve) => { this.resolve = resolve; });
  }
}

function fixture() {
  const camera = new MediaPort();
  const picker = new MediaPort();
  const location = new DeferredLocation();
  const pendingMedia = new PendingMedia();
  const operations = new MemoryOperations();
  const files = new MemoryFiles();
  const clock = new FixedClock();
  const coordinator = new DeviceFeatureCoordinator({
    camera,
    photoPicker: picker,
    location,
    pendingMedia,
    operations,
    files,
    clock,
    ids: new SequentialIds(),
  });
  return { coordinator, camera, picker, location, pendingMedia, operations, files, clock };
}

test("commits an external media operation and attachment as one durable completion", async () => {
  const { coordinator, picker, operations } = fixture();
  const result = await coordinator.attachMedia({ recordId: "record-1", source: "photo-picker" });
  assert.equal(result.kind, "attached");
  assert.equal(result.kind === "attached" && result.recovered, false);
  assert.equal(picker.launches, 1);
  assert.equal(operations.operation?.state, "completed");
  assert.equal(operations.attachments.length, 1);
});

test("does not launch external UI after terminal permission denial", async () => {
  const { coordinator, camera } = fixture();
  camera.currentPermission = { kind: "denied", canAskAgain: false };
  const result = await coordinator.attachMedia({ recordId: "record-1", source: "camera" });
  assert.equal(result.kind, "denied");
  assert.equal(camera.launches, 0);
});

test("removes an oversized owned file before completing metadata", async () => {
  const { coordinator, files, operations } = fixture();
  files.byteSize = 20 * 1024 * 1024 + 1;
  const result = await coordinator.attachMedia({ recordId: "record-1", source: "camera" });
  assert.deepEqual(result, {
    kind: "failed",
    code: "file-too-large",
    reason: "selected image exceeds the 20 MiB local safety limit",
  });
  assert.deepEqual(files.removed, ["owned://temporary.jpg"]);
  assert.equal(operations.operation?.state, "failed");
});

test("recovers a pending Android-style media result against the durable operation", async () => {
  const { coordinator, operations, pendingMedia, clock } = fixture();
  await operations.beginExternalMediaOperation({
    operationId: "operation-recovery",
    recordId: "record-1",
    source: "photo-picker",
    createdAt: clock.now(),
    expiresAt: "2026-08-22T00:15:00.000Z",
  });
  pendingMedia.result = {
    kind: "acquired",
    temporaryUri: "recovered.jpg",
    mimeType: "image/jpeg",
  };
  const result = await coordinator.recoverPendingMedia();
  assert.equal(result.kind, "attached");
  assert.equal(result.kind === "attached" && result.recovered, true);
  assert.equal(operations.operation?.state, "completed");
});

test("discards a location result invalidated while native measurement was pending", async () => {
  const { coordinator, location } = fixture();
  const pending = coordinator.measureLocation();
  while (!location.resolve) await Promise.resolve();
  coordinator.invalidateLocationMeasurement();
  location.resolve({
    kind: "measured",
    latitude: 37.5665,
    longitude: 126.978,
    accuracyMeters: 12,
    measuredAt: "2026-08-22T00:00:01.000Z",
  });
  assert.deepEqual(await pending, { kind: "interrupted" });
});
