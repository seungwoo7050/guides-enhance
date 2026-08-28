import WebSocket from "ws";

import type { ServerEvent } from "./protocol";

export type Role = "editor" | "viewer";

export interface ClientConnection {
  id: string;
  socket: WebSocket;
  boardId: string | null;
  alive: boolean;
  role: Role;
}

// [Implementation 4] Socket membership and room delivery
export class ConnectionHub {
  private readonly clients = new Set<ClientConnection>();

  add(client: ClientConnection): void {
    this.clients.add(client);
  }

  remove(client: ClientConnection): void {
    if (!this.clients.delete(client)) return;
    const previousBoard = client.boardId;
    client.boardId = null;
    if (previousBoard) this.broadcastPresence(previousBoard);
  }

  join(client: ClientConnection, boardId: string): void {
    if (!this.clients.has(client)) throw new Error("이 hub에 등록되지 않은 연결입니다.");
    const previousBoard = client.boardId;
    client.boardId = boardId;
    if (previousBoard && previousBoard !== boardId) this.broadcastPresence(previousBoard);
    this.broadcastPresence(boardId);
  }

  broadcast(boardId: string, event: ServerEvent): void {
    for (const client of this.clients) {
      if (client.boardId === boardId) this.send(client, event);
    }
  }

  send(client: ClientConnection, event: ServerEvent): void {
    if (client.socket.readyState === WebSocket.OPEN) {
      client.socket.send(JSON.stringify(event));
    }
  }

  all(): ClientConnection[] {
    return [...this.clients];
  }

  closeAll(): void {
    const clients = [...this.clients];
    this.clients.clear();
    for (const client of clients) {
      client.boardId = null;
      client.socket.terminate();
    }
  }

  private broadcastPresence(boardId: string): void {
    const members = [...this.clients]
      .filter((client) => client.boardId === boardId)
      .map((client) => client.id)
      .sort();
    this.broadcast(boardId, { type: "presence.changed", boardId, members });
  }
}
