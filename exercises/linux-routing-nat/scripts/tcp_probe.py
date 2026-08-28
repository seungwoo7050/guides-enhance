#!/usr/bin/env python3
"""손실 제거 뒤 TCP 연결과 페이로드 왕복이 복구되는지 확인합니다."""

from __future__ import annotations

import argparse
import socket


# [Implementation 6] TCP request/reply probe
# 연결 성공만 확인하지 않고 고정 페이로드의 요청과 응답까지 검사합니다.
def run_server(bind: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((bind, port))
        listener.listen(1)
        listener.settimeout(12)
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(5)
            data = connection.recv(16)
            if data != b"probe":
                raise SystemExit(f"Unexpected request payload: {data!r}")
            connection.sendall(b"ack")
    return 0


def run_client(target: str, port: int, timeout: float) -> int:
    with socket.create_connection((target, port), timeout=timeout) as connection:
        connection.settimeout(5)
        connection.sendall(b"probe")
        if connection.recv(16) != b"ack":
            raise SystemExit("Expected acknowledgment payload was not received")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create one TCP connection for a SYN retransmission experiment."
    )
    sub = parser.add_subparsers(dest="mode", required=True, title="role")
    server = sub.add_parser("server", help="run the TCP server")
    server.add_argument("--bind", required=True, help="address to bind")
    server.add_argument("--port", type=int, required=True, help="port to bind")
    client = sub.add_parser("client", help="run the TCP client")
    client.add_argument("--target", required=True, help="server address")
    client.add_argument("--port", type=int, required=True, help="server port")
    client.add_argument("--timeout", type=float, default=10, help="connect timeout in seconds")
    args = parser.parse_args()
    if args.mode == "server":
        return run_server(args.bind, args.port)
    return run_client(args.target, args.port, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
