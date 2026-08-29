import assert from "node:assert/strict";
import test from "node:test";
import { parseNotificationEnvelope } from "../src/index.ts";

const envelope = {
  schemaVersion: 1 as const,
  messageId: "message-1",
  accountId: "account-1",
  intent: { kind: "record-conflict" as const, recordId: "record-1" },
};

test("rejects unknown fields and business snapshots", () => {
  assert.equal(parseNotificationEnvelope({ ...envelope, title: "private record text" }).kind, "invalid");
  assert.equal(parseNotificationEnvelope({ ...envelope, intent: { ...envelope.intent, record: { title: "snapshot" } } }).kind, "invalid");
});
