"""검증한 사례와 실행 결과, 입력·실행 예외를 정의합니다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_LIMIT = 1024 * 1024


# [Implementation 2] Store validated case input as immutable values.
@dataclass(frozen=True, slots=True)
class Case:
    name: str
    args: tuple[str, ...] = ()
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timeout: float = 2.0
    cwd: Path | None = None
    env: tuple[tuple[str, str], ...] = ()
    output_limit: int = DEFAULT_OUTPUT_LIMIT

    def environment_overrides(self) -> dict[str, str]:
        """프로세스를 시작할 때 사용할 새 환경 변수 `dict`를 반환합니다."""
        return dict(self.env)


# [Implementation 2-1] Store process observations and limit failures as immutable results.
@dataclass(frozen=True, slots=True)
class Result:
    name: str
    passed: bool
    duration_ms: int
    failures: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    exceeded_stream: str | None = None


# [Implementation 2-2] Separate specification failures from process-management failures.
class SpecificationError(ValueError):
    """사례 명세가 유효하지 않을 때 발생합니다."""


class ExecutionError(RuntimeError):
    """대상 프로세스를 시작하거나 정리할 수 없을 때 발생합니다."""
