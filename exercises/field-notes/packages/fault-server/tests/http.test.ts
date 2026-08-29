import assert from "node:assert/strict";
import test from "node:test";
import { createFaultHttpServer } from "../src/http.ts";

const command = {
  commandId: "cmd-http",
  recordId: "record-http",
  operation: "upsert",
  baseVersion: null,
  localRevision: 1,
  payload: {
    title: "HTTP path",
    notes: "local deterministic endpoint",
    status: "open",
    observedAt: "2026-08-22T00:00:00.000Z",
  },
  createdAt: "2026-08-22T00:00:01.000Z",
};

test("exposes command and control endpoints on an ephemeral port", async (context) => {
  const { server } = createFaultHttpServer();
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  context.after(() => new Promise<void>((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  }));

  const address = server.address();
  assert(address && typeof address === "object");
  const base = `http://127.0.0.1:${address.port}`;

  const response = await fetch(`${base}/commands`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(command),
  });
  assert.equal(response.status, 200);

  const snapshotResponse = await fetch(`${base}/__control/snapshot`);
  const snapshot = await snapshotResponse.json() as { records: unknown[] };
  assert.equal(snapshot.records.length, 1);
});
