"""classic PCAP의 global header와 packet record를 파싱합니다."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .errors import PacketFormatError


@dataclass(frozen=True)
class CapturedPacket:
    timestamp_seconds: int
    timestamp_fraction: int
    original_length: int
    data: bytes


@dataclass(frozen=True)
class Capture:
    byte_order: str
    timestamp_resolution: str
    snap_length: int
    link_type: int
    packets: tuple[CapturedPacket, ...]


_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", "microseconds"),
    b"\xa1\xb2\xc3\xd4": (">", "microseconds"),
    b"\x4d\x3c\xb2\xa1": ("<", "nanoseconds"),
    b"\xa1\xb2\x3c\x4d": (">", "nanoseconds"),
}


# [Implementation 3] Classic PCAP record parsing
# magic 값으로 바이트 순서와 타임스탬프 단위를 먼저 정한 뒤 레코드 길이를 검증합니다.
def parse_pcap(data: bytes) -> Capture:
    """classic PCAP 2.4 형식의 전체 바이트열을 파싱합니다."""

    if not isinstance(data, bytes):
        raise ValueError("PCAP input must be bytes")
    if len(data) < 24:
        raise PacketFormatError("The PCAP global header is truncated")

    format_info = _MAGIC.get(data[:4])
    if format_info is None:
        raise PacketFormatError("The PCAP magic value is not supported")
    order, resolution = format_info

    major, minor, _zone, _accuracy, snap_length, link_type = struct.unpack_from(
        f"{order}HHiIII", data, 4
    )
    if (major, minor) != (2, 4):
        raise PacketFormatError(f"Unsupported PCAP version: {major}.{minor}")
    if snap_length == 0:
        raise PacketFormatError("PCAP snaplen must be greater than zero")

    packets: list[CapturedPacket] = []
    offset = 24
    while offset < len(data):
        if len(data) - offset < 16:
            raise PacketFormatError("A PCAP packet header is truncated")
        seconds, fraction, included, original = struct.unpack_from(
            f"{order}IIII", data, offset
        )
        offset += 16

        fraction_limit = 1_000_000 if resolution == "microseconds" else 1_000_000_000
        if fraction >= fraction_limit:
            raise PacketFormatError("The packet timestamp fraction exceeds its resolution")
        if included > snap_length:
            raise PacketFormatError("The captured length exceeds PCAP snaplen")
        if included > original:
            raise PacketFormatError("The captured length exceeds the original packet length")

        end = offset + included
        if end > len(data):
            raise PacketFormatError("The PCAP packet data is truncated")
        packets.append(
            CapturedPacket(
                timestamp_seconds=seconds,
                timestamp_fraction=fraction,
                original_length=original,
                data=data[offset:end],
            )
        )
        offset = end

    return Capture(
        byte_order="little" if order == "<" else "big",
        timestamp_resolution=resolution,
        snap_length=snap_length,
        link_type=link_type,
        packets=tuple(packets),
    )
