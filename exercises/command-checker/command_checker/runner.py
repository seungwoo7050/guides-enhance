"""실행 파일을 선택하고 사례 실행과 결과 출력을 처리합니다."""

from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Sequence, TextIO

from .model import Case, ExecutionError, Result, SpecificationError
from .process import run_case


# [Implementation 5] Resolve the target executable once before running cases.
def validate_executable(command: str) -> str:
    contains_separator = os.sep in command or (os.altsep is not None and os.altsep in command)
    if contains_separator:
        path = Path(command).resolve()
    else:
        selected = shutil.which(command)
        if selected is None:
            raise SpecificationError(f"command not found on PATH: {command}")
        path = Path(selected).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SpecificationError(f"command is not executable: {command}")
    return str(path)


# [Implementation 6] Run cases sequentially and preserve input order.
def run_cases(
    cases: Sequence[Case],
    command: Sequence[str],
    jobs: int,
) -> tuple[Result, ...]:
    if jobs < 1:
        raise SpecificationError("jobs must be at least 1")
    if jobs == 1:
        return tuple(run_case(case, command) for case in cases)

    # [Implementation 9] Run cases with bounded workers while preserving input order.
    try:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            return tuple(executor.map(lambda case: run_case(case, command), cases))
    except OSError as error:
        raise ExecutionError(f"cannot create execution workers: {error}") from error


# [Implementation 6-1] Send passing and failing results to the appropriate streams.
def print_results(
    results: Sequence[Result],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    for result in results:
        destination = stdout if result.passed else stderr
        print(("PASS " if result.passed else "FAIL ") + result.name, file=destination)
        for failure in result.failures:
            print(f"  - {failure}", file=destination)


# [Implementation 6-2] Return success only when every case matches.
def exit_status(results: Sequence[Result]) -> int:
    return 0 if all(result.passed for result in results) else 1
