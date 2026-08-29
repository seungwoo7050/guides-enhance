import assert from "node:assert/strict";
import test from "node:test";
import { InMemorySyncRepository } from "../src/index.ts";

const payload = {
  title: "Retaining wall",
  notes: "Crack at marker 12",
  status: "open" as const,
  observedAt: "2026-08-22T00:00:00.000Z",
};

test("prevents overlapping claims until the live lease expires", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({ commandId: "cmd-lease", recordId: "record-lease", operation: "upsert", payload, createdAt: "2026-08-22T00:00:01.000Z" });
  const first = await repository.claimNext({ workerId: "a", now: 0, leaseDurationMs: 1_000 });
  assert(first);
  assert.equal(await repository.claimNext({ workerId: "b", now: 999, leaseDurationMs: 1_000 }), null);
  const recovered = await repository.claimNext({ workerId: "b", now: 1_000, leaseDurationMs: 1_000 });
  assert.equal(recovered?.attempt, 2);
  assert.deepEqual(recovered?.attempted, first.attempted);
});

test("preserves both sides of a conflict", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({ commandId: "cmd-local", recordId: "record-conflict", operation: "upsert", payload, createdAt: "2026-08-22T00:00:01.000Z" });
  const claim = await repository.claimNext({ workerId: "worker", now: 0, leaseDurationMs: 1_000 });
  assert(claim);
  const remote = { recordId: "record-conflict", payload: { ...payload, notes: "Remote edit" }, version: 4, deleted: false };
  await repository.checkpoint(claim, { kind: "conflict", remote, createdAt: 10 });
  const conflict = (await repository.snapshot()).conflicts[0];
  assert.deepEqual(conflict?.local.payload, payload);
  assert.deepEqual(conflict?.remote, remote);
});
