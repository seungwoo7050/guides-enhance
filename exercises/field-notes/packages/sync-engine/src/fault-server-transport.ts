import type { DeterministicFaultServer } from "../../fault-server/src/server.ts";
import type { SyncTransport } from "./ports.ts";
import type { RecordCommand } from "./types.ts";

export class FaultServerTransport implements SyncTransport {
  readonly #server: DeterministicFaultServer;

  constructor(server: DeterministicFaultServer) {
    this.#server = server;
  }

  send(command: RecordCommand, signal: AbortSignal) {
    return this.#server.execute(command, signal);
  }
}
