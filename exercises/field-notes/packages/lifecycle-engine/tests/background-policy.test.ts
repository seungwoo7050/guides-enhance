import assert from "node:assert/strict";
import test from "node:test";
import {
  backgroundInvocationSucceeded,
  observeBackgroundSync,
  type SyncOpportunityResult,
} from "../src/index.ts";

function ran(input: {
  claimed: number;
  checkpoints: number;
  stopped: "budget" | "idle" | "aborted" | "checkpoint-failed" | "auth-blocked";
}): SyncOpportunityResult {
  return {
    kind: "ran",
    trigger: "background",
    workerId: "background-1",
    worker: {
      trigger: "background",
      workerId: "background-1",
      claimed: input.claimed,
      checkpoints: Array.from({ length: input.checkpoints }, (_, index) => index),
      stopped: input.stopped,
    },
  };
}

test("accepts only background runs with a durable checkpoint per claim", () => {
  const durable = observeBackgroundSync(ran({ claimed: 2, checkpoints: 2, stopped: "idle" }));
  assert.deepEqual(durable, { kind: "durable", claimed: 2, checkpoints: 2 });
  assert.equal(backgroundInvocationSucceeded(durable), true);

  const lostCheckpoint = observeBackgroundSync(
    ran({ claimed: 2, checkpoints: 1, stopped: "checkpoint-failed" }),
  );
  assert.deepEqual(lostCheckpoint, { kind: "failed", claimed: 2, checkpoints: 1 });
  assert.equal(backgroundInvocationSucceeded(lostCheckpoint), false);
});

test("rejects expired or aborted invocations", () => {
  assert.equal(observeBackgroundSync({
    kind: "not-started",
    trigger: "background",
    reason: "deadline",
  }).kind, "failed");
  assert.equal(observeBackgroundSync(ran({ claimed: 1, checkpoints: 1, stopped: "aborted" })).kind, "failed");
});
