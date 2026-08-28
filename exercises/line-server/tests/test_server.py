#!/usr/bin/env python3
import argparse
import os
import select
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise AssertionError("server did not terminate after SIGTERM")
    if process.returncode != 0:
        raise RuntimeError(process.stderr.read())


def start(binary: str) -> tuple[subprocess.Popen[str], int]:
    process = subprocess.Popen(
        [binary, "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    ready, _, _ = select.select([process.stdout], [], [], 5)
    if not ready:
        terminate(process)
        raise RuntimeError("server did not report its port")
    line = process.stdout.readline().strip()
    if not line.startswith("PORT "):
        terminate(process)
        raise RuntimeError(f"invalid startup line: {line!r}")
    return process, int(line.split()[1])


def connect(port: int, timeout: float = 3.0) -> socket.socket:
    peer = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    peer.settimeout(timeout)
    return peer


def recv_line(stream) -> bytes:
    line = stream.readline()
    if not line.endswith(b"\n"):
        raise AssertionError(f"incomplete response: {line!r}")
    return line


def normal(binary: str) -> None:
    process, port = start(binary)
    try:
        first = connect(port)
        stream = first.makefile("rb")
        first.sendall(b"alpha\n")
        assert recv_line(stream) == b"ECHO alpha\n"

        # 줄바꿈 전 응답하는 구현과 recv 결과를 한 줄로 가정한 구현을 검출합니다.
        first.sendall(b"par")
        readable, _, _ = select.select([first], [], [], 0.05)
        assert not readable
        first.sendall(b"tial\none\ntwo\nCOUNT\n")
        assert recv_line(stream) == b"ECHO partial\n"
        assert recv_line(stream) == b"ECHO one\n"
        assert recv_line(stream) == b"ECHO two\n"
        assert recv_line(stream) == b"COUNT 4\n"

        second = connect(port)
        second_stream = second.makefile("rb")
        second.sendall(b"beta\nCOUNT\nQUIT\n")
        assert recv_line(second_stream) == b"ECHO beta\n"
        assert recv_line(second_stream) == b"COUNT 1\n"
        assert recv_line(second_stream) == b"BYE\n"
        assert second_stream.read() == b""
        second_stream.close()
        second.close()

        first.sendall(b"QUIT\n")
        assert recv_line(stream) == b"BYE\n"
        assert stream.read() == b""
        stream.close()
        first.close()
    finally:
        terminate(process)


def stress(binary: str) -> None:
    process, port = start(binary)
    errors: list[BaseException] = []
    lock = threading.Lock()
    count = 40
    barrier = threading.Barrier(count)

    def worker(index: int) -> None:
        try:
            peer = connect(port, 5)
            stream = peer.makefile("rb")
            barrier.wait(timeout=5)
            message = f"client-{index}\n".encode()
            peer.sendall(message)
            assert recv_line(stream) == b"ECHO " + message
            stream.close()
            peer.close()
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert not [thread for thread in threads if thread.is_alive()]
        assert not errors, errors
    finally:
        terminate(process)


def backpressure(binary: str) -> None:
    process, port = start(binary)
    slow = None
    try:
        # 응답을 읽지 않는 client 하나가 다른 client 처리까지 막지 않는지 확인합니다.
        slow = connect(port)
        slow.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        slow.settimeout(0.5)
        payload = b"x" * 200 + b"\n"
        try:
            slow.sendall(payload * 2000)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

        closed = False
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                chunk = slow.recv(65536)
            except (ConnectionResetError, BrokenPipeError):
                closed = True
                break
            except socket.timeout:
                continue
            if not chunk:
                closed = True
                break
        assert closed, "slow reader was not closed after exceeding output limit"

        probe = connect(port)
        stream = probe.makefile("rb")
        probe.sendall(b"still-alive\n")
        assert recv_line(stream) == b"ECHO still-alive\n"
        stream.close()
        probe.close()
    finally:
        if slow is not None:
            slow.close()
        terminate(process)


def leak_check(binary: str) -> None:
    process, port = start(binary)
    try:
        directory = Path(f"/proc/{process.pid}/fd")
        if not directory.is_dir():
            print("SKIP: /proc descriptor inspection is unavailable")
            return
        # 반복 연결 뒤 fd 수가 계속 증가하면 종료 경로의 close 누락입니다.
        before = len(list(directory.iterdir()))
        for index in range(100):
            peer = connect(port)
            stream = peer.makefile("rb")
            message = f"leak-{index}\n".encode()
            peer.sendall(message)
            assert recv_line(stream) == b"ECHO " + message
            stream.close()
            peer.close()

        deadline = time.monotonic() + 5
        after = len(list(directory.iterdir()))
        while time.monotonic() < deadline and after > before + 2:
            time.sleep(0.05)
            after = len(list(directory.iterdir()))
        assert after <= before + 2, (before, after)
    finally:
        terminate(process)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--backpressure", action="store_true")
    parser.add_argument("--leak-check", action="store_true")
    args = parser.parse_args()
    binary = os.path.realpath(args.binary)

    if args.stress:
        stress(binary)
    elif args.backpressure:
        backpressure(binary)
    elif args.leak_check:
        leak_check(binary)
    else:
        normal(binary)
        stress(binary)
        backpressure(binary)
        leak_check(binary)


if __name__ == "__main__":
    main()
