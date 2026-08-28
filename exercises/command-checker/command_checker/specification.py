"""JSON을 읽고 검증한 Case 값으로 변환합니다."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .model import Case, DEFAULT_OUTPUT_LIMIT, SpecificationError

_ALLOWED_FIELDS = {
    "name",
    "args",
    "stdin",
    "stdout",
    "stderr",
    "returncode",
    "timeout",
    "cwd",
    "env",
    "output_limit",
}


# [Implementation 4] Validate JSON scalar and collection values.
def _string(value: Any, field: str, index: int) -> str:
    if not isinstance(value, str):
        raise SpecificationError(f"cases[{index}].{field} must be a string")
    return value


def _strings(value: Any, field: str, index: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SpecificationError(f"cases[{index}].{field} must be an array of strings")
    if any("\0" in item for item in value):
        raise SpecificationError(f"cases[{index}].{field} must not contain NUL characters")
    return tuple(value)


def _environment(value: Any, index: int) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise SpecificationError(
            f"cases[{index}].env must be an object with string keys and values"
        )
    for key, item in value.items():
        if "\0" in key or "=" in key or "\0" in item:
            raise SpecificationError(
                f"cases[{index}].env contains an invalid operating-system environment entry"
            )
    return tuple(sorted(value.items()))


# [Implementation 4-1] Validate case fields and construct an immutable Case.
def _case(raw: Any, index: int, base: Path) -> Case:
    if not isinstance(raw, dict):
        raise SpecificationError(f"cases[{index}] must be an object")

    unknown = sorted(set(raw) - _ALLOWED_FIELDS)
    if unknown:
        raise SpecificationError(
            f"cases[{index}] contains unknown fields: {', '.join(unknown)}"
        )

    name = _string(raw.get("name"), "name", index)
    if not name.strip():
        raise SpecificationError(f"cases[{index}].name must not be empty")

    returncode = raw.get("returncode", 0)
    if isinstance(returncode, bool) or not isinstance(returncode, int):
        raise SpecificationError(f"cases[{index}].returncode must be an integer")

    timeout = raw.get("timeout", 2.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise SpecificationError(f"cases[{index}].timeout must be a number")
    timeout = float(timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise SpecificationError(f"cases[{index}].timeout must be a finite positive number")

    output_limit = raw.get("output_limit", DEFAULT_OUTPUT_LIMIT)
    if isinstance(output_limit, bool) or not isinstance(output_limit, int):
        raise SpecificationError(f"cases[{index}].output_limit must be an integer")
    if output_limit <= 0:
        raise SpecificationError(f"cases[{index}].output_limit must be positive")

    cwd_value = raw.get("cwd")
    cwd: Path | None = None
    if cwd_value is not None:
        cwd_text = _string(cwd_value, "cwd", index)
        if "\0" in cwd_text:
            raise SpecificationError(f"cases[{index}].cwd must not contain NUL characters")
        cwd_path = Path(cwd_text)
        if not cwd_text or cwd_path.is_absolute():
            raise SpecificationError(f"cases[{index}].cwd must be a non-empty relative path")
        cwd = (base / cwd_path).resolve()
        if not cwd.is_dir():
            raise SpecificationError(f"cases[{index}].cwd directory does not exist: {cwd}")

    return Case(
        name=name,
        args=_strings(raw.get("args", []), "args", index),
        stdin=_string(raw.get("stdin", ""), "stdin", index),
        stdout=_string(raw.get("stdout", ""), "stdout", index),
        stderr=_string(raw.get("stderr", ""), "stderr", index),
        returncode=returncode,
        timeout=timeout,
        cwd=cwd,
        env=_environment(raw.get("env", {}), index),
        output_limit=output_limit,
    )


# [Implementation 4-2] Load the case file and reject duplicate names.
def load_cases(path: Path) -> tuple[Case, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SpecificationError(f"cannot read case specification: {error}") from error
    except json.JSONDecodeError as error:
        raise SpecificationError(
            f"invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})"
        ) from error

    if not isinstance(raw, list):
        raise SpecificationError("the top-level specification value must be an array")
    if not raw:
        raise SpecificationError("at least one case is required")

    names: set[str] = set()
    cases: list[Case] = []
    for index, item in enumerate(raw):
        case = _case(item, index, path.parent.resolve())
        if case.name in names:
            raise SpecificationError(f"duplicate case name: {case.name}")
        names.add(case.name)
        cases.append(case)
    return tuple(cases)
