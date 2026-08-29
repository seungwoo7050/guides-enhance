import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { pathToFileURL } from "node:url";
import process from "node:process";
import { DeterministicFaultServer } from "./server.ts";
import type { FaultPlan, RecordCommand } from "./types.ts";

const JSON_LIMIT = 256 * 1024;

async function readJson(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > JSON_LIMIT) throw new Error("request body exceeds 256 KiB");
    chunks.push(buffer);
  }
  if (chunks.length === 0) return null;
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function send(response: ServerResponse, status: number, body: unknown): void {
  const data = JSON.stringify(body);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(data),
    "cache-control": "no-store",
  });
  response.end(data);
}

export function createFaultHttpServer(engine = new DeterministicFaultServer()): {
  engine: DeterministicFaultServer;
  server: Server;
} {
  const server = createServer(async (request, response) => {
    try {
      const method = request.method ?? "GET";
      const url = new URL(request.url ?? "/", "http://localhost");

      if (method === "POST" && url.pathname === "/commands") {
        const wire = await engine.execute(await readJson(request) as RecordCommand);
        send(response, wire.status, wire.body);
        return;
      }
      if (method === "POST" && url.pathname === "/__control/faults") {
        engine.enqueueFault(await readJson(request) as FaultPlan);
        send(response, 202, { kind: "accepted" });
        return;
      }
      if (method === "POST" && url.pathname === "/__control/reset") {
        engine.reset();
        send(response, 200, { kind: "reset" });
        return;
      }
      if (method === "GET" && url.pathname === "/__control/snapshot") {
        send(response, 200, engine.snapshot());
        return;
      }
      send(response, 404, { kind: "not-found" });
    } catch (error) {
      send(response, 500, {
        kind: "server-error",
        reason: error instanceof Error ? error.message : String(error),
      });
    }
  });
  return { engine, server };
}

async function main(): Promise<void> {
  const port = Number.parseInt(process.env.PORT ?? "8787", 10);
  const host = process.env.HOST ?? "127.0.0.1";
  const { server } = createFaultHttpServer();
  await new Promise<void>((resolve) => server.listen(port, host, resolve));
  console.log(`Field Notes fault server listening on http://${host}:${port}`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
