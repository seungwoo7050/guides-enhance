import type { SyncOpportunityResult } from "./types.ts";

export type BackgroundSyncObservation = {
  kind: "durable" | "failed" | "disabled";
  claimed: number;
  checkpoints: number;
};

/**
 * 가져온 명령마다 처리 결과를 저장한 뒤에만 백그라운드 작업을 성공으로 봅니다.
 * 작업자 시작이나 네트워크 입출력 완료만으로는 성공을 반환하지 않습니다.
 */
export function observeBackgroundSync(
  result: SyncOpportunityResult,
): BackgroundSyncObservation {
  const execution = result.kind === "coalesced" ? result.execution : result;
  if (execution.kind !== "ran") {
    return { kind: "failed", claimed: 0, checkpoints: 0 };
  }
  const { worker } = execution;
  const durable = worker.stopped !== "aborted"
    && worker.stopped !== "checkpoint-failed"
    && worker.checkpoints.length === worker.claimed;
  return {
    kind: durable ? "durable" : "failed",
    claimed: worker.claimed,
    checkpoints: worker.checkpoints.length,
  };
}

export function backgroundInvocationSucceeded(
  result: BackgroundSyncObservation,
): boolean {
  return result.kind !== "failed";
}
