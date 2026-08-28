import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const [html, css, js] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("../style.css", import.meta.url), "utf8"),
  readFile(new URL("../app.js", import.meta.url), "utf8")
]);

test("검색 폼의 의미와 접근성 요소를 확인합니다", () => {
  assert.match(html, /role="search"/);
  assert.match(html, /label for="query"/);
  assert.match(html, /role="status"/);
  assert.match(html, /href="#main"/);
});

test("검색 상태는 현재 URL에서 복원합니다", () => {
  assert.match(js, /new URL\(location\.href\)/);
  assert.match(js, /history\.pushState/);
  assert.match(js, /popstate/);
});

test("검색 데이터가 HTML로 실행되지 않게 합니다", () => {
  assert.doesNotMatch(js, /\.innerHTML\s*=/);
  assert.match(js, /heading\.textContent = doc\.title/);
  assert.match(js, /body\.textContent = doc\.body/);
});

test("좁은 화면과 긴 문자열에서도 화면이 넘치지 않습니다", () => {
  assert.match(css, /@media \(max-width: 32rem\)/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.match(css, /:focus-visible/);
});
