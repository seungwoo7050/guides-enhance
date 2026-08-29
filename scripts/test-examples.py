#!/usr/bin/env python3
"""Run deterministic contract checks for the user-space OS examples."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def run(binary: Path, *arguments: str, expected_status: int = 0) -> str:
    completed = subprocess.run(
        [str(binary), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if completed.returncode != expected_status:
        raise AssertionError(
            f"{binary.name} {' '.join(arguments)} returned {completed.returncode}, "
            f"expected {expected_status}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def require(output: str, pattern: str, command: str) -> None:
    if re.search(pattern, output, re.MULTILINE) is None:
        raise AssertionError(f"{command} output did not match {pattern!r}:\n{output}")


def verify(build_dir: Path) -> None:
    syscall = run(build_dir / "syscall-boundary")
    require(syscall, r"write .* 경계를 넘었습니다", "syscall-boundary")
    require(syscall, r"open이 예상대로 실패했습니다: errno=\d+", "syscall-boundary")

    split = run(build_dir / "lost-update", "split", "100")
    require(split, r"mode=split rounds=100 expected=200 actual=100$", "lost-update split")
    fetch_add = run(build_dir / "lost-update", "fetch-add", "100")
    require(fetch_add, r"mode=fetch-add rounds=100 expected=200 actual=200$", "lost-update fetch-add")
    run(build_dir / "lost-update", "invalid", expected_status=2)

    bounded = run(build_dir / "bounded-buffer", "100")
    require(bounded, r"produced=100 consumed=100 sums_match=yes$", "bounded-buffer")
    run(build_dir / "bounded-buffer", "0", expected_status=2)

    dining = run(build_dir / "dining-cycle", "100")
    require(dining, r"diners=5 rounds=100 all_completed=yes lock_order=lower-first$", "dining-cycle")
    run(build_dir / "dining-cycle", "0", expected_status=2)

    cow = run(build_dir / "cow-observer")
    require(cow, r"before fork .* value=41", "cow-observer")
    require(cow, r"child .* value=99", "cow-observer")
    require(cow, r"parent .* value=41 unchanged=yes$", "cow-observer")

    faults = run(build_dir / "page-fault-observer", "16")
    require(
        faults,
        r"page_size=[1-9]\d* touched_pages=16 touch_checksum=136 minor_fault_delta=\d+$",
        "page-fault-observer",
    )
    run(build_dir / "page-fault-observer", "0", expected_status=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, required=True)
    args = parser.parse_args()
    verify(args.build_dir)
    print("OS example verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
