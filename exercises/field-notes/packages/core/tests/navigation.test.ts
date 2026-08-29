import assert from "node:assert/strict";
import test from "node:test";
import {
  CrossSourceRouteArbiter,
  LatestNavigationIntentBuffer,
  OneShotNavigationPermit,
  RecentIntentSet,
  applyReservedRoute,
  decideDraftBack,
  decideNavigation,
  handlePreventedDraftNavigation,
  navigationIntentKey,
  normalizeRecordId,
  parseNavigationIntent,
  requestDraftLeave,
} from "../src/index.ts";

test("normalizes bounded opaque record identifiers", () => {
  assert.deepEqual(normalizeRecordId(" Record_42 "), {
    kind: "valid",
    recordId: "record_42",
  });
  assert.equal(normalizeRecordId("").kind, "invalid");
  assert.equal(normalizeRecordId("a/b").kind, "invalid");
  assert.equal(normalizeRecordId("x".repeat(65)).kind, "invalid");
});

test("parses custom-scheme, restoration, and Expo development inputs", () => {
  assert.deepEqual(parseNavigationIntent("fieldnotes://records/R-1/edit"), {
    kind: "open-record",
    recordId: "r-1",
    destination: "edit",
    source: "link",
  });
  assert.deepEqual(parseNavigationIntent("/records/r-2", "restoration"), {
    kind: "open-record",
    recordId: "r-2",
    destination: "detail",
    source: "restoration",
  });
  assert.deepEqual(parseNavigationIntent("exp://127.0.0.1:8081/--/sync"), {
    kind: "open-sync",
    source: "link",
  });
});

test("rejects unexpected schemes, malformed encodings, and arbitrary routes", () => {
  assert.deepEqual(parseNavigationIntent("https://example.com/records/r-1"), {
    kind: "invalid",
    reason: "unexpected-scheme",
    source: "link",
  });
  assert.equal(parseNavigationIntent("fieldnotes://records/%zz").kind, "invalid");
  assert.equal(parseNavigationIntent("fieldnotes://admin").kind, "invalid");
  assert.equal(parseNavigationIntent("fieldnotes://records/a/b").kind, "invalid");
});

test("checks current record state before producing a protected route", async () => {
  const intent = parseNavigationIntent("fieldnotes://records/missing");
  const decision = await decideNavigation({
    intent,
    alreadyProcessed: false,
    recordExists: async () => false,
  });
  assert.deepEqual(decision, {
    kind: "missing-record",
    recordId: "missing",
    fallbackHref: "/records",
  });
});

test("uses source-independent normalized intent identities", () => {
  const link = parseNavigationIntent("fieldnotes://sync", "link");
  const notification = parseNavigationIntent("fieldnotes://sync", "notification");
  assert.equal(navigationIntentKey(link), "sync");
  assert.equal(navigationIntentKey(notification), "sync");
});

test("bounds recent input memory and keeps only the latest startup input", () => {
  const recent = new RecentIntentSet(2);
  assert.equal(recent.accept("a"), true);
  assert.equal(recent.accept("a"), false);
  assert.equal(recent.accept("b"), true);
  assert.equal(recent.accept("c"), true);
  assert.equal(recent.has("a"), false);

  const buffer = new LatestNavigationIntentBuffer();
  buffer.offer(parseNavigationIntent("/records", "restoration"));
  buffer.offer(parseNavigationIntent("/settings", "link"));
  assert.deepEqual(buffer.take(), { kind: "open-settings", source: "link" });
  assert.equal(buffer.take(), null);
});

test("shares one route reservation across validated input sources", () => {
  const arbiter = new CrossSourceRouteArbiter(2);
  const first = arbiter.reserve("/records/r-1");
  assert.notEqual(first, null);
  assert.equal(arbiter.reserve("/records/r-1"), null);
  first?.release();

  const retried = arbiter.reserve("/records/r-1");
  assert.notEqual(retried, null);
  let applied = false;
  if (retried) applyReservedRoute(retried, () => { applied = true; });
  assert.equal(applied, true);
  assert.equal(arbiter.reserve("/records/r-1"), null);
});

test("protects dirty drafts and allows one committed navigation", () => {
  assert.equal(decideDraftBack(true), "confirm-discard");
  assert.equal(decideDraftBack(false), "leave");

  const permit = new OneShotNavigationPermit();
  let dispatched = 0;
  let confirm: (() => void) | null = null;
  assert.equal(
    handlePreventedDraftNavigation(
      permit,
      (discard) => { confirm = discard; },
      () => { dispatched += 1; },
    ),
    "confirmation-requested",
  );
  assert.equal(dispatched, 0);
  (confirm as (() => void) | null)?.();
  assert.equal(dispatched, 1);

  permit.grant();
  assert.equal(
    handlePreventedDraftNavigation(permit, () => assert.fail(), () => { dispatched += 1; }),
    "bypassed",
  );
  assert.equal(dispatched, 2);

  assert.equal(requestDraftLeave(false, () => assert.fail(), () => { dispatched += 1; }), "left");
  assert.equal(dispatched, 3);
});
