import type { RemoteRecord } from "../../core/src/contracts.ts";
import type { WireResponse } from "../../fault-server/src/types.ts";
import type { ClaimedCommand, ParsedTransportResult, RecordPayload } from "./types.ts";

function object(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function validIsoDate(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function parsePayload(value: unknown): RecordPayload | null | undefined {
  if (value === null) return null;
  const payload = object(value);
  if (!payload) return undefined;
  if (typeof payload.title !== "string" || typeof payload.notes !== "string") return undefined;
  if (!(["draft", "open", "resolved"] as unknown[]).includes(payload.status)) return undefined;
  if (!validIsoDate(payload.observedAt)) return undefined;

  let location: RecordPayload["location"];
  if (payload.location !== undefined) {
    const raw = object(payload.location);
    if (!raw
      || typeof raw.latitude !== "number"
      || typeof raw.longitude !== "number"
      || typeof raw.accuracyMeters !== "number"
      || !Number.isFinite(raw.latitude)
      || !Number.isFinite(raw.longitude)
      || !Number.isFinite(raw.accuracyMeters)
      || raw.accuracyMeters < 0
      || !validIsoDate(raw.measuredAt)) return undefined;
    location = {
      latitude: raw.latitude,
      longitude: raw.longitude,
      accuracyMeters: raw.accuracyMeters,
      measuredAt: raw.measuredAt,
    };
  }

  return {
    title: payload.title,
    notes: payload.notes,
    status: payload.status as RecordPayload["status"],
    observedAt: payload.observedAt,
    ...(location ? { location } : {}),
  };
}

function parseRemoteRecord(value: unknown): RemoteRecord | null {
  const record = object(value);
  if (!record
    || typeof record.recordId !== "string"
    || !Number.isInteger(record.version)
    || (record.version as number) < 1
    || typeof record.deleted !== "boolean") return null;
  const payload = parsePayload(record.payload);
  if (payload === undefined) return null;
  if (record.deleted && payload !== null) return null;
  if (!record.deleted && payload === null) return null;
  return {
    recordId: record.recordId,
    version: record.version as number,
    deleted: record.deleted,
    payload,
  };
}

// [Implementation 6-1]
// 처리 결과를 기록하기 전에 응답 ID·버전·필수 값을 검증합니다.
export function parseTransportResponse(
  response: WireResponse,
  claim: ClaimedCommand,
): ParsedTransportResult {
  const body = object(response.body);
  if (!body) return { kind: "invalid_response", reason: "body-not-an-object" };
  if (body.commandId !== claim.commandId) {
    return { kind: "invalid_response", reason: "command-id-mismatch" };
  }

  if (response.status === 200 && body.kind === "success") {
    const remote = parseRemoteRecord(body.record);
    if (!remote) return { kind: "invalid_response", reason: "invalid-success-record" };
    if (remote.recordId !== claim.attempted.recordId) {
      return { kind: "invalid_response", reason: "record-id-mismatch" };
    }
    if (claim.knownRemoteVersion !== null && remote.version < claim.knownRemoteVersion) {
      return { kind: "invalid_response", reason: "remote-version-regression" };
    }
    if (claim.attempted.baseVersion !== null && remote.version <= claim.attempted.baseVersion) {
      return { kind: "invalid_response", reason: "remote-version-did-not-advance" };
    }
    if (claim.attempted.operation === "delete" && !remote.deleted) {
      return { kind: "invalid_response", reason: "delete-not-applied" };
    }
    return { kind: "success", remote };
  }

  if (response.status === 409 && body.kind === "conflict") {
    if (body.recordId !== claim.attempted.recordId) {
      return { kind: "invalid_response", reason: "conflict-record-id-mismatch" };
    }
    if (body.expectedBaseVersion !== null
      && (!Number.isInteger(body.expectedBaseVersion) || (body.expectedBaseVersion as number) < 1)) {
      return { kind: "invalid_response", reason: "invalid-expected-base" };
    }
    const remote = body.current === null ? null : parseRemoteRecord(body.current);
    if (body.current !== null && !remote) {
      return { kind: "invalid_response", reason: "invalid-conflict-record" };
    }
    return { kind: "conflict", remote };
  }

  if (response.status === 401 && body.kind === "unauthorized") {
    return { kind: "blocked_auth", reason: "unauthorized" };
  }

  if (response.status === 422 && body.kind === "permanent-failure") {
    return {
      kind: "permanent",
      reason: typeof body.reason === "string" ? body.reason : "permanent-validation",
    };
  }

  if (response.status === 400 && body.kind === "validation-failure") {
    return {
      kind: "permanent",
      reason: typeof body.reason === "string" ? body.reason : "invalid-command",
    };
  }

  if (response.status === 409 && body.kind === "command-identity-reuse") {
    return { kind: "permanent", reason: "command-identity-reuse" };
  }

  return { kind: "invalid_response", reason: `unsupported-response:${response.status}` };
}
