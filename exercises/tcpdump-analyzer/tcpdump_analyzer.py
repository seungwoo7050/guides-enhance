#!/usr/bin/env python3
"""tcpdump 텍스트에서 TCP 핸드셰이크와 반복 전송 후보를 찾습니다."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

# [Implementation 1] Supported tcpdump line grammar
# 지원하는 ``tcpdump -nn -tt`` 한 줄 형식만 읽고 다른 형식은 무시합니다.
LINE = re.compile(
    r"^(?P<time>\d+(?:\.\d+)?)\s+IP6?\s+"
    r"(?P<source>\S+)\s+>\s+(?P<destination>\S+):\s+"
    r"Flags \[(?P<flags>[^]]+)\]"
    r"(?P<rest>.*)$"
)
SEQ = re.compile(r"\bseq\s+(?P<start>\d+)(?::(?P<end>\d+))?")
ACK = re.compile(r"\back\s+(?P<ack>\d+)")
LENGTH = re.compile(r"\blength\s+(?P<length>\d+)")


# [Implementation 1-1] Parsed TCP packet model
# 원본 한 줄에서 이후 판정에 필요한 필드만 변경할 수 없는 객체로 보관합니다.
@dataclass(frozen=True)
class Packet:
    timestamp: float
    source: str
    destination: str
    flags: str
    sequence_start: int | None
    sequence_end: int | None
    acknowledgment: int | None
    length: int | None

    @property
    def signature(self) -> tuple[str, str, str, int | None, int | None]:
        return (
            self.source,
            self.destination,
            self.flags,
            self.sequence_start,
            self.sequence_end,
        )


# [Implementation 1-2] Trace normalization
# 일치하지 않는 줄은 오류로 만들지 않고 분석 대상에서 제외합니다.
def parse_line(line: str) -> Packet | None:
    match = LINE.match(line.strip())
    if match is None:
        return None
    rest = match.group("rest")
    seq_match = SEQ.search(rest)
    ack_match = ACK.search(rest)
    length_match = LENGTH.search(rest)
    start = int(seq_match.group("start")) if seq_match else None
    end = int(seq_match.group("end")) if seq_match and seq_match.group("end") else start
    return Packet(
        timestamp=float(match.group("time")),
        source=match.group("source"),
        destination=match.group("destination"),
        flags=match.group("flags"),
        sequence_start=start,
        sequence_end=end,
        acknowledgment=int(ack_match.group("ack")) if ack_match else None,
        length=int(length_match.group("length")) if length_match else None,
    )


def parse_trace(text: str) -> list[Packet]:
    return [
        packet
        for line in text.splitlines()
        if (packet := parse_line(line)) is not None
    ]


def _is_syn(packet: Packet) -> bool:
    return "S" in packet.flags and "." not in packet.flags


def _is_syn_ack(packet: Packet) -> bool:
    return "S" in packet.flags and "." in packet.flags


def _is_plain_ack(packet: Packet) -> bool:
    return packet.flags == "."


# [Implementation 2] Sequence-aware handshake validation
# 방향뿐 아니라 SYN이 소비한 순서 번호까지 맞아야 핸드셰이크로 인정합니다.
def handshake_complete(packets: list[Packet]) -> bool:
    for first_index, first in enumerate(packets):
        if not _is_syn(first) or first.sequence_start is None:
            continue
        expected_syn_ack = (first.sequence_start + 1) & 0xFFFFFFFF
        for second_index in range(first_index + 1, len(packets)):
            second = packets[second_index]
            if not (
                _is_syn_ack(second)
                and second.source == first.destination
                and second.destination == first.source
                and second.acknowledgment == expected_syn_ack
                and second.sequence_start is not None
            ):
                continue
            expected_final_ack = (second.sequence_start + 1) & 0xFFFFFFFF
            for third in packets[second_index + 1 :]:
                if (
                    _is_plain_ack(third)
                    and third.source == first.source
                    and third.destination == first.destination
                    and third.acknowledgment == expected_final_ack
                ):
                    return True
    return False


# [Implementation 3] Repeated-segment candidate detection
# 같은 튜플, 플래그와 순서 번호의 반복은 후보일 뿐 실제 손실 원인을 확정하지 않습니다.
def retransmission_candidates(packets: list[Packet]) -> list[dict[str, object]]:
    first_seen: dict[tuple[str, str, str, int | None, int | None], Packet] = {}
    duplicates: list[dict[str, object]] = []
    for packet in packets:
        if packet.sequence_start is None:
            continue
        previous = first_seen.get(packet.signature)
        if previous is None:
            first_seen[packet.signature] = packet
            continue
        duplicates.append(
            {
                "source": packet.source,
                "destination": packet.destination,
                "flags": packet.flags,
                "sequence_start": packet.sequence_start,
                "sequence_end": packet.sequence_end,
                "first_timestamp": previous.timestamp,
                "repeat_timestamp": packet.timestamp,
                "delay_seconds": round(packet.timestamp - previous.timestamp, 6),
            }
        )
    return duplicates


# [Implementation 4] Report assembly
def analyze(text: str) -> dict[str, object]:
    packets = parse_trace(text)
    return {
        "packet_count": len(packets),
        "handshake_complete": handshake_complete(packets),
        "retransmission_candidates": retransmission_candidates(packets),
        "packets": [asdict(packet) for packet in packets],
    }


# [Implementation 4-1] Trace-file CLI handling
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find a TCP handshake and retransmission candidates in tcpdump text."
    )
    parser.add_argument("trace", type=Path, help="tcpdump text file to analyze")
    args = parser.parse_args()
    result = analyze(args.trace.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
