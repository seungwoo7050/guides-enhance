import Constants from "expo-constants";

type FieldNotesExtra = {
  buildProfile?: unknown;
  syncUrl?: unknown;
};

function fieldNotesExtra(): FieldNotesExtra {
  const value = Constants.expoConfig?.extra?.fieldNotes;
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as FieldNotesExtra
    : {};
}

export function resolvedBuildProfile(): string {
  const value = fieldNotesExtra().buildProfile;
  return typeof value === "string" && value.length > 0 ? value : "unknown";
}

export function resolvedSyncEndpoint(): string {
  const value = fieldNotesExtra().syncUrl;
  if (typeof value !== "string" || value.length === 0) {
    throw new Error("sync endpoint is missing from Expo configuration");
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("sync endpoint is not a valid absolute URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("sync endpoint must use http or https");
  }
  return url.toString().replace(/\/$/, "");
}
