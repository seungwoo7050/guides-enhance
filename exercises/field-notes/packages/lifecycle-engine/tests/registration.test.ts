import assert from "node:assert/strict";
import test from "node:test";
import {
  AndroidNotificationRegistrationCoordinator,
  InMemoryInstallationRegistry,
  NotificationInstallationCoordinator,
} from "../src/index.ts";

test("orders channel, permission, request, and token acquisition", async () => {
  const calls: string[] = [];
  const coordinator = new AndroidNotificationRegistrationCoordinator({
    channel: { async ensureChannel() { calls.push("channel"); return { kind: "ready" }; } },
    permission: {
      async current() { calls.push("permission-current"); return { kind: "not-determined" }; },
      async request() { calls.push("permission-request"); return { kind: "granted" }; },
    },
    tokens: { async getToken() { calls.push("token"); return { kind: "token", token: "secret-token" }; } },
  });

  const result = await coordinator.register({ requestPermission: true });
  assert.equal(result.kind, "token-ready");
  assert.deepEqual(calls, ["channel", "permission-current", "permission-request", "token"]);
});

test("does not request a token after denied permission", async () => {
  let tokenCalls = 0;
  const coordinator = new AndroidNotificationRegistrationCoordinator({
    channel: { async ensureChannel() { return { kind: "ready" }; } },
    permission: {
      async current() { return { kind: "denied", canAskAgain: false }; },
      async request() { throw new Error("must not request"); },
    },
    tokens: { async getToken() { tokenCalls += 1; return { kind: "token", token: "x" }; } },
  });
  assert.deepEqual(await coordinator.register({ requestPermission: true }), {
    kind: "permission-denied",
    canAskAgain: false,
  });
  assert.equal(tokenCalls, 0);
});

test("classifies token rotation and protects a newer account from stale logout", async () => {
  const registry = new InMemoryInstallationRegistry();
  const coordinator = new NotificationInstallationCoordinator(registry);
  const token = (value: string) => ({
    kind: "token-ready" as const,
    permission: "granted" as const,
    token: value,
  });

  const created = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-a",
    updatedAt: 1,
    tokenResult: token("token-a"),
  });
  assert.equal(created.kind === "registered" && created.change.kind, "created");

  const rotated = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-a",
    updatedAt: 2,
    tokenResult: token("token-b"),
  });
  assert.equal(rotated.kind === "registered" && rotated.change.kind, "rotated");

  const switched = await coordinator.register({
    installationId: "installation-1",
    accountId: "account-b",
    updatedAt: 3,
    tokenResult: token("token-c"),
  });
  assert.equal(switched.kind === "registered" && switched.change.kind, "account-switched");

  const staleLogout = await coordinator.logout({
    installationId: "installation-1",
    accountId: "account-a",
  });
  assert.deepEqual(staleLogout, {
    kind: "account-mismatch",
    installationId: "installation-1",
    accountId: "account-a",
    boundAccountId: "account-b",
  });
  assert.equal(registry.read("installation-1")?.accountId, "account-b");
});

test("preserves the previous binding when registry upsert fails", async () => {
  const registry = new InMemoryInstallationRegistry();
  const coordinator = new NotificationInstallationCoordinator(registry);
  const tokenResult = { kind: "token-ready" as const, permission: "granted" as const, token: "one" };
  await coordinator.register({ installationId: "i", accountId: "a", updatedAt: 1, tokenResult });
  registry.failNextUpsert = "backend unavailable";
  const failed = await coordinator.register({
    installationId: "i",
    accountId: "b",
    updatedAt: 2,
    tokenResult: { ...tokenResult, token: "two" },
  });
  assert.equal(failed.kind, "registry-failed");
  assert.equal(registry.read("i")?.accountId, "a");
  assert.equal(registry.read("i")?.token, "one");
});
