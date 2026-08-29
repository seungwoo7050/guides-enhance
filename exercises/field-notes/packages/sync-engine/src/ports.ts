import type { WireResponse } from "../../fault-server/src/types.ts";
import type {
  CheckpointOutcome,
  CheckpointResult,
  ClaimedCommand,
  ConflictResolution,
  ConflictResolutionResult,
  RecordCommand,
  RepositorySnapshot,
  SyncTrigger,
} from "./types.ts";

export interface SyncRepository {
  claimNext(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ClaimedCommand | null>;
  checkpoint(claim: ClaimedCommand, outcome: CheckpointOutcome): Promise<CheckpointResult>;
  resumeBlockedAuth(now: number): Promise<number>;
  resolveConflict(
    conflictId: string,
    resolution: ConflictResolution,
  ): Promise<ConflictResolutionResult>;
  snapshot(): Promise<RepositorySnapshot>;
}

export interface SyncTransport {
  send(command: RecordCommand, signal: AbortSignal): Promise<WireResponse>;
}

export interface SyncClock {
  now(): number;
}

export interface SyncBudget {
  canStartNext(input: { trigger: SyncTrigger; claimed: number; startedAt: number; now: number }): boolean;
  leaseDurationMs(): number;
  maxAttempts(): number;
  retryDelayMs(attempt: number): number;
}
