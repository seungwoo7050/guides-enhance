import assert from "node:assert/strict";
import test from "node:test";
import { parsePort, sum } from "../packages/math/src/index.ts";

test("sum은 입력 배열을 바꾸지 않습니다", () => {
  const values = Object.freeze([1, 2, 3]);
  assert.equal(sum(values), 6);
  assert.deepEqual(values, [1, 2, 3]);
});

test("parsePort는 허용 범위의 양 끝값을 받습니다", () => {
  assert.equal(parsePort("1"), 1);
  assert.equal(parsePort(65535), 65535);
});

test("parsePort는 잘못된 값과 범위 밖 숫자를 거부합니다", () => {
  for (const value of [undefined, null, "", "12.5", 0, 65536, Number.NaN]) {
    assert.throws(() => parsePort(value));
  }
});
