import assert from "node:assert/strict";
import test from "node:test";
import { searchUsers } from "../lib/fake-api.ts";

test("빈 검색어는 전체 사용자 목록을 반환합니다", async () => {
  const users = await searchUsers("", new AbortController().signal);
  assert.deepEqual(users.map((user) => user.handle), ["alpha", "beta", "gamma"]);
});

test("검색어의 앞뒤 공백과 대소문자를 정리합니다", async () => {
  const users = await searchUsers("  BETA ", new AbortController().signal);
  assert.deepEqual(users.map((user) => user.handle), ["beta"]);
});

test("정해 둔 검색 오류를 호출자에게 전달합니다", async () => {
  await assert.rejects(searchUsers("error", new AbortController().signal), /검색 오류/);
});

test("취소한 이전 요청은 결과를 반환하지 않습니다", async () => {
  const controller = new AbortController();
  const pending = searchUsers("a", controller.signal);
  controller.abort();
  await assert.rejects(pending, (error) => error instanceof DOMException && error.name === "AbortError");
});
