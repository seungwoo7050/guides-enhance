import {
  DeviceFeatureCoordinator,
  permissionAllowsUse,
  type CameraPort,
  type CapabilityAvailability,
  type LocationMeasurementResult,
  type LocationPort,
  type MediaAcquisitionResult,
  type PendingMediaResultPort,
  type PermissionState,
  type PhotoPickerPort,
} from "@field-notes/core";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { Platform } from "react-native";
import type { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";
import { createOpaqueId } from "../storage/SQLiteFieldNotesRepository";
import { ExpoAttachmentFileStore } from "../storage/attachment-files";

function nativeModuleAvailability(
  feature: "camera" | "photo-picker" | "foreground-location",
): CapabilityAvailability {
  if (Platform.OS === "android" || Platform.OS === "ios") return { kind: "available" };
  if (Platform.OS === "web") {
    return {
      kind: "limited",
      description: `${feature} depends on browser user activation and browser capability`,
    };
  }
  return { kind: "unavailable", reason: `${feature} is not supported on this platform` };
}

function mapPermission(input: {
  status: string;
  granted: boolean;
  canAskAgain: boolean;
}): PermissionState {
  if (input.status === "undetermined") return { kind: "not-determined" };
  if (input.status === "denied" || !input.granted) {
    return { kind: "denied", canAskAgain: input.canAskAgain };
  }
  return { kind: "granted" };
}

function mapLocationPermission(input: {
  status: string;
  granted: boolean;
  canAskAgain: boolean;
  ios?: { accuracy?: string } | null;
  android?: { accuracy?: string } | null;
}): PermissionState {
  const base = mapPermission(input);
  if (base.kind !== "granted") return base;
  if (input.ios?.accuracy === "reduced") {
    return { kind: "limited", description: "iOS reduced-accuracy foreground location" };
  }
  if (input.android?.accuracy === "coarse") {
    return { kind: "limited", description: "Android approximate foreground location" };
  }
  if (input.android?.accuracy === "none") {
    return {
      kind: "limited",
      description: "Android reported granted without a usable accuracy scope",
    };
  }
  return base;
}

type PickerResult = Awaited<ReturnType<typeof ImagePicker.getPendingResultAsync>>;

function normalizePickerResult(
  result: PickerResult,
  context: "launch" | "recovery",
): MediaAcquisitionResult | null {
  if (result === null) return null;
  if ("code" in result) {
    return {
      kind: "failed",
      code: context === "recovery" ? "interrupted" : "launch-failed",
      reason: context === "recovery"
        ? "platform returned a pending image-picker error"
        : "platform image UI failed",
    };
  }
  if (result.canceled) return { kind: "cancelled" };
  const asset = result.assets[0];
  if (
    result.assets.length !== 1
    || !asset
    || asset.uri.trim() === ""
    || (asset.type !== undefined && asset.type !== "image")
  ) {
    return {
      kind: "failed",
      code: "invalid-result",
      reason: "image UI returned no single usable image",
    };
  }
  return {
    kind: "acquired",
    temporaryUri: asset.uri,
    ...(asset.mimeType ? { mimeType: asset.mimeType } : {}),
  };
}

const IMAGE_OPTIONS = {
  mediaTypes: ["images"],
  allowsEditing: false,
  allowsMultipleSelection: false,
  selectionLimit: 1,
  quality: 1,
  exif: false,
  base64: false,
} as const satisfies ImagePicker.ImagePickerOptions;

export class ExpoCameraAdapter implements CameraPort {
  async availability(): Promise<CapabilityAvailability> {
    return nativeModuleAvailability("camera");
  }

  async permission(): Promise<PermissionState> {
    return mapPermission(await ImagePicker.getCameraPermissionsAsync());
  }

  async requestPermission(): Promise<PermissionState> {
    return mapPermission(await ImagePicker.requestCameraPermissionsAsync());
  }

  async capture(): Promise<MediaAcquisitionResult> {
    let current: PermissionState;
    try {
      current = await this.permission();
    } catch {
      return {
        kind: "failed",
        code: "permission-revoked",
        reason: "camera permission could not be rechecked at capture time",
      };
    }
    if (!permissionAllowsUse(current)) {
      return {
        kind: "failed",
        code: "permission-revoked",
        reason: "camera permission is not available at capture time",
      };
    }
    try {
      return normalizePickerResult(await ImagePicker.launchCameraAsync(IMAGE_OPTIONS), "launch")
        ?? { kind: "failed", code: "invalid-result", reason: "camera returned no result" };
    } catch {
      return {
        kind: "failed",
        code: "launch-failed",
        reason: "camera session failed or was interrupted",
      };
    }
  }
}

export class ExpoPhotoPickerAdapter implements PhotoPickerPort {
  async availability(): Promise<CapabilityAvailability> {
    return nativeModuleAvailability("photo-picker");
  }

  async permission(): Promise<PermissionState> {
    return { kind: "not-required" };
  }

  async requestPermission(): Promise<PermissionState> {
    return { kind: "not-required" };
  }

  async choose(): Promise<MediaAcquisitionResult> {
    try {
      return normalizePickerResult(
        await ImagePicker.launchImageLibraryAsync(IMAGE_OPTIONS),
        "launch",
      ) ?? {
        kind: "failed",
        code: "invalid-result",
        reason: "system photo picker returned no result",
      };
    } catch {
      return {
        kind: "failed",
        code: "launch-failed",
        reason: "system photo picker failed or was interrupted",
      };
    }
  }
}

export class ExpoPendingImagePickerAdapter implements PendingMediaResultPort {
  async recoverPending(): Promise<MediaAcquisitionResult | null> {
    if (Platform.OS !== "android") return null;
    try {
      return normalizePickerResult(await ImagePicker.getPendingResultAsync(), "recovery");
    } catch {
      return {
        kind: "failed",
        code: "interrupted",
        reason: "Android pending image result could not be recovered",
      };
    }
  }
}

function normalizeLocation(input: {
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number | null;
  };
  timestamp: number;
}): LocationMeasurementResult {
  const { latitude, longitude, accuracy } = input.coords;
  const measuredAt = new Date(input.timestamp);
  if (
    !Number.isFinite(latitude)
    || latitude < -90
    || latitude > 90
    || !Number.isFinite(longitude)
    || longitude < -180
    || longitude > 180
    || accuracy === null
    || !Number.isFinite(accuracy)
    || accuracy < 0
    || !Number.isFinite(input.timestamp)
    || !Number.isFinite(measuredAt.getTime())
  ) {
    return { kind: "failed", reason: "location provider returned invalid values" };
  }
  return {
    kind: "measured",
    latitude,
    longitude,
    accuracyMeters: accuracy,
    measuredAt: measuredAt.toISOString(),
  };
}

export class ExpoForegroundLocationAdapter implements LocationPort {
  readonly #deadlineMs: number;

  constructor(deadlineMs = 15_000) {
    if (!Number.isFinite(deadlineMs) || deadlineMs <= 0) {
      throw new RangeError("location deadline must be positive");
    }
    this.#deadlineMs = deadlineMs;
  }

  async availability(): Promise<CapabilityAvailability> {
    const module = nativeModuleAvailability("foreground-location");
    if (module.kind === "unavailable") return module;
    try {
      return await Location.hasServicesEnabledAsync()
        ? module
        : { kind: "unavailable", reason: "device location services are disabled" };
    } catch {
      return { kind: "unavailable", reason: "location services status could not be read" };
    }
  }

  async permission(): Promise<PermissionState> {
    return mapLocationPermission(await Location.getForegroundPermissionsAsync());
  }

  async requestPermission(): Promise<PermissionState> {
    return mapLocationPermission(await Location.requestForegroundPermissionsAsync());
  }

  async current(): Promise<LocationMeasurementResult> {
    const availability = await this.availability();
    if (availability.kind === "unavailable") return availability;
    let current: PermissionState;
    try {
      current = await this.permission();
    } catch {
      return { kind: "failed", reason: "foreground location permission could not be rechecked" };
    }
    if (!permissionAllowsUse(current)) {
      return { kind: "permission-revoked", permission: current };
    }

    return new Promise((resolve) => {
      let settled = false;
      const finish = (result: LocationMeasurementResult) => {
        if (settled) return;
        settled = true;
        clearTimeout(deadline);
        resolve(result);
      };
      const deadline = setTimeout(
        () => finish({ kind: "failed", reason: "foreground location timed out" }),
        this.#deadlineMs,
      );
      void Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
        mayShowUserSettingsDialog: false,
      }).then((value) => finish(normalizeLocation(value))).catch(() =>
        finish({ kind: "failed", reason: "foreground location measurement failed" }),
      );
    });
  }
}

export function createMobileDeviceFeatureCoordinator(input: {
  repository: SQLiteFieldNotesRepository;
  files: ExpoAttachmentFileStore;
}): DeviceFeatureCoordinator {
  return new DeviceFeatureCoordinator({
    camera: new ExpoCameraAdapter(),
    photoPicker: new ExpoPhotoPickerAdapter(),
    location: new ExpoForegroundLocationAdapter(),
    pendingMedia: new ExpoPendingImagePickerAdapter(),
    operations: input.repository,
    files: input.files,
    clock: { now: () => new Date().toISOString() },
    ids: {
      recordId: () => createOpaqueId("record"),
      attachmentId: () => createOpaqueId("attachment"),
      commandId: () => createOpaqueId("cmd"),
      externalOperationId: () => createOpaqueId("media-op"),
    },
  });
}
