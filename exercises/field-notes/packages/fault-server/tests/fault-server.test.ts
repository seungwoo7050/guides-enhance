import assert from "node:assert/strict";
import test from "node:test";
import { DeterministicFaultServer, ResponseLostError } from "../src/index.ts";
import type { RecordCommand } from "../src/index.ts";

function command(overrides: Partial<RecordCommand> = {}): RecordCommand {
  return {
    commandId: "cmd-1",
    recordId: "record-1",
    operation: "upsert",
    baseVersion: null,
    localRevision: 1,
    payload: {
      title: "Bridge inspection",
      notes: "North expansion joint",
      status: "open",
      observedAt: "2026-08-22T00:00:00.000Z",
    },
    createdAt: "2026-08-22T00:00:01.000Z",
    ...overrides,
  };
}

test("memoizes remote application before simulated response loss", async () => {
  const server = new DeterministicFaultServer();
  server.enqueueFault({ commandId: "cmd-1", fault: { kind: "response-loss" } });

  await assert.rejects(server.execute(command()), ResponseLostError);
  const retry = await server.execute(command());

  assert.equal(retry.status, 200);
  assert.equal((retry.body as { replayed: boolean }).replayed, true);
  assert.equal(server.snapshot().applyCountByCommand["cmd-1"], 1);
});

test("rejects command identity reuse with a different attempted payload", async () => {
  const server = new DeterministicFaultServer();
  await server.execute(command());
  const response = await server.execute(command({
    payload: {
      title: "Changed payload",
      notes: "must not reuse identity",
      status: "open",
      observedAt: "2026-08-22T00:00:00.000Z",
    },
  }));

  assert.equal(response.status, 409);
  assert.equal((response.body as { kind: string }).kind, "command-identity-reuse");
  assert.equal(server.snapshot().applyCountByCommand["cmd-1"], 1);
});

test("returns a conflict when the attempted base version is stale", async () => {
  const server = new DeterministicFaultServer();
  await server.execute(command());
  const response = await server.execute(command({
    commandId: "cmd-2",
    localRevision: 2,
    baseVersion: null,
  }));

  assert.equal(response.status, 409);
  assert.equal((response.body as { kind: string }).kind, "conflict");
  assert.equal((response.body as { expectedBaseVersion: number }).expectedBaseVersion, 1);
});

test("keeps unauthorized and malformed responses outside canonical success state", async () => {
  const server = new DeterministicFaultServer();
  server.enqueueFault({ fault: { kind: "unauthorized" } });
  const unauthorized = await server.execute(command());
  assert.equal(unauthorized.status, 401);
  assert.deepEqual(server.snapshot().memoizedCommandIds, []);

  server.enqueueFault({ fault: { kind: "malformed-success", body: { ok: true } } });
  const malformed = await server.execute(command());
  assert.deepEqual(malformed, { status: 200, body: { ok: true } });
  assert.equal(server.snapshot().applyCountByCommand["cmd-1"], 1);
  const reconciled = await server.execute(command());
  assert.equal((reconciled.body as { kind: string }).kind, "success");
});
