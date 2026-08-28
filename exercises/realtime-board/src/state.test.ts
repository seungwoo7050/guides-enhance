import { describe, expect, it } from "vitest";

import { BoardStore } from "./state";

describe("BoardStore", () => {
  it("미리보기는 저장하지 않고 유효한 최종 이동만 확정합니다", () => {
    const store = new BoardStore();
    expect(store.createItem("planning", { content: "이동할 항목", x: 10, y: 20 })).toMatchObject({
      kind: "committed",
      event: {
        patch: {
          sequence: 1,
          boardVersion: 1,
          item: { content: "이동할 항목", version: 1 }
        }
      }
    });
    const item = store.snapshot("planning").items[0]!;

    expect(store.moveItem("planning", {
      itemId: item.id,
      x: 900,
      y: 800,
      baseVersion: item.version,
      final: false
    })).toMatchObject({ kind: "preview" });
    expect(store.snapshot("planning")).toMatchObject({
      sequence: 1,
      items: [{ x: 10, y: 20, version: 1 }]
    });

    expect(store.moveItem("planning", {
      itemId: item.id,
      x: 300,
      y: 240,
      baseVersion: item.version,
      final: true
    })).toMatchObject({
      kind: "committed",
      event: {
        patch: {
          sequence: 2,
          boardVersion: 2,
          item: { x: 300, y: 240, version: 2 }
        }
      }
    });
    expect(store.snapshot("planning").items[0]).toMatchObject({
      x: 300,
      y: 240,
      version: 2
    });
  });

  it("보드 범위 밖 좌표를 거부합니다", () => {
    const store = new BoardStore();
    expect(() => store.createItem("planning", { content: "범위 밖", x: -1, y: 0 }))
      .toThrow(/허용 범위/);
    expect(() => store.createItem("planning", { content: "범위 밖", x: 0, y: 901 }))
      .toThrow(/허용 범위/);
    expect(store.snapshot("planning")).toMatchObject({ sequence: 0, items: [] });
  });

  it("오래된 쓰기는 값을 바꾸지 않고 현재 스냅샷을 반환합니다", () => {
    const store = new BoardStore();
    store.createItem("planning", { content: "원본", x: 10, y: 20 });
    const item = store.snapshot("planning").items[0]!;
    store.updateItem("planning", {
      itemId: item.id,
      content: "현재 값",
      baseVersion: item.version
    });

    expect(store.updateItem("planning", {
      itemId: item.id,
      content: "오래된 값",
      baseVersion: item.version
    })).toMatchObject({
      kind: "stale",
      snapshot: {
        sequence: 2,
        items: [{ content: "현재 값", version: 2 }]
      }
    });
  });
});
