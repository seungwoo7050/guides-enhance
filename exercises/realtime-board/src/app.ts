import { randomUUID } from "node:crypto";

import websocket from "@fastify/websocket";
import Fastify, { type FastifyRequest } from "fastify";
import type { RawData, WebSocket } from "ws";

import { ConnectionHub, type ClientConnection, type Role } from "./hub";
import { ClientEventSchema, type ClientEvent } from "./protocol";
import { BoardStore } from "./state";

export interface RealtimeAppOptions {
  resolveRole?: (request: FastifyRequest) => Role;
}

// [Implementation 5] Per-app realtime state
export async function buildApp({
  resolveRole = () => "editor"
}: RealtimeAppOptions = {}) {
  const app = Fastify({ logger: false });
  const boards = new BoardStore();
  const hub = new ConnectionHub();
  await app.register(websocket);

  // [Implementation 6] Message parsing and join requirement
  app.get("/ws", { websocket: true }, (socket, request) => {
    const client: ClientConnection = {
      id: randomUUID(),
      socket: socket as WebSocket,
      boardId: null,
      alive: true,
      role: resolveRole(request)
    };
    hub.add(client);

    socket.on("close", () => {
      hub.remove(client);
    });
    socket.on("message", (raw: RawData) => {
      const parsed = ClientEventSchema.safeParse(safeJson(String(raw)));
      if (!parsed.success) {
        client.socket.close(1008, "메시지 형식이 올바르지 않습니다.");
        return;
      }
      dispatch(client, parsed.data);
    });
  });

  function dispatch(client: ClientConnection, event: ClientEvent): void {
    if (event.type === "board.join") {
      hub.join(client, event.boardId);
      hub.send(client, { type: "board.snapshot", snapshot: boards.snapshot(event.boardId) });
      return;
    }

    if (client.boardId !== event.boardId) {
      client.socket.close(1008, "먼저 보드에 참가해야 합니다.");
      return;
    }

    // [Implementation 7] Viewer write rejection
    if (client.role === "viewer") {
      client.socket.close(1008, "쓰기 권한이 필요합니다.");
      return;
    }

  }

  return app;
}

function safeJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
