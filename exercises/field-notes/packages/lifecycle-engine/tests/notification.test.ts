import assert from "node:assert/strict";
import test from "node:test";
import {
  InMemoryNotificationState,
  InMemoryProcessedIntentClaims,
  NotificationCoordinator,
  SequentialNotificationOwnerIds,
  parseNotificationEnvelope,
} from "../src/index.ts";

class Clock {
  value = 0;
  now() { return this.value; }
}

const envelope = {
  schemaVersion: 1 as const,
  messageId: "message-1",
  accountId: "account-1",
  intent: { kind: "record-conflict" as const, recordId: "record-1" },
};

function fixture() {
  const state = new InMemoryNotificationState();
  state.account = { kind: "active", accountId: "account-1" };
  state.records.set("record-1", "active");
  state.conflicts.set("record-1", "active");
  const claims = new InMemoryProcessedIntentClaims();
  const clock = new Clock();
  const coordinator = new NotificationCoordinator({
    state,
    claims,
    clock,
    owners: new SequentialNotificationOwnerIds(),
    leaseDurationMs: 100,
  });
  return { state, claims, clock, coordinator };
}

test("rejects unknown fields and business snapshots", () => {
  assert.equal(parseNotificationEnvelope({ ...envelope, title: "private record text" }).kind, "invalid");
  assert.equal(parseNotificationEnvelope({
    ...envelope,
    intent: { ...envelope.intent, record: { title: "snapshot" } },
  }).kind, "invalid");
});

test("prepares current-state conflict navigation and completes only after acknowledgement", async () => {
  const { coordinator } = fixture();
  const prepared = await coordinator.prepare(envelope);
  assert.equal(prepared.kind, "prepared");
  if (prepared.kind === "prepared") {
    assert.deepEqual(prepared.navigation, {
      kind: "open-sync",
      focus: "conflict",
      recordId: "record-1",
    });
  }
  assert.equal((await coordinator.prepare(envelope)).kind, "rejected");
  await coordinator.acknowledge(prepared);
  const duplicate = await coordinator.prepare(envelope);
  assert.deepEqual(duplicate, { kind: "rejected", reason: "duplicate" });
});

test("recovers an incomplete claim after lease expiry", async () => {
  const { coordinator, clock } = fixture();
  const first = await coordinator.prepare(envelope);
  assert.equal(first.kind, "prepared");
  clock.value = 100;
  const recovered = await coordinator.prepare(envelope);
  assert.equal(recovered.kind, "prepared");
  if (first.kind === "prepared" && recovered.kind === "prepared") {
    assert.notEqual(first.claim.token, recovered.claim.token);
  }
});

test("uses safe fallbacks for deleted records and account mismatches", async () => {
  const { coordinator, state } = fixture();
  state.records.set("record-1", "deleted");
  const deleted = await coordinator.prepare(envelope);
  assert.equal(deleted.kind, "rejected");
  if (deleted.kind === "rejected") {
    assert.equal(deleted.reason, "record-deleted");
    assert.deepEqual(deleted.safeNavigation, { kind: "open-records" });
  }

  const other = fixture();
  other.state.account = { kind: "active", accountId: "another-account" };
  assert.deepEqual(await other.coordinator.prepare(envelope), {
    kind: "rejected",
    reason: "account-mismatch",
  });
});
