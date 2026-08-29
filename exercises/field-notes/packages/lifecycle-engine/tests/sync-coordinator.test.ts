import assert from "node:assert/strict";
import test from "node:test";
import {
  LifecycleSyncCoordinator,
  SequentialWorkerIdGenerator,
} from "../src/index.ts";

class ManualClock {
  value = 0;
  now() { return this.value; }
}

class ManualScheduler {
  callbacks: Array<{ at: number; callback: () => void }> = [];
  schedule(at: number, callback: () => void) {
    const entry = { at, callback };
    this.callbacks.push(entry);
    return () => {
      this.callbacks = this.callbacks.filter((candidate) => candidate !== entry);
    };
  }
  fire() {
    for (const entry of [...this.callbacks]) entry.callback();
  }
}

test("passes every lifecycle trigger to the same bounded worker port", async () => {
  const seen: string[] = [];
  const clock = new ManualClock();
  const scheduler = new ManualScheduler();
  const coordinator = new LifecycleSyncCoordinator({
    clock,
    scheduler,
    ids: new SequentialWorkerIdGenerator(),
    worker: {
      async run(input) {
        seen.push(input.trigger);
        return { ...input, claimed: 0, checkpoints: [], stopped: "idle" };
      },
    },
  });

  for (const trigger of ["manual", "app-active", "background", "notification"] as const) {
    const result = await coordinator.run({ trigger });
    assert.equal(result.kind, "ran");
  }
  assert.deepEqual(seen, ["manual", "app-active", "background", "notification"]);
});

test("coalesces concurrent process-local triggers without extending the leader deadline", async () => {
  const clock = new ManualClock();
  const scheduler = new ManualScheduler();
  let resolveWorker!: () => void;
  const gate = new Promise<void>((resolve) => { resolveWorker = resolve; });
  const coordinator = new LifecycleSyncCoordinator({
    clock,
    scheduler,
    ids: new SequentialWorkerIdGenerator(),
    worker: {
      async run(input) {
        await gate;
        return { ...input, claimed: 0, checkpoints: [], stopped: "idle" };
      },
    },
  });

  const leader = coordinator.run({ trigger: "background", deadlineAt: 100 });
  const follower = coordinator.run({ trigger: "app-active", deadlineAt: 10_000 });
  resolveWorker();
  const [leaderResult, followerResult] = await Promise.all([leader, follower]);
  assert.equal(leaderResult.kind, "ran");
  assert.equal(followerResult.kind, "coalesced");
  if (followerResult.kind === "coalesced") assert.equal(followerResult.leaderTrigger, "background");
});

test("does not start work after the opportunity deadline", async () => {
  const clock = new ManualClock();
  clock.value = 10;
  const coordinator = new LifecycleSyncCoordinator({
    clock,
    scheduler: new ManualScheduler(),
    ids: new SequentialWorkerIdGenerator(),
    worker: { async run() { throw new Error("must not run"); } },
  });
  assert.deepEqual(await coordinator.run({ trigger: "background", deadlineAt: 10 }), {
    kind: "not-started",
    trigger: "background",
    reason: "deadline",
  });
});
