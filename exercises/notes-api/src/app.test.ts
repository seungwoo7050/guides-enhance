import { describe, expect, it } from "vitest";
import { buildApp } from "./app.js";
import { MemoryMemoRepository } from "./repository.js";

describe("메모 API", () => {
  it("입력을 검사하고 메모를 생성하며 중복 제목을 거부합니다", async () => {
    const app = buildApp(new MemoryMemoRepository());
    await app.ready();
    try {
      const invalid = await app.inject({ method: "POST", url: "/memos", payload: { title: "" } });
      expect(invalid.statusCode).toBe(400);
      expect(invalid.json()).toEqual({
        code: "invalid_request",
        message: "요청 형식이 올바르지 않습니다."
      });

      const malformed = await app.inject({
        method: "POST",
        url: "/memos",
        headers: { "content-type": "application/json" },
        payload: "{"
      });
      expect(malformed.statusCode).toBe(400);
      expect(malformed.json()).toEqual({
        code: "invalid_request",
        message: "요청 형식이 올바르지 않습니다."
      });
      expect(invalid.body + malformed.body).not.toContain("issues");

      const created = await app.inject({
        method: "POST",
        url: "/memos",
        payload: { title: "one", body: "body" }
      });
      expect(created.statusCode).toBe(201);

      const duplicate = await app.inject({
        method: "POST",
        url: "/memos",
        payload: { title: "one" }
      });
      expect(duplicate.statusCode).toBe(409);
      expect(duplicate.json()).toEqual({
        code: "title_taken",
        message: "같은 제목의 메모가 이미 있습니다."
      });
    } finally {
      await app.close();
    }
  });

  it("없는 메모에는 일관된 404 응답을 반환합니다", async () => {
    const app = buildApp(new MemoryMemoRepository());
    await app.ready();
    try {
      const response = await app.inject({ method: "GET", url: "/memos/missing" });
      expect(response.statusCode).toBe(404);
      expect(response.json()).toEqual({
        code: "not_found",
        message: "메모를 찾을 수 없습니다."
      });
    } finally {
      await app.close();
    }
  });

  it("예상하지 못한 오류에서 내부 정보를 노출하지 않습니다", async () => {
    class FailingMemoRepository extends MemoryMemoRepository {
      override async list(): Promise<never> {
        throw new Error("password_hash column is unavailable");
      }
    }

    const app = buildApp(new FailingMemoRepository());
    await app.ready();
    try {
      const response = await app.inject({ method: "GET", url: "/memos" });
      expect(response.statusCode).toBe(500);
      expect(response.json()).toEqual({
        code: "internal_error",
        message: "요청을 처리하지 못했습니다."
      });
      expect(response.body).not.toContain("password_hash");
    } finally {
      await app.close();
    }
  });
});
