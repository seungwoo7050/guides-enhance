"""protocol-inspector 기능을 하위 명령과 출력 형식에 연결합니다."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

from .checksum import internet_checksum
from .packet import decode_ethernet_ipv4_tcp
from .pcap import parse_pcap
from .routing import Route, RoutingTable
from .tcp_state import EndpointRole, TCPEndpoint, TCPEvent


def _load_hex(path: Path) -> bytes:
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip().replace(" ", "")
        if body:
            chunks.append(body)
    return bytes.fromhex("".join(chunks))


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if hasattr(value, "compressed"):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


# [Implementation 6] CLI result conversion
# 파서와 상태 기계의 결과를 필드 순서가 고정된 JSON과 종료 상태로 변환합니다.
def command_decode(args: argparse.Namespace) -> int:
    decoded = decode_ethernet_ipv4_tcp(_load_hex(args.path))
    payload = {
        "ethernet": _jsonable(asdict(decoded.ethernet)),
        "ipv4": _jsonable(asdict(decoded.ipv4)) if decoded.ipv4 else None,
        "tcp": _jsonable(asdict(decoded.tcp)) if decoded.tcp else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_checksum(args: argparse.Namespace) -> int:
    data = bytes.fromhex(args.hex.replace(" ", ""))
    print(f"0x{internet_checksum(data):04x}")
    return 0


def command_pcap(args: argparse.Namespace) -> int:
    capture = parse_pcap(args.path.read_bytes())
    print(
        json.dumps(
            {
                "byte_order": capture.byte_order,
                "timestamp_resolution": capture.timestamp_resolution,
                "snap_length": capture.snap_length,
                "link_type": capture.link_type,
                "packets": [
                    {
                        "timestamp_seconds": packet.timestamp_seconds,
                        "timestamp_fraction": packet.timestamp_fraction,
                        "captured_length": len(packet.data),
                        "original_length": packet.original_length,
                        "data": packet.data.hex(),
                    }
                    for packet in capture.packets
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_route(args: argparse.Namespace) -> int:
    rows = json.loads(args.table.read_text(encoding="utf-8"))
    table = RoutingTable()
    for row in rows:
        table.add(
            Route.from_strings(
                row["network"],
                row["interface"],
                next_hop=row.get("next_hop"),
                metric=int(row.get("metric", 0)),
            )
        )
    route = table.lookup(args.destination)
    if route is None:
        print("no-route")
        return 1
    print(
        json.dumps(
            {
                "network": str(route.network),
                "interface": route.interface,
                "next_hop": str(route.next_hop) if route.next_hop else None,
                "metric": route.metric,
            },
            ensure_ascii=False,
        )
    )
    return 0


def command_tcp(args: argparse.Namespace) -> int:
    endpoint = TCPEndpoint(EndpointRole(args.role))
    print(endpoint.state.value)
    for raw_event in args.events.split(","):
        event = TCPEvent(raw_event.strip())
        print(endpoint.apply(event).value)
    return 0


# [Implementation 6-1] Subcommand registration and dispatch
# 모든 하위 명령과 처리 함수 연결을 한곳에서 등록해 누락을 쉽게 확인합니다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m protocol_inspector",
        description="Inspect frames, checksums, routes, PCAP records, and TCP state transitions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, title="commands")

    decode = subparsers.add_parser("decode", help="decode an Ethernet/IPv4/TCP frame")
    decode.add_argument("path", type=Path, help="path to a hexadecimal frame file")
    decode.set_defaults(handler=command_decode)

    checksum = subparsers.add_parser("checksum", help="calculate an Internet checksum")
    checksum.add_argument("hex", help="hexadecimal byte sequence")
    checksum.set_defaults(handler=command_checksum)

    pcap = subparsers.add_parser("pcap", help="parse classic PCAP records")
    pcap.add_argument("path", type=Path, help="path to a classic PCAP file")
    pcap.set_defaults(handler=command_pcap)

    route = subparsers.add_parser("route", help="perform IPv4 longest-prefix lookup")
    route.add_argument("--table", type=Path, required=True, help="JSON routing table")
    route.add_argument("--destination", required=True, help="destination IPv4 address")
    route.set_defaults(handler=command_route)

    tcp = subparsers.add_parser("tcp", help="apply TCP state-machine events")
    tcp.add_argument(
        "--role",
        choices=[role.value for role in EndpointRole],
        required=True,
        help="endpoint role",
    )
    tcp.add_argument("--events", required=True, help="comma-separated TCP events")
    tcp.set_defaults(handler=command_tcp)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
