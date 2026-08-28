#!/usr/bin/env python3
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import time


def read_line(process: subprocess.Popen[str], timeout: float) -> str:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        events = selector.select(timeout)
        if not events:
            raise AssertionError(f"no output within {timeout} seconds")
        line = process.stdout.readline()
        if line == "":
            raise AssertionError(f"unexpected EOF: status={process.poll()}")
        return line.rstrip("\n")
    finally:
        selector.close()


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def run_once(program: str, include_burst: bool) -> None:
    process = subprocess.Popen(
        [program],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    try:
        ready = read_line(process, 4.0)
        if not ready.startswith("ready pid="):
            raise AssertionError(f"invalid ready line: {ready!r}")
        announced = int(ready[len("ready pid="):])
        if announced != process.pid:
            raise AssertionError(
                f"PID mismatch: announced={announced}, actual={process.pid}"
            )

        for _ in range(3):
            os.kill(process.pid, signal.SIGUSR1)
            line = read_line(process, 4.0)
            if line != "event=SIGUSR1":
                raise AssertionError(f"unexpected SIGUSR1 output: {line!r}")

        if include_burst:
            for _ in range(64):
                os.kill(process.pid, signal.SIGUSR1)

            # POSIX 표준 시그널은 여러 번 발생해도 하나로 합쳐질 수 있습니다.
            # 정확한 횟수 대신 SIGUSR1을 한 번 이상 확인한 뒤 SIGTERM을 보냅니다.
            usr1_count = 0
            deadline = time.monotonic() + 5.0
            while usr1_count == 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("burst SIGUSR1 was not observed")
                line = read_line(process, remaining)
                if line != "event=SIGUSR1":
                    raise AssertionError(f"unknown event output: {line!r}")
                usr1_count += 1

            os.kill(process.pid, signal.SIGTERM)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("SIGTERM was not handled after burst")
                line = read_line(process, remaining)
                if line == "event=SIGUSR1":
                    usr1_count += 1
                    continue
                if line == "event=SIGTERM":
                    break
                raise AssertionError(f"unknown event output: {line!r}")
            if not 1 <= usr1_count <= 64:
                raise AssertionError(
                    f"standard-signal coalescing range violated: {usr1_count}"
                )
        else:
            os.kill(process.pid, signal.SIGTERM)
            line = read_line(process, 4.0)
            if line != "event=SIGTERM":
                raise AssertionError(f"unexpected SIGTERM output: {line!r}")

        status = process.wait(timeout=4.0)
        if status != 0:
            raise AssertionError(f"unexpected exit status: {status}")
        assert process.stdout is not None
        trailing = process.stdout.read()
        if trailing:
            raise AssertionError(f"trailing stdout after termination: {trailing!r}")
        assert process.stderr is not None
        error = process.stderr.read()
        if error:
            raise AssertionError(f"unexpected stderr: {error!r}")
    finally:
        terminate(process)


def main() -> int:
    if len(sys.argv) != 2:
        print("program path required", file=sys.stderr)
        return 2
    run_once(sys.argv[1], include_burst=False)
    run_once(sys.argv[1], include_burst=True)
    print("signal-loop tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
