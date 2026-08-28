"""수집한 프로세스 결과를 예상값과 비교합니다."""

from __future__ import annotations

from .model import Case


# [Implementation 3] Compare return code, streams, timeout, and output limits.
def compare_observation(
    case: Case,
    *,
    returncode: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
    exceeded_stream: str | None = None,
) -> tuple[str, ...]:
    failures: list[str] = []

    if timed_out:
        failures.append(f"timeout: exceeded {case.timeout:g} seconds")
        return tuple(failures)

    if exceeded_stream is not None:
        failures.append(
            f"output limit: {exceeded_stream} exceeded {case.output_limit} bytes"
        )
        return tuple(failures)

    if returncode != case.returncode:
        failures.append(f"return code: expected {case.returncode}, got {returncode}")
    if stdout != case.stdout:
        failures.append(f"stdout: expected {case.stdout!r}, got {stdout!r}")
    if stderr != case.stderr:
        failures.append(f"stderr: expected {case.stderr!r}, got {stderr!r}")
    return tuple(failures)
