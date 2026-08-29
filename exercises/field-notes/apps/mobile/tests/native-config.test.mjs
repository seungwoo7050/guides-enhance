import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const staticConfig = require("../app.json").expo;
const appConfig = require("../app.config.js");

function profile(name) {
  return appConfig.resolveConfig({
    FIELD_NOTES_BUILD_PROFILE: name,
    EXPO_PUBLIC_FIELD_NOTES_SYNC_URL: `https://${name}.field-notes.invalid/sync`,
  });
}

function plugin(config, name) {
  return config.plugins.find((entry) => (Array.isArray(entry) ? entry[0] : entry) === name);
}

test("gives every install profile an isolated identity and scheme", () => {
  const development = profile("development");
  const preview = profile("preview");
  const production = profile("production");
  assert.equal(new Set([
    development.android.package,
    preview.android.package,
    production.android.package,
  ]).size, 3);
  assert.equal(new Set([
    development.scheme,
    preview.scheme,
    production.scheme,
  ]).size, 3);
  assert.equal(development.extra.fieldNotes.buildProfile, "development");
  assert.equal(production.extra.fieldNotes.syncUrl, "https://production.field-notes.invalid/sync");
});

test("limits generated dev-client schemes to the development profile", () => {
  assert.deepEqual(plugin(profile("development"), "expo-dev-client"), [
    "expo-dev-client",
    { addGeneratedScheme: true },
  ]);
  assert.deepEqual(plugin(profile("preview"), "expo-dev-client"), [
    "expo-dev-client",
    { addGeneratedScheme: false },
  ]);
});

test("declares only foreground media and location capabilities", () => {
  assert.ok(staticConfig.android.permissions.includes("android.permission.CAMERA"));
  assert.ok(staticConfig.android.permissions.includes("android.permission.ACCESS_FINE_LOCATION"));
  assert.ok(staticConfig.android.blockedPermissions.includes("android.permission.ACCESS_BACKGROUND_LOCATION"));
  assert.ok(staticConfig.android.blockedPermissions.includes("android.permission.RECORD_AUDIO"));

  const imagePicker = plugin(staticConfig, "expo-image-picker");
  assert.equal(imagePicker[1].microphonePermission, false);
  const location = plugin(staticConfig, "expo-location");
  assert.equal(location[1].isIosBackgroundLocationEnabled, false);
  assert.equal(location[1].isAndroidBackgroundLocationEnabled, false);
});

test("requires an explicit public sync URL outside development", () => {
  assert.throws(
    () => appConfig.resolveConfig({ FIELD_NOTES_BUILD_PROFILE: "production" }),
    /EXPO_PUBLIC_FIELD_NOTES_SYNC_URL is required/,
  );
  assert.throws(
    () => appConfig.resolvedSyncUrl({ EXPO_PUBLIC_FIELD_NOTES_SYNC_URL: "file:///tmp/data" }, "preview"),
    /must use http or https/,
  );
});
