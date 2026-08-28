"""대상 프로세스의 세 표준 스트림을 수집하고 실행 시간을 제한합니다."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from typing import Any, Sequence

from .comparison import compare_observation
from .model import Case, ExecutionError, Result

_TERMINATION_GRACE_SECONDS = 0.2
_IO_CHUNK = 65536


def _process_group_exists(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# [Implementation 7] Terminate the process group and reap its parent.
def _terminate_group(process: subprocess.Popen[Any]) -> None:
    """프로세스 그룹을 종료하고 직접 시작한 부모 프로세스를 회수합니다."""
    group_id = process.pid
    try:
        os.killpg(group_id, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError as error:
        raise ExecutionError(
            f"permission denied while terminating process group: {error}"
        ) from error

    deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
    while _process_group_exists(group_id) and time.monotonic() < deadline:
        time.sleep(0.01)

    if _process_group_exists(group_id):
        try:
            os.killpg(group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            # macOS는 SIGTERM 뒤 신호를 받을 수 없는 좀비 프로세스만 남아도
            # EPERM을 반환할 수 있습니다. 부모 프로세스가 실행 중일 때만
            # 실제 권한 오류로 처리합니다.
            if process.poll() is None:
                raise ExecutionError(
                    f"permission denied while force-killing process group: {error}"
                ) from error

    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired as error:
        raise ExecutionError("failed to reap the target parent process") from error


def _close_stream(selector: selectors.BaseSelector, stream: Any) -> None:
    try:
        selector.unregister(stream)
    except (KeyError, ValueError):
        pass
    try:
        stream.close()
    except OSError:
        pass


# [Implementation 7-1] Collect three non-blocking pipes within time and byte limits.
def _collect_process(
    process: subprocess.Popen[bytes],
    input_bytes: bytes,
    *,
    timeout: float,
    output_limit: int,
) -> tuple[bytes, bytes, bool, str | None]:
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    input_offset = 0
    timed_out = False
    exceeded: str | None = None
    deadline = time.monotonic() + timeout

    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    for stream in (process.stdin, process.stdout, process.stderr):
        os.set_blocking(stream.fileno(), False)

    selector.register(process.stdout, selectors.EVENT_READ, ("stdout", stdout))
    selector.register(process.stderr, selectors.EVENT_READ, ("stderr", stderr))
    if input_bytes:
        selector.register(process.stdin, selectors.EVENT_WRITE, ("stdin", None))
    else:
        process.stdin.close()

    try:
        while selector.get_map() or process.poll() is None:
            if process.poll() is not None and not process.stdin.closed:
                _close_stream(selector, process.stdin)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break

            events = selector.select(min(0.05, remaining))
            for key, _ in events:
                label, destination = key.data

                if label == "stdin":
                    try:
                        written = os.write(
                            key.fd,
                            input_bytes[input_offset : input_offset + _IO_CHUNK],
                        )
                    except (BrokenPipeError, OSError):
                        _close_stream(selector, process.stdin)
                        continue
                    input_offset += written
                    if input_offset >= len(input_bytes):
                        _close_stream(selector, process.stdin)
                    continue

                try:
                    chunk = os.read(key.fd, _IO_CHUNK)
                except BlockingIOError:
                    continue
                except OSError:
                    chunk = b""

                if not chunk:
                    _close_stream(selector, key.fileobj)
                    continue

                remaining_capacity = output_limit - len(destination)
                if remaining_capacity > 0:
                    destination.extend(chunk[:remaining_capacity])
                if len(chunk) > remaining_capacity:
                    exceeded = label
                    break

            if exceeded is not None:
                break
    finally:
        selector.close()

    if timed_out or exceeded is not None:
        _terminate_group(process)
    else:
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            _terminate_group(process)
            timed_out = True

    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass

    return bytes(stdout), bytes(stderr), timed_out, exceeded


# [Implementation 5-1] Start one case and convert its observations into Result.
def run_case(case: Case, command: Sequence[str]) -> Result:
    if not command:
        raise ExecutionError("command must not be empty")

    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(case.environment_overrides())

    try:
        process = subprocess.Popen(
            [*command, *case.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=case.cwd,
            env=environment,
            start_new_session=True,
        )
    except OSError as error:
        raise ExecutionError(f"cannot start command: {error}") from error

    # [Implementation 7-2] Clean up the process group if stream collection fails.
    try:
        stdout_bytes, stderr_bytes, timed_out, exceeded = _collect_process(
            process,
            case.stdin.encode("utf-8"),
            timeout=case.timeout,
            output_limit=case.output_limit,
        )
    except BaseException:
        if process.poll() is None or _process_group_exists(process.pid):
            try:
                _terminate_group(process)
            except ExecutionError:
                pass
        raise

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    failures = compare_observation(
        case,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        exceeded_stream=exceeded,
    )
    elapsed = max(0, round((time.monotonic() - started) * 1000))

    return Result(
        name=case.name,
        passed=not failures,
        duration_ms=elapsed,
        failures=failures,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        exceeded_stream=exceeded,
    )
