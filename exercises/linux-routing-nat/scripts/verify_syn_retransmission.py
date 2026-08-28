#!/usr/bin/env python3
"""tcpdump 텍스트에서 같은 TCP SYN이 반복되었는지 확인합니다."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

LINE = re.compile(
    r"^(?P<time>\d+(?:\.\d+)?)\s+IP6?\s+"
    r"(?P<source>\S+)\s+>\s+(?P<destination>\S+):\s+"
    r"Flags \[(?P<flags>[^]]+)\](?P<rest>.*)$"
)
SEQ = re.compile(r"\bseq\s+(?P<start>\d+)(?::(?P<end>\d+))?")


# [Implementation 6-1] Repeated-SYN verification
# 시각은 식별값에서 제외하고 튜플과 순서 번호가 같은 SYN만 반복 후보로 봅니다.
@dataclass(frozen=True)
class SynObservation:
    timestamp: float
    source: str
    destination: str
    sequence_start: int
    sequence_end: int

    @property
    def signature(self) -> tuple[str, str, int, int]:
        return (
            self.source,
            self.destination,
            self.sequence_start,
            self.sequence_end,
        )


def parse_syn_observations(text: str) -> list[SynObservation]:
    observations: list[SynObservation] = []
    for line in text.splitlines():
        match = LINE.match(line.strip())
        if match is None or match.group("flags") != "S":
            continue
        sequence = SEQ.search(match.group("rest"))
        if sequence is None:
            continue
        start = int(sequence.group("start"))
        end = int(sequence.group("end") or start)
        observations.append(
            SynObservation(
                timestamp=float(match.group("time")),
                source=match.group("source"),
                destination=match.group("destination"),
                sequence_start=start,
                sequence_end=end,
            )
        )
    return observations


def retransmission_candidates(
    observations: list[SynObservation],
) -> list[dict[str, object]]:
    first_seen: dict[tuple[str, str, int, int], SynObservation] = {}
    candidates: list[dict[str, object]] = []
    for observation in observations:
        previous = first_seen.get(observation.signature)
        if previous is None:
            first_seen[observation.signature] = observation
            continue
        candidate = asdict(observation)
        candidate["first_timestamp"] = previous.timestamp
        candidate["delay_seconds"] = round(
            observation.timestamp - previous.timestamp,
            6,
        )
        candidates.append(candidate)
    return candidates


def analyze(text: str) -> dict[str, object]:
    observations = parse_syn_observations(text)
    return {
        "syn_count": len(observations),
        "retransmission_candidates": retransmission_candidates(observations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that tcpdump output contains a repeated TCP SYN signature."
    )
    parser.add_argument("trace", type=Path, help="tcpdump text trace")
    args = parser.parse_args()
    report = analyze(args.trace.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["retransmission_candidates"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
