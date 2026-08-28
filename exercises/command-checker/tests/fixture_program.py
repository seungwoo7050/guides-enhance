#!/usr/bin/env python3
"""프로세스, 스트림, 완료 순서를 반복해서 재현하는 테스트 대상입니다."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("mode is required", file=sys.stderr)
        return 2

    mode = sys.argv[1]
    args = sys.argv[2:]

    if mode == "echo":
        sys.stdout.write(sys.stdin.read())
        return 0
    if mode == "args":
        sys.stdout.write(json.dumps(args, ensure_ascii=False) + "\n")
        return 0
    if mode == "environment":
        sys.stdout.write(os.environ.get("CHECKER_VALUE", "") + "\n")
        return 0
    if mode == "cwd":
        sys.stdout.write(str(Path.cwd()) + "\n")
        return 0
    if mode == "channels":
        sys.stdout.write(os.environ.get("OUT", ""))
        sys.stderr.write(os.environ.get("ERR", ""))
        return int(os.environ.get("CODE", "0"))
    if mode == "sleep":
        time.sleep(float(args[0]))
        return 0
    if mode == "flood":
        stream_name = args[0]
        amount = int(args[1])
        descriptor = sys.stdout.fileno() if stream_name == "stdout" else sys.stderr.fileno()
        block = b"x" * 65536
        remaining = amount
        while remaining > 0:
            chunk = block[: min(len(block), remaining)]
            os.write(descriptor, chunk)
            remaining -= len(chunk)
        return 0
    if mode in {"spawn-child", "orphan-pipe"}:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
        )
        pid_file = os.environ.get("CHILD_PID_FILE")
        if pid_file:
            Path(pid_file).write_text(f"{child.pid}\n", encoding="utf-8")
        if mode == "spawn-child":
            time.sleep(60)
        return 0
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
