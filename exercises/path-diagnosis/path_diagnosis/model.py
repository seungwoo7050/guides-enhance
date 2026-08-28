"""단계별 관찰 기록의 입력 형식과 상태 순서를 검증합니다."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

STAGE_ORDER = ("dns", "route", "neighbor", "path", "transport", "tls", "http")
VALID_STATUSES = frozenset({"ok", "failed", "not-run"})
VALID_TRANSPORTS = frozenset({"tcp", "udp", "quic"})


class TraceFormatError(ValueError):
    """입력 추적 기록이 허용된 형식을 따르지 않을 때 발생합니다."""


# [Implementation 1] Request field validation
# 요청 이름, 포트, 전송 프로토콜과 애플리케이션 값을 검증합니다.
@dataclass(frozen=True)
class RequestContext:
    """진단할 요청을 식별하는 최소 필드를 보관합니다."""

    name: str
    port: int
    transport: str
    application: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RequestContext":
        if not isinstance(value, Mapping):
            raise TraceFormatError("request must be an object")
        name = _required_text(value, "name", "request")
        application = _required_text(value, "application", "request")
        transport = _required_text(value, "transport", "request").lower()
        if transport not in VALID_TRANSPORTS:
            supported = ", ".join(sorted(VALID_TRANSPORTS))
            raise TraceFormatError(
                f"unsupported request.transport: {transport}; supported: {supported}"
            )
        port = value.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise TraceFormatError("request.port must be an integer from 1 through 65535")
        return cls(name=name, port=port, transport=transport, application=application)

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "port": self.port,
            "transport": self.transport,
            "application": self.application,
        }


# [Implementation 1-1] Stage record validation
# 각 단계의 이름, 상태, 관찰 문장과 ``facts`` 형식을 함께 확인합니다.
@dataclass(frozen=True)
class StageEvidence:
    """한 단계의 상태, 관찰 문장과 ``facts`` 값을 보관합니다."""

    stage: str
    status: str
    observation: str
    facts: Mapping[str, Any]

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        expected_stage: str,
    ) -> "StageEvidence":
        if not isinstance(value, Mapping):
            raise TraceFormatError(f"{expected_stage} stage must be an object")
        stage = _required_text(value, "stage", expected_stage)
        if stage != expected_stage:
            raise TraceFormatError(
                f"stage order is invalid: expected {expected_stage}, found {stage}"
            )
        status = _required_text(value, "status", stage)
        if status not in VALID_STATUSES:
            raise TraceFormatError(f"invalid {stage}.status: {status}")
        observation = _required_text(value, "observation", stage)
        facts = value.get("facts")
        if not isinstance(facts, Mapping):
            raise TraceFormatError(f"{stage}.facts must be an object")
        return cls(
            stage=stage,
            status=status,
            observation=observation,
            facts=dict(facts),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "status": self.status,
            "observation": self.observation,
            "facts": dict(self.facts),
        }


# [Implementation 1-2] Trace progression validation
# 첫 실패 뒤의 단계는 모두 ``not-run``이어야 하며 두 번째 실패를 허용하지 않습니다.
@dataclass(frozen=True)
class Trace:
    """요청과 일곱 단계의 검증된 관찰 기록을 보관합니다."""

    request: RequestContext
    stages: tuple[StageEvidence, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Trace":
        if not isinstance(value, Mapping):
            raise TraceFormatError("the trace root must be an object")
        request = RequestContext.from_mapping(value.get("request"))
        raw_stages = value.get("stages")
        if not isinstance(raw_stages, list):
            raise TraceFormatError("stages must be an array")
        if len(raw_stages) != len(STAGE_ORDER):
            raise TraceFormatError(
                f"stages must contain exactly {len(STAGE_ORDER)} entries; "
                f"received {len(raw_stages)}"
            )
        stages = tuple(
            StageEvidence.from_mapping(raw_stage, expected_stage)
            for raw_stage, expected_stage in zip(
                raw_stages,
                STAGE_ORDER,
                strict=True,
            )
        )
        _validate_progression(stages)
        return cls(request=request, stages=stages)

    def to_mapping(self) -> dict[str, object]:
        return {
            "request": self.request.to_mapping(),
            "stages": [stage.to_mapping() for stage in self.stages],
        }

    @property
    def first_failure(self) -> StageEvidence | None:
        return next(
            (stage for stage in self.stages if stage.status == "failed"),
            None,
        )

    @property
    def last_success(self) -> StageEvidence | None:
        failure = self.first_failure
        if failure is None:
            return self.stages[-1]
        failure_index = STAGE_ORDER.index(failure.stage)
        if failure_index == 0:
            return None
        return self.stages[failure_index - 1]


# [Implementation 1-3] Trace file loading
# 파일 읽기, JSON 파싱과 값 검증 오류를 ``TraceFormatError``로 통일합니다.
def load_trace(path: str | Path) -> Trace:
    """JSON 추적 기록을 읽고 입력 오류를 ``TraceFormatError``로 변환합니다."""

    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise TraceFormatError(f"cannot read trace file {source}: {error}") from error
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise TraceFormatError(
            f"invalid JSON syntax at {source}:{error.lineno}:{error.colno}"
        ) from error
    try:
        return Trace.from_mapping(value)
    except TraceFormatError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise TraceFormatError(f"invalid trace structure: {error}") from error


def _required_text(value: Mapping[str, Any], key: str, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise TraceFormatError(f"{context}.{key} must be a non-empty string")
    return item.strip()


def _validate_progression(stages: tuple[StageEvidence, ...]) -> None:
    failure_seen = False
    for stage in stages:
        if not failure_seen:
            if stage.status == "ok":
                continue
            if stage.status == "failed":
                failure_seen = True
                continue
            raise TraceFormatError(
                f"{stage.stage} cannot be not-run without a preceding failure"
            )
        if stage.status != "not-run":
            raise TraceFormatError(
                f"{stage.stage} must be not-run after the first failure"
            )
