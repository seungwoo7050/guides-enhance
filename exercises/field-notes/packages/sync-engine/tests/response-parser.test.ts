import assert from "node:assert/strict";
import test from "node:test";
import { parseTransportResponse } from "../src/response-parser.ts";
import type { ClaimedCommand } from "../src/types.ts";

const claim: ClaimedCommand = {
  commandId: "cmd-1",
  attempted: {
    commandId: "cmd-1",
    recordId: "record-1",
    operation: "upsert",
    baseVersion: 2,
    localRevision: 3,
    payload: {
      title: "Observation",
      notes: "Stable",
      status: "open",
      observedAt: "2026-08-22T00:00:00.000Z",
    },
    createdAt: "2026-08-22T00:00:01.000Z",
  },
  attempt: 1,
  lease: { token: "lease", owner: "worker", expiresAt: 1000 },
  knownRemoteVersion: 2,
};

test("accepts a matching monotonic success", () => {
  const result = parseTransportResponse({
    status: 200,
    body: {
      kind: "success",
      commandId: "cmd-1",
      record: {
        recordId: "record-1",
        payload: claim.attempted.payload,
        version: 3,
        deleted: false,
      },
    },
  }, claim);
  assert.equal(result.kind, "success");
});

test("rejects command mismatches and version regressions", () => {
  assert.equal(parseTransportResponse({
    status: 200,
    body: { kind: "success", commandId: "other", record: {} },
  }, claim).kind, "invalid_response");

  const regression = parseTransportResponse({
    status: 200,
    body: {
      kind: "success",
      commandId: "cmd-1",
      record: {
        recordId: "record-1",
        payload: claim.attempted.payload,
        version: 2,
        deleted: false,
      },
    },
  }, claim);
  assert.deepEqual(regression, {
    kind: "invalid_response",
    reason: "remote-version-did-not-advance",
  });
});

test("keeps authentication and permanent validation distinct", () => {
  assert.deepEqual(parseTransportResponse({
    status: 401,
    body: { kind: "unauthorized", commandId: "cmd-1" },
  }, claim), { kind: "blocked_auth", reason: "unauthorized" });

  assert.deepEqual(parseTransportResponse({
    status: 422,
    body: { kind: "permanent-failure", commandId: "cmd-1", reason: "bad title" },
  }, claim), { kind: "permanent", reason: "bad title" });
});
