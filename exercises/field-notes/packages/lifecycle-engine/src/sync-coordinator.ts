import type {
  BoundedWorkerPort,
  DeadlineScheduler,
  LifecycleClock,
  WorkerIdGenerator,
} from "./ports.ts";
import type {
  LifecycleSyncTrigger,
  SyncExecution,
  SyncOpportunityResult,
} from "./types.ts";

export class SystemLifecycleClock implements LifecycleClock {
  now(): number {
    return Date.now();
  }
}

export class TimerDeadlineScheduler implements DeadlineScheduler {
  readonly #clock: LifecycleClock;

  constructor(clock: LifecycleClock) {
    this.#clock = clock;
  }

  schedule(at: number, callback: () => void): () => void {
    const timer = setTimeout(callback, Math.max(0, at - this.#clock.now()));
    return () => clearTimeout(timer);
  }
}

export class SequentialWorkerIdGenerator implements WorkerIdGenerator {
  #sequence = 0;

  next(trigger: LifecycleSyncTrigger): string {
    return `${trigger}-${++this.#sequence}`;
  }
}

// [Implementation 8]
// 수동·앱 활성화·백그라운드·알림 실행에서 같은 동기화 작업자를 호출합니다.
export class LifecycleSyncCoordinator {
  readonly #worker: BoundedWorkerPort;
  readonly #clock: LifecycleClock;
  readonly #scheduler: DeadlineScheduler;
  readonly #ids: WorkerIdGenerator;
  #active: { trigger: LifecycleSyncTrigger; execution: Promise<SyncExecution> } | null = null;

  constructor(input: {
    worker: BoundedWorkerPort;
    clock: LifecycleClock;
    scheduler: DeadlineScheduler;
    ids: WorkerIdGenerator;
  }) {
    this.#worker = input.worker;
    this.#clock = input.clock;
    this.#scheduler = input.scheduler;
    this.#ids = input.ids;
  }

  async run(input: {
    trigger: LifecycleSyncTrigger;
    deadlineAt?: number;
    signal?: AbortSignal;
  }): Promise<SyncOpportunityResult> {
    if (this.#active) {
      const active = this.#active;
      return {
        kind: "coalesced",
        trigger: input.trigger,
        leaderTrigger: active.trigger,
        execution: await active.execution,
      };
    }

    if (input.signal?.aborted) {
      return { kind: "not-started", trigger: input.trigger, reason: "aborted" };
    }
    if (input.deadlineAt !== undefined && input.deadlineAt <= this.#clock.now()) {
      return { kind: "not-started", trigger: input.trigger, reason: "deadline" };
    }

    const controller = new AbortController();
    const relayAbort = () => controller.abort(input.signal?.reason);
    input.signal?.addEventListener("abort", relayAbort, { once: true });
    const cancelDeadline = input.deadlineAt === undefined
      ? () => undefined
      : this.#scheduler.schedule(input.deadlineAt, () => controller.abort(new Error("deadline")));
    const workerId = this.#ids.next(input.trigger);

    const execution = (async (): Promise<SyncExecution> => {
      try {
        const worker = await this.#worker.run({
          trigger: input.trigger,
          workerId,
          signal: controller.signal,
        });
        return { kind: "ran", trigger: input.trigger, workerId, worker };
      } finally {
        cancelDeadline();
        input.signal?.removeEventListener("abort", relayAbort);
      }
    })();
    this.#active = { trigger: input.trigger, execution };

    try {
      return await execution;
    } finally {
      if (this.#active?.execution === execution) this.#active = null;
    }
  }
}
