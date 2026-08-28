#!/usr/bin/env python3
"""SNAT 전후의 주소를 확인할 수 있는 UDP 요청과 응답을 만듭니다."""

from __future__ import annotations

import argparse
from pathlib import Path
import socket


# [Implementation 5] UDP request/reply probe
# 서버는 실제 상대 주소를 파일에 남기고 같은 소켓으로 응답합니다.
def run_server(bind: str, port: int, output: Path, ready: Path) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((bind, port))
        sock.settimeout(8)
        # ``x`` 모드로 예상하지 못한 기존 표시 파일을 덮어쓰지 않습니다.
        # 바인드가 끝난 뒤 표시 파일을 만들어 고정된 대기 시간 없이 준비 완료를 알립니다.
        with ready.open("x", encoding="utf-8") as marker:
            marker.write("ready\n")
        payload, peer = sock.recvfrom(1024)
        output.write_text(
            f"{peer[0]}:{peer[1]} {payload.decode('ascii')}\n",
            encoding="utf-8",
        )
        sock.sendto(b"ack", peer)
    return 0


def run_client(target: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(8)
        sock.sendto(b"probe", (target, port))
        payload, _ = sock.recvfrom(1024)
        if payload != b"ack":
            raise SystemExit(f"Unexpected response: {payload!r}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a UDP exchange whose translated source is observable."
    )
    sub = parser.add_subparsers(dest="mode", required=True, title="role")
    server = sub.add_parser("server", help="run the UDP server")
    server.add_argument("--bind", required=True, help="address to bind")
    server.add_argument("--port", type=int, required=True, help="port to bind")
    server.add_argument("--output", type=Path, required=True, help="peer evidence file")
    server.add_argument(
        "--ready",
        type=Path,
        required=True,
        help="exclusive marker created after bind completes",
    )
    client = sub.add_parser("client", help="run the UDP client")
    client.add_argument("--target", required=True, help="server address")
    client.add_argument("--port", type=int, required=True, help="server port")
    args = parser.parse_args()
    if args.mode == "server":
        return run_server(args.bind, args.port, args.output, args.ready)
    return run_client(args.target, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
