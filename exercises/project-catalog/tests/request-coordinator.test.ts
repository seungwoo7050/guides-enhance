import { describe, expect, it } from "vitest";
import { createRequestCoordinator } from "../lib/request-coordinator";

// [Implementation 14-4]
// 새 요청과 취소가 이전 signal과 generation을 무효화하는지 확인합니다.
describe("request coordinator", () => {
  it("aborts the previous signal and advances the current generation", () => {
    const coordinator = createRequestCoordinator();
    const first = coordinator.begin();
    const second = coordinator.begin();

    expect(first.signal.aborted).toBe(true);
    expect(second.signal.aborted).toBe(false);
    expect(coordinator.isCurrent(first.generation)).toBe(false);
    expect(coordinator.isCurrent(second.generation)).toBe(true);
  });

  it("invalidates a result that arrives after cancellation", () => {
    const coordinator = createRequestCoordinator();
    const request = coordinator.begin();
    coordinator.cancel();

    expect(request.signal.aborted).toBe(true);
    expect(coordinator.isCurrent(request.generation)).toBe(false);
  });
});
