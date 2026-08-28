import { z } from "zod";

export const BOARD_WIDTH = 1_600;
export const BOARD_HEIGHT = 900;

const boardId = z.string().min(1).max(128);
const itemId = z.string().min(1).max(128);
const xCoordinate = z.number().finite().min(0).max(BOARD_WIDTH);
const yCoordinate = z.number().finite().min(0).max(BOARD_HEIGHT);

// [Implementation 1] Validated client message types
export const ClientEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId }),
  z.object({ type: z.literal("cursor.move"), boardId, x: xCoordinate, y: yCoordinate }),
  z.object({
    type: z.literal("item.create"),
    boardId,
    content: z.string().trim().min(1).max(500),
    x: xCoordinate,
    y: yCoordinate
  }),
  z.object({
    type: z.literal("item.update"),
    boardId,
    itemId,
    content: z.string().trim().min(1).max(500),
    baseVersion: z.number().int().positive()
  }),
  z.object({
    type: z.literal("item.move"),
    boardId,
    itemId,
    x: xCoordinate,
    y: yCoordinate,
    baseVersion: z.number().int().positive(),
    final: z.boolean()
  }),
  z.object({
    type: z.literal("snapshot.request"),
    boardId,
    afterSequence: z.number().int().nonnegative().optional()
  })
]);

export type ClientEvent = z.infer<typeof ClientEventSchema>;

export interface BoardItem {
  id: string;
  content: string;
  x: number;
  y: number;
  version: number;
}

export interface BoardSnapshot {
  boardId: string;
  version: number;
  sequence: number;
  items: BoardItem[];
}

export type ServerEvent =
  | { type: "board.snapshot"; snapshot: BoardSnapshot }
  | {
      type: "board.patch";
      patch: {
        boardId: string;
        boardVersion: number;
        sequence: number;
        operation: "item.create" | "item.update" | "item.move";
        item: BoardItem;
      };
    }
  | { type: "item.preview"; preview: { boardId: string; itemId: string; x: number; y: number; baseVersion: number } }
  | { type: "cursor.moved"; cursor: { boardId: string; clientId: string; x: number; y: number } }
  | { type: "presence.changed"; boardId: string; members: string[] }
  | { type: "board.closed"; boardId: string; reason: string };
