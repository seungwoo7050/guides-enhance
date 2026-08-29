import type { SyncBudget, SyncClock, SyncRepository, SyncTransport } from "./ports.ts";
import { parseTransportResponse } from "./response-parser.ts";
import type {
  CheckpointOutcome,
  ClaimedCommand,
  ParsedTransportResult,
  SyncTrigger,
  WorkerRunResult,
} from "./types.ts";

function reason(error: unknown): string {
  return error instanceof Error ? `${error.name}:${error.message}` : String(error);
}

// [Implementation 6-2]
// 제한 시간 안에 명령을 가져오고 결과를 모르는 요청은 같은 명령으로 재시도합니다.
export class BoundedSyncWorker {
  readonly #repository: SyncRepository;
  readonly #transport: SyncTransport;
  readonly #clock: SyncClock;
  readonly #budget: SyncBudget;

  constructor(input: {
    repository: SyncRepository;
    transport: SyncTransport;
    clock: SyncClock;
    budget: SyncBudget;
  }) {
    this.#repository = input.repository;
    this.#transport = input.transport;
    this.#clock = input.clock;
    this.#budget = input.budget;
  }

  async run(input: {
    trigger: SyncTrigger;
    workerId: string;
    signal?: AbortSignal;
  }): Promise<WorkerRunResult> {
    const startedAt = this.#clock.now();
    const checkpoints: WorkerRunResult["checkpoints"] = [];
    let claimed = 0;

    while (this.#budget.canStartNext({
      trigger: input.trigger,
      claimed,
      startedAt,
      now: this.#clock.now(),
    })) {
      if (input.signal?.aborted) {
        return { trigger: input.trigger, workerId: input.workerId, claimed, checkpoints, stopped: "aborted" };
      }

      const claim = await this.#repository.claimNext({
        workerId: input.workerId,
        now: this.#clock.now(),
        leaseDurationMs: this.#budget.leaseDurationMs(),
      });
      if (!claim) {
        return { trigger: input.trigger, workerId: input.workerId, claimed, checkpoints, stopped: "idle" };
      }
      claimed += 1;

      const controller = new AbortController();
      const relayAbort = () => controller.abort(input.signal?.reason);
      input.signal?.addEventListener("abort", relayAbort, { once: true });

      let parsed: ParsedTransportResult;
      try {
        const response = await this.#transport.send(claim.attempted, controller.signal);
        parsed = parseTransportResponse(response, claim);
      } catch (error) {
        // 전송 예외만으로 서버가 처리하지 않았다고 단정할 수 없으므로 처리 여부를 모르는 상태로 남깁니다.
        parsed = { kind: "invalid_response", reason: `transport-unknown:${reason(error)}` };
      } finally {
        input.signal?.removeEventListener("abort", relayAbort);
      }

      const outcome = this.#outcome(claim, parsed);
      try {
        const checkpoint = await this.#repository.checkpoint(claim, outcome);
        checkpoints.push(checkpoint);
      } catch (error) {
        // 처리 결과 저장이 실패하면 다른 결과를 추측해 기록하지 않고 lease 만료 뒤 다시 처리합니다.
        return {
          trigger: input.trigger,
          workerId: input.workerId,
          claimed,
          checkpoints,
          stopped: "checkpoint-failed",
          checkpointError: reason(error),
        };
      }

      if (outcome.kind === "blocked_auth") {
        return { trigger: input.trigger, workerId: input.workerId, claimed, checkpoints, stopped: "auth-blocked" };
      }
      if (input.signal?.aborted) {
        return { trigger: input.trigger, workerId: input.workerId, claimed, checkpoints, stopped: "aborted" };
      }
    }

    return { trigger: input.trigger, workerId: input.workerId, claimed, checkpoints, stopped: "budget" };
  }

  #outcome(claim: ClaimedCommand, parsed: ParsedTransportResult): CheckpointOutcome {
    switch (parsed.kind) {
      case "success":
        return { kind: "success", remote: parsed.remote, completedAt: this.#clock.now() };
      case "conflict":
        return { kind: "conflict", remote: parsed.remote, createdAt: this.#clock.now() };
      case "blocked_auth":
        return { kind: "blocked_auth", reason: parsed.reason };
      case "permanent":
        return { kind: "permanent", reason: parsed.reason };
      case "invalid_response":
        if (claim.attempt >= this.#budget.maxAttempts()) {
          return { kind: "permanent", reason: `attempt-exhausted:${parsed.reason}` };
        }
        return {
          kind: "retry_wait",
          reason: parsed.reason,
          nextAttemptAt: this.#clock.now() + this.#budget.retryDelayMs(claim.attempt),
        };
    }
  }
}
