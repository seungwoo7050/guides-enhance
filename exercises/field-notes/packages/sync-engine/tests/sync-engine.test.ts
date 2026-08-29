import assert from "node:assert/strict";
import test from "node:test";
import { DeterministicFaultServer } from "../../fault-server/src/server.ts";
import {
  BoundedSyncWorker,
  FaultServerTransport,
  FixedSyncBudget,
  InMemorySyncRepository,
  ManualSyncClock,
} from "../src/index.ts";

const payload = {
  title: "Retaining wall",
  notes: "Crack at marker 12",
  status: "open" as const,
  observedAt: "2026-08-22T00:00:00.000Z",
};

function worker(input: {
  repository: InMemorySyncRepository;
  server: DeterministicFaultServer;
  clock: ManualSyncClock;
  maxCommands?: number;
  maxAttempts?: number;
}) {
  return new BoundedSyncWorker({
    repository: input.repository,
    transport: new FaultServerTransport(input.server),
    clock: input.clock,
    budget: new FixedSyncBudget({
      maxCommands: input.maxCommands ?? 1,
      leaseDurationMs: 1_000,
      retryDelayMs: 100,
      maxAttempts: input.maxAttempts ?? 5,
    }),
  });
}

test("retries an unknown response with the immutable attempted command", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-1",
    recordId: "record-1",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const server = new DeterministicFaultServer();
  server.enqueueFault({ commandId: "cmd-1", fault: { kind: "response-loss" } });
  const clock = new ManualSyncClock(0);
  const sync = worker({ repository, server, clock });

  const first = await sync.run({ trigger: "foreground", workerId: "worker-1" });
  assert.equal(first.checkpoints[0]?.state, "retry_wait");
  clock.advance(100);
  const second = await sync.run({ trigger: "background", workerId: "worker-2" });
  assert.equal(second.checkpoints[0]?.state, "completed");
  assert.equal(server.snapshot().applyCountByCommand["cmd-1"], 1);

  const snapshot = await repository.snapshot();
  assert.equal(snapshot.records[0]?.syncState, "synced");
  assert.deepEqual(
    (snapshot.commands[0]?.state.kind === "completed" && snapshot.commands[0].state.attempted),
    snapshot.commands[0]?.command,
  );
});

test("prevents overlapping claims until the live lease expires", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-lease",
    recordId: "record-lease",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });

  const first = await repository.claimNext({ workerId: "a", now: 0, leaseDurationMs: 1_000 });
  assert(first);
  assert.equal(await repository.claimNext({ workerId: "b", now: 999, leaseDurationMs: 1_000 }), null);
  const recovered = await repository.claimNext({ workerId: "b", now: 1_000, leaseDurationMs: 1_000 });
  assert(recovered);
  assert.equal(recovered.commandId, first.commandId);
  assert.equal(recovered.attempt, 2);
  assert.deepEqual(recovered.attempted, first.attempted);
  assert.notEqual(recovered.lease.token, first.lease.token);
});

test("preserves a newer local edit and rebases only its unattempted command", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-a",
    recordId: "record-1",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const claim = await repository.claimNext({ workerId: "worker", now: 0, leaseDurationMs: 1_000 });
  assert(claim);

  const newer = { ...payload, notes: "Newer local observation" };
  repository.saveLocalMutation({
    commandId: "cmd-b",
    recordId: "record-1",
    operation: "upsert",
    payload: newer,
    createdAt: "2026-08-22T00:00:02.000Z",
    expectedLocalRevision: 1,
  });

  const checkpoint = await repository.checkpoint(claim, {
    kind: "success",
    remote: { recordId: "record-1", payload, version: 1, deleted: false },
    completedAt: 10,
  });
  assert.deepEqual(checkpoint.rebased, [{
    previousCommandId: "cmd-b",
    commandId: "cmd-b-rebase-1",
    baseVersion: 1,
  }]);

  const snapshot = await repository.snapshot();
  assert.deepEqual(snapshot.records[0]?.payload, newer);
  assert.equal(snapshot.records[0]?.knownRemoteVersion, 1);
  assert.equal(snapshot.commands[1]?.command.baseVersion, 1);
});

test("durably blocks unauthorized commands until explicit credential recovery", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-auth",
    recordId: "record-auth",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const server = new DeterministicFaultServer();
  server.enqueueFault({ fault: { kind: "unauthorized" } });
  const clock = new ManualSyncClock(0);
  const sync = worker({ repository, server, clock });

  const blocked = await sync.run({ trigger: "manual", workerId: "auth-worker" });
  assert.equal(blocked.stopped, "auth-blocked");
  assert.equal(await repository.claimNext({ workerId: "other", now: 10_000, leaseDurationMs: 1_000 }), null);
  assert.equal(await repository.resumeBlockedAuth(10_000), 1);
  clock.set(10_000);
  const completed = await sync.run({ trigger: "app-active", workerId: "recovered-worker" });
  assert.equal(completed.checkpoints[0]?.state, "completed");
});

test("preserves both sides of a conflict and creates a new resolution command", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-local",
    recordId: "record-conflict",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const claim = await repository.claimNext({ workerId: "worker", now: 0, leaseDurationMs: 1_000 });
  assert(claim);
  const remote = {
    recordId: "record-conflict",
    payload: { ...payload, notes: "Remote edit" },
    version: 4,
    deleted: false,
  };
  await repository.checkpoint(claim, { kind: "conflict", remote, createdAt: 10 });
  const snapshot = await repository.snapshot();
  const conflict = snapshot.conflicts[0];
  assert(conflict);
  assert.deepEqual(conflict.local.payload, payload);
  assert.deepEqual(conflict.remote, remote);

  const resolution = await repository.resolveConflict(conflict.conflictId, {
    kind: "merge",
    commandId: "cmd-resolution",
    payload: { ...payload, notes: "Merged edit" },
    createdAt: "2026-08-22T00:00:03.000Z",
    resolvedAt: 20,
  });
  assert.equal(resolution.command?.command.baseVersion, 4);
  assert.equal(resolution.command?.command.commandId, "cmd-resolution");
});

test("stops after a local checkpoint failure and recovers after lease expiry", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-checkpoint",
    recordId: "record-checkpoint",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  repository.failNextCheckpoint();
  const server = new DeterministicFaultServer();
  const clock = new ManualSyncClock(0);
  const sync = worker({ repository, server, clock });

  const failed = await sync.run({ trigger: "foreground", workerId: "worker-a" });
  assert.equal(failed.stopped, "checkpoint-failed");
  assert.equal(server.snapshot().applyCountByCommand["cmd-checkpoint"], 1);

  clock.advance(1_000);
  const recovered = await sync.run({ trigger: "app-active", workerId: "worker-b" });
  assert.equal(recovered.checkpoints[0]?.state, "completed");
  assert.equal(server.snapshot().applyCountByCommand["cmd-checkpoint"], 1);
});

test("supersedes newer pending edits when local conflict state is retried", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-conflicted",
    recordId: "record-resolution",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const claim = await repository.claimNext({
    workerId: "worker",
    now: 0,
    leaseDurationMs: 1_000,
  });
  assert(claim);

  const newer = { ...payload, notes: "Edited while the first command was in flight" };
  repository.saveLocalMutation({
    commandId: "cmd-newer",
    recordId: "record-resolution",
    operation: "upsert",
    payload: newer,
    createdAt: "2026-08-22T00:00:02.000Z",
    expectedLocalRevision: 1,
  });
  await repository.checkpoint(claim, {
    kind: "conflict",
    remote: {
      recordId: "record-resolution",
      payload: { ...payload, notes: "Remote edit" },
      version: 8,
      deleted: false,
    },
    createdAt: 10,
  });

  const beforeResolution = await repository.snapshot();
  const conflict = beforeResolution.conflicts[0];
  assert(conflict);
  const resolution = await repository.resolveConflict(conflict.conflictId, {
    kind: "local",
    commandId: "cmd-resolution",
    createdAt: "2026-08-22T00:00:03.000Z",
    resolvedAt: 20,
  });

  assert.equal(resolution.command?.command.commandId, "cmd-resolution");
  assert.deepEqual(resolution.command?.command.payload, newer);
  const snapshot = await repository.snapshot();
  assert.deepEqual(snapshot.commands[1]?.state, {
    kind: "superseded",
    supersededBy: "cmd-resolution",
    completedAt: 20,
  });
  assert.equal(snapshot.records[0]?.knownRemoteVersion, 8);
  assert.deepEqual(snapshot.records[0]?.payload, newer);

  const next = await repository.claimNext({
    workerId: "resolution-worker",
    now: 21,
    leaseDurationMs: 1_000,
  });
  assert.equal(next?.commandId, "cmd-resolution");
  assert.deepEqual(next?.attempted.payload, newer);
});

test("supersedes newer pending edits when remote conflict state is accepted", async () => {
  const repository = new InMemorySyncRepository();
  repository.saveLocalMutation({
    commandId: "cmd-conflicted-remote",
    recordId: "record-remote-resolution",
    operation: "upsert",
    payload,
    createdAt: "2026-08-22T00:00:01.000Z",
  });
  const claim = await repository.claimNext({
    workerId: "worker",
    now: 0,
    leaseDurationMs: 1_000,
  });
  assert(claim);

  repository.saveLocalMutation({
    commandId: "cmd-newer-remote",
    recordId: "record-remote-resolution",
    operation: "upsert",
    payload: { ...payload, notes: "Unsynchronized local edit" },
    createdAt: "2026-08-22T00:00:02.000Z",
    expectedLocalRevision: 1,
  });
  const remote = {
    recordId: "record-remote-resolution",
    payload: { ...payload, notes: "Accepted remote edit" },
    version: 5,
    deleted: false,
  };
  await repository.checkpoint(claim, {
    kind: "conflict",
    remote,
    createdAt: 10,
  });
  const beforeResolution = await repository.snapshot();
  const conflict = beforeResolution.conflicts[0];
  assert(conflict);

  await repository.resolveConflict(conflict.conflictId, {
    kind: "remote",
    resolvedAt: 20,
  });
  const snapshot = await repository.snapshot();
  assert.deepEqual(snapshot.commands[1]?.state, {
    kind: "superseded",
    supersededBy: null,
    completedAt: 20,
  });
  assert.deepEqual(snapshot.records[0]?.payload, remote.payload);
  assert.equal(snapshot.records[0]?.syncState, "synced");
  assert.equal(
    await repository.claimNext({ workerId: "other", now: 21, leaseDurationMs: 1_000 }),
    null,
  );
});
