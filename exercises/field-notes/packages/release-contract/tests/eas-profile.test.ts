import assert from "node:assert/strict";
import test from "node:test";
import { validateEasConfiguration } from "../src/eas-profile.ts";

const valid = {
  cli: { requireCommit: true, appVersionSource: "local" },
  build: {
    base: { node: "24.19.0" },
    development: {
      extends: "base",
      developmentClient: true,
      distribution: "internal",
      env: { FIELD_NOTES_BUILD_PROFILE: "development" },
    },
    preview: {
      extends: "base",
      distribution: "internal",
      android: { buildType: "apk" },
      env: { FIELD_NOTES_BUILD_PROFILE: "preview" },
    },
    production: {
      extends: "base",
      env: { FIELD_NOTES_BUILD_PROFILE: "production" },
    },
  },
};

test("accepts the three explicit build roles without claiming build execution", () => {
  const result = validateEasConfiguration(valid);
  assert.equal(result.configurationValid, true);
  assert.equal(result.guarantees.nativeBuildExecuted, false);
  assert.equal(result.guarantees.storeAccepted, false);
});

test("rejects secret-like env, production APK, and update-channel claims", () => {
  const wrong = structuredClone(valid);
  wrong.build.production = {
    ...wrong.build.production,
    channel: "production",
    android: { buildType: "apk" },
    env: { API_TOKEN: "secret" },
  } as never;
  const result = validateEasConfiguration(wrong);
  assert.equal(result.configurationValid, false);
  assert(result.errors.some((error) => error.includes("channel")));
  assert(result.errors.some((error) => error.includes("AAB")));
  assert(result.errors.some((error) => error.includes("FIELD_NOTES_BUILD_PROFILE")));
});
