#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


def run(program: str, line: str, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [program, line],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def run_with_closed_standard_fds(
    program: str,
    line: str,
    *,
    close_stdin: bool,
    close_stdout: bool,
    timeout: float = 8.0,
) -> subprocess.CompletedProcess[str]:
    def close_selected_fds() -> None:
        if close_stdin:
            os.close(0)
        if close_stdout:
            os.close(1)

    return subprocess.run(
        [program, line],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
        preexec_fn=close_selected_fds,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_syntax_error(runner: str, line: str) -> None:
    result = run(runner, line)
    require(result.returncode == 2, f"syntax status failed {line!r}: {result.returncode}")
    require(result.stdout == "", f"syntax error produced stdout: {line!r}")
    require("Syntax error:" in result.stderr, f"missing syntax diagnostic: {line!r}")


def main() -> int:
    if len(sys.argv) != 8:
        print("runner and six helper paths required", file=sys.stderr)
        return 2
    runner, print_args, emit, expect, exit_with, terminate_with, mark_file = sys.argv[1:]

    result = run(runner, f"{print_args} one 'two three' \"\" ab\"cd\" escaped\\ space")
    require(result.returncode == 0, f"argument execution failed: {result.stderr}")
    require(
        result.stdout
        == "argc=5\narg[0]=<one>\narg[1]=<two three>\narg[2]=<>\n"
        "arg[3]=<abcd>\narg[4]=<escaped space>\n",
        f"quote result mismatch: {result.stdout!r}",
    )
    require(result.stderr == "", f"unexpected stderr: {result.stderr!r}")

    result = run(runner, f"{print_args} '' \"a\\\"b\"")
    require(result.returncode == 0, f"empty argument or escape failed: {result.stderr!r}")
    require(result.stdout == "argc=2\narg[0]=<>\narg[1]=<a\"b>\n", result.stdout)

    result = run(runner, f"{print_args} 'a|b' a\\|b '<' \\; \"x&y\" \\>")
    require(result.returncode == 0, f"quoted control character failed: {result.stderr!r}")
    require(
        result.stdout
        == "argc=6\narg[0]=<a|b>\narg[1]=<a|b>\narg[2]=<<>\n"
        "arg[3]=<;>\narg[4]=<x&y>\narg[5]=<>>\n",
        f"control-character literal mismatch: {result.stdout!r}",
    )

    result = run(runner, f"\t{print_args}\talpha   beta\t")
    require(result.returncode == 0, f"whitespace split failed: {result.stderr!r}")
    require(result.stdout == "argc=2\narg[0]=<alpha>\narg[1]=<beta>\n", result.stdout)

    result = run(runner, f"{emit} 4194304 | {expect} 4194304", timeout=20.0)
    require(
        result.returncode == 0,
        f"large pipeline failed: {result.returncode} {result.stderr}",
    )

    for close_stdin, close_stdout in ((True, False), (False, True), (True, True)):
        result = run_with_closed_standard_fds(
            runner,
            f"{emit} 128 | {expect} 128",
            close_stdin=close_stdin,
            close_stdout=close_stdout,
        )
        require(
            result.returncode == 0,
            "standard FD reuse failed: "
            f"stdin={close_stdin} stdout={close_stdout} "
            f"status={result.returncode} stderr={result.stderr!r}",
        )

    result = run(runner, f"{exit_with} 37")
    require(result.returncode == 37, f"exit status propagation failed: {result.returncode}")

    result = run(runner, f"{emit} 0 | {exit_with} 29")
    require(result.returncode == 29, f"last pipeline status failed: {result.returncode}")

    result = run(runner, f"{exit_with} 41 | {expect} 0")
    require(result.returncode == 0, f"left failure replaced last status: {result.returncode}")

    result = run(runner, f"{terminate_with} {signal.SIGTERM}")
    require(
        result.returncode == 128 + signal.SIGTERM,
        f"signal status failed: {result.returncode}",
    )

    result = run(runner, f"{emit} 0 | {terminate_with} {signal.SIGTERM}")
    require(
        result.returncode == 128 + signal.SIGTERM,
        f"pipeline signal status failed: {result.returncode}",
    )

    result = run(runner, "./definitely-not-a-command")
    require(result.returncode == 127, f"missing command status failed: {result.returncode}")
    require("command execution failed" in result.stderr, "missing exec diagnostic")

    with tempfile.TemporaryDirectory(prefix="command-runner-") as temp:
        temp_path = Path(temp)
        non_executable = temp_path / "not-executable"
        non_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        non_executable.chmod(0o600)
        result = run(runner, str(non_executable))
        require(result.returncode == 126, f"non-executable status failed: {result.returncode}")
        require("command execution failed" in result.stderr, "missing EACCES diagnostic")

        # 문법을 모두 확인하기 전에 fork하는 구현은 표시 파일을 남깁니다.
        marker = temp_path / "marker"
        assert_syntax_error(runner, f"{mark_file} {marker} |")
        require(not marker.exists(), "trailing-pipe syntax error caused a child side effect")
        assert_syntax_error(runner, f"{mark_file} {marker} > ignored")
        require(not marker.exists(), "unsupported operator caused a child side effect")

    bad_lines = [
        "",
        "   \t",
        "| x",
        "x |",
        "x || y",
        "x | y | z",
        "'unterminated",
        '"unterminated',
        "x \\",
        "x < input",
        "x > output",
        "x; y",
        "x & y",
    ]
    for line in bad_lines:
        assert_syntax_error(runner, line)

    result = subprocess.run([runner], text=True, capture_output=True, check=False)
    require(result.returncode == 2, f"usage status failed: {result.returncode}")
    require(result.stdout == "", f"usage error produced stdout: {result.stdout!r}")
    require("Usage:" in result.stderr, f"missing usage diagnostic: {result.stderr!r}")

    print("command-runner tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
