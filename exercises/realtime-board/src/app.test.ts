import { afterEach, describe, expect, it } from "vitest";
import type { RawData, WebSocket } from "ws";

import { buildApp } from "./app";

function next(socket: WebSocket, type: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${type} 메시지를 기다리다 시간이 초과되었습니다.`)), 1_000);
    const handler = (raw: RawData) => {
      const message = JSON.parse(String(raw));
      if (message.type !== type) return;
      clearTimeout(timer);
      socket.off("message", handler);
      resolve(message);
    };
    socket.on("message", handler);
  });
}

function closed(socket: WebSocket): Promise<number> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("연결 종료를 기다리다 시간이 초과되었습니다.")), 1_000);
    socket.once("close", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

describe("실시간 보드 프로토콜", () => {
  let app: Awaited<ReturnType<typeof buildApp>> | undefined;

  afterEach(async () => {
    await app?.close();
  });

  it("확정 패치를 같은 시퀀스로 전송하고 스냅샷으로 복구합니다", async () => {
    app = await buildApp();
    await app.ready();
    const first = await app.injectWS("/ws") as WebSocket;
    const second = await app.injectWS("/ws") as WebSocket;

    for (const socket of [first, second]) {
      const snapshot = next(socket, "board.snapshot");
      socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
      expect((await snapshot).snapshot.boardId).toBe("planning");
    }

    const firstPatch = next(first, "board.patch");
    const secondPatch = next(second, "board.patch");
    first.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "검토",
      x: 100,
      y: 120
    }));
    expect((await firstPatch).patch).toEqual((await secondPatch).patch);

    const recovered = next(second, "board.snapshot");
    second.send(JSON.stringify({ type: "snapshot.request", boardId: "planning", afterSequence: 0 }));
    expect((await recovered).snapshot).toMatchObject({
      sequence: 1,
      items: [{ content: "검토" }]
    });
  });

  it("viewer가 영속 변경을 시도하면 연결을 닫습니다", async () => {
    app = await buildApp({
      resolveRole: (request) => request.headers["x-role"] === "viewer" ? "viewer" : "editor"
    });
    await app.ready();
    const viewer = await app.injectWS("/ws", { headers: { "x-role": "viewer" } }) as WebSocket;
    const joined = next(viewer, "board.snapshot");
    viewer.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
    await joined;

    const closeCode = closed(viewer);
    viewer.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "허용되지 않은 변경",
      x: 0,
      y: 0
    }));
    expect(await closeCode).toBe(1008);
  });

  it("잘못된 메시지와 참가 전 요청을 거부합니다", async () => {
    app = await buildApp();
    await app.ready();
    const malformed = await app.injectWS("/ws") as WebSocket;
    const malformedClose = closed(malformed);
    malformed.send("{");
    expect(await malformedClose).toBe(1008);

    const unjoined = await app.injectWS("/ws") as WebSocket;
    const unjoinedClose = closed(unjoined);
    unjoined.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    expect(await unjoinedClose).toBe(1008);
  });
});
