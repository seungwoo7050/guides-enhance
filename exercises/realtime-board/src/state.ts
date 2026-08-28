import { randomUUID } from "node:crypto";

import { BOARD_HEIGHT, BOARD_WIDTH, type BoardSnapshot, type ServerEvent } from "./protocol";

interface BoardState extends BoardSnapshot {}

type PatchEvent = Extract<ServerEvent, { type: "board.patch" }>;
type PreviewEvent = Extract<ServerEvent, { type: "item.preview" }>;

export type MutationResult =
  | { kind: "committed"; event: PatchEvent }
  | { kind: "preview"; event: PreviewEvent }
  | { kind: "stale"; snapshot: BoardSnapshot };

// [Implementation 2] Mutable board snapshots and defensive copies
export class BoardStore {
  private readonly boards = new Map<string, BoardState>();

  snapshot(boardId: string): BoardSnapshot {
    return cloneSnapshot(this.board(boardId));
  }

  // [Implementation 3] Version-checked board mutation
  createItem(boardId: string, input: { content: string; x: number; y: number }): MutationResult {
    assertPosition(input.x, input.y);
    const board = this.board(boardId);
    const item = {
      id: randomUUID(),
      content: input.content,
      x: input.x,
      y: input.y,
      version: 1
    };
    board.items.push(item);
    return this.commit(board, "item.create", item);
  }

  updateItem(
    boardId: string,
    input: { itemId: string; content: string; baseVersion: number }
  ): MutationResult {
    const board = this.board(boardId);
    const item = board.items.find((candidate) => candidate.id === input.itemId);
    if (!item || item.version !== input.baseVersion) {
      return { kind: "stale", snapshot: cloneSnapshot(board) };
    }

    item.content = input.content;
    item.version += 1;
    return this.commit(board, "item.update", item);
  }

  moveItem(
    boardId: string,
    input: { itemId: string; x: number; y: number; baseVersion: number; final: boolean }
  ): MutationResult {
    assertPosition(input.x, input.y);
    const board = this.board(boardId);
    const item = board.items.find((candidate) => candidate.id === input.itemId);
    if (!item || item.version !== input.baseVersion) {
      return { kind: "stale", snapshot: cloneSnapshot(board) };
    }

    if (!input.final) {
      return {
        kind: "preview",
        event: {
          type: "item.preview",
          preview: {
            boardId,
            itemId: input.itemId,
            x: input.x,
            y: input.y,
            baseVersion: input.baseVersion
          }
        }
      };
    }

    item.x = input.x;
    item.y = input.y;
    item.version += 1;
    return this.commit(board, "item.move", item);
  }

  private board(boardId: string): BoardState {
    const existing = this.boards.get(boardId);
    if (existing) return existing;
    const created: BoardState = { boardId, version: 0, sequence: 0, items: [] };
    this.boards.set(boardId, created);
    return created;
  }

  private commit(
    board: BoardState,
    operation: PatchEvent["patch"]["operation"],
    item: BoardSnapshot["items"][number]
  ): MutationResult {
    board.version += 1;
    board.sequence += 1;
    return {
      kind: "committed",
      event: {
        type: "board.patch",
        patch: {
          boardId: board.boardId,
          boardVersion: board.version,
          sequence: board.sequence,
          operation,
          item: { ...item }
        }
      }
    };
  }
}

function cloneSnapshot(snapshot: BoardSnapshot): BoardSnapshot {
  return {
    ...snapshot,
    items: snapshot.items.map((item) => ({ ...item }))
  };
}

function assertPosition(x: number, y: number): void {
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > BOARD_WIDTH || y < 0 || y > BOARD_HEIGHT) {
    throw new RangeError("보드 좌표가 허용 범위를 벗어났습니다.");
  }
}
