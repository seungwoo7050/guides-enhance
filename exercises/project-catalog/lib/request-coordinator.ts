export type CoordinatedRequest = {
  generation: number;
  signal: AbortSignal;
};

export type RequestCoordinator = {
  begin(): CoordinatedRequest;
  isCurrent(generation: number): boolean;
  cancel(): void;
};

// [Implementation 7]
// 새 요청이 이전 요청을 중단하며, generation 비교로 늦게 끝난 결과를 버립니다.
export function createRequestCoordinator(): RequestCoordinator {
  let generation = 0;
  let controller: AbortController | null = null;

  return {
    begin() {
      controller?.abort();
      controller = new AbortController();
      generation += 1;
      return { generation, signal: controller.signal };
    },
    isCurrent(candidate) {
      return candidate === generation;
    },
    cancel() {
      controller?.abort();
      controller = null;
      generation += 1;
    }
  };
}
