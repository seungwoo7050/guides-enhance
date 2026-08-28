"""`Result` 목록으로 JSON/JUnit을 만들고 완성한 파일로 교체합니다."""

from __future__ import annotations

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .model import Result


# [Implementation 8] Write a complete temporary file before replacing the report.
def atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


# [Implementation 8-1] Render deterministic JSON from the final Result sequence.
def render_json(results: Sequence[Result]) -> str:
    payload = {
        "passed": sum(result.passed for result in results),
        "failed": sum(not result.passed for result in results),
        "results": [asdict(result) for result in results],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_json_report(path: Path, results: Sequence[Result]) -> None:
    atomic_write_text(path, render_json(results))


# [Implementation 8-2] Sanitize XML text and render JUnit from the same results.
def xml_text(value: str) -> str:
    return "".join(
        character
        if (
            character in "\t\n\r"
            or 0x20 <= ord(character) <= 0xD7FF
            or 0xE000 <= ord(character) <= 0xFFFD
            or 0x10000 <= ord(character) <= 0x10FFFF
        )
        else "\uFFFD"
        for character in value
    )


def render_junit(results: Sequence[Result]) -> str:
    suite = ET.Element(
        "testsuite",
        {
            "name": "command-checker",
            "tests": str(len(results)),
            "failures": str(sum(not result.passed for result in results)),
            "time": f"{sum(result.duration_ms for result in results) / 1000:.3f}",
        },
    )
    for result in results:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "name": xml_text(result.name),
                "time": f"{result.duration_ms / 1000:.3f}",
            },
        )
        if not result.passed:
            failure = ET.SubElement(
                case,
                "failure",
                {"message": xml_text(result.failures[0])},
            )
            failure.text = xml_text("\n".join(result.failures))
        ET.SubElement(case, "system-out").text = xml_text(result.stdout)
        ET.SubElement(case, "system-err").text = xml_text(result.stderr)
    return ET.tostring(suite, encoding="unicode") + "\n"


def write_junit_report(path: Path, results: Sequence[Result]) -> None:
    atomic_write_text(path, render_junit(results))
