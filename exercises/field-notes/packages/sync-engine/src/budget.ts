import type { SyncBudget } from "./ports.ts";
import type { SyncTrigger } from "./types.ts";

export class FixedSyncBudget implements SyncBudget {
  readonly #maxCommands: number;
  readonly #leaseMs: number;
  readonly #attempts: number;
  readonly #retryMs: number;
  readonly #wallTimeMs: number;

  constructor(input: {
    maxCommands?: number;
    leaseDurationMs?: number;
    maxAttempts?: number;
    retryDelayMs?: number;
    wallTimeMs?: number;
  } = {}) {
    this.#maxCommands = input.maxCommands ?? 25;
    this.#leaseMs = input.leaseDurationMs ?? 30_000;
    this.#attempts = input.maxAttempts ?? 5;
    this.#retryMs = input.retryDelayMs ?? 5_000;
    this.#wallTimeMs = input.wallTimeMs ?? 60_000;
  }

  canStartNext(input: {
    trigger: SyncTrigger;
    claimed: number;
    startedAt: number;
    now: number;
  }): boolean {
    return input.claimed < this.#maxCommands && input.now - input.startedAt < this.#wallTimeMs;
  }

  leaseDurationMs(): number {
    return this.#leaseMs;
  }

  maxAttempts(): number {
    return this.#attempts;
  }

  retryDelayMs(attempt: number): number {
    const exponent = Math.max(0, Math.min(6, attempt - 1));
    return this.#retryMs * (2 ** exponent);
  }
}

export class ManualSyncClock {
  #value: number;

  constructor(initial = 0) {
    this.#value = initial;
  }

  now(): number {
    return this.#value;
  }

  set(value: number): void {
    this.#value = value;
  }

  advance(milliseconds: number): void {
    this.#value += milliseconds;
  }
}
