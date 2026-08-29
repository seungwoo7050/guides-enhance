import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { validateReleaseManifest, validateReleasePair } from "../src/validate.ts";

async function fixture(name: string): Promise<unknown> {
  return JSON.parse(await readFile(new URL(`../fixtures/${name}`, import.meta.url), "utf8"));
}

// [Implementation 11]
// 서로 모순되는 릴리스 근거를 거부하고 프로젝트 전체 불변식을 회귀 테스트로 확인합니다.
test("accepts a consistent cross-platform candidate without upgrading evidence guarantees", async () => {
  const result = validateReleasePair(await fixture("android.json"), await fixture("ios.json"));
  assert.equal(result.consistent, true);
  assert.equal(result.sameCandidate, true);
  assert.equal(result.crossPlatformPhysicalEvidenceConsistent, true);
  assert.equal(result.guarantees.artifactBytesVerified, false);
  assert.equal(result.guarantees.signingTrustVerified, false);
});

test("rejects an AAB as direct physical-device installation evidence", async () => {
  const android = await fixture("android.json") as Record<string, any>;
  android.installation.artifactRef = "android-aab";
  const result = validateReleaseManifest(android).assessment;
  assert.equal(result.consistent, false);
  assert(result.errors.some((error) => error.includes("not installable")));
});

test("rejects cross-platform source and runtime identity drift", async () => {
  const android = await fixture("android.json");
  const ios = await fixture("ios.json") as Record<string, any>;
  ios.source.revision = "different-revision";
  ios.application.runtimeFingerprint = "runtime-2";
  const result = validateReleasePair(android, ios);
  assert.equal(result.sameCandidate, false);
  assert.equal(result.consistent, false);
});

test("allows honest not-run evidence while keeping completion booleans false", async () => {
  const android = await fixture("android.json") as Record<string, any>;
  android.installation = { status: "not-run", reason: "device unavailable" };
  const result = validateReleaseManifest(android).assessment;
  assert.equal(result.consistent, true);
  assert.equal(result.physicalDeviceEvidenceConsistent, false);
});
