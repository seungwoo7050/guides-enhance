"""Ethernet, IPv4와 TCP 헤더를 길이 검증 뒤 파싱합니다."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import Final

from .checksum import checksum_is_valid, tcp_checksum_ipv4
from .errors import PacketFormatError

ETHERTYPE_IPV4: Final[int] = 0x0800
ETHERTYPE_VLAN: Final[set[int]] = {0x8100, 0x88A8}
IP_PROTOCOL_TCP: Final[int] = 6


def _format_mac(raw: bytes) -> str:
    return ":".join(f"{octet:02x}" for octet in raw)


@dataclass(frozen=True)
class VlanTag:
    priority: int
    drop_eligible: bool
    vlan_id: int


@dataclass(frozen=True)
class EthernetFrame:
    destination: str
    source: str
    ethertype: int
    payload: bytes
    vlan: VlanTag | None = None


@dataclass(frozen=True)
class IPv4Packet:
    header_length: int
    dscp: int
    ecn: int
    total_length: int
    identification: int
    flags: int
    fragment_offset: int
    ttl: int
    protocol: int
    header_checksum: int
    checksum_valid: bool
    source: ipaddress.IPv4Address
    destination: ipaddress.IPv4Address
    options: bytes
    payload: bytes


@dataclass(frozen=True)
class TCPSegment:
    source_port: int
    destination_port: int
    sequence_number: int
    acknowledgment_number: int
    header_length: int
    flags: tuple[str, ...]
    window_size: int
    checksum: int
    checksum_valid: bool | None
    urgent_pointer: int
    options: bytes
    payload: bytes


@dataclass(frozen=True)
class DecodedPacket:
    ethernet: EthernetFrame
    ipv4: IPv4Packet | None
    tcp: TCPSegment | None


# [Implementation 2] Ethernet and VLAN parsing
# 기본 14바이트와 VLAN 태그 4바이트가 실제로 있을 때만 페이로드 위치를 계산합니다.
def parse_ethernet(data: bytes) -> EthernetFrame:
    """FCS가 제외된 Ethernet 프레임을 파싱합니다."""

    if len(data) < 14:
        raise PacketFormatError("An Ethernet header requires at least 14 bytes")

    destination = _format_mac(data[0:6])
    source = _format_mac(data[6:12])
    ethertype = int.from_bytes(data[12:14], "big")
    offset = 14
    vlan: VlanTag | None = None

    if ethertype in ETHERTYPE_VLAN:
        if len(data) < 18:
            raise PacketFormatError("The 802.1Q tag is truncated")
        tci = int.from_bytes(data[14:16], "big")
        vlan = VlanTag(
            priority=(tci >> 13) & 0b111,
            drop_eligible=bool((tci >> 12) & 0b1),
            vlan_id=tci & 0x0FFF,
        )
        ethertype = int.from_bytes(data[16:18], "big")
        offset = 18

    return EthernetFrame(
        destination=destination,
        source=source,
        ethertype=ethertype,
        payload=data[offset:],
        vlan=vlan,
    )


# [Implementation 2-1] IPv4 length and checksum validation
# IHL과 Total Length가 실제 입력 길이 안에 있을 때만 헤더와 페이로드를 나눕니다.
def parse_ipv4(data: bytes) -> IPv4Packet:
    """Total Length까지 포함된 하나의 IPv4 패킷을 파싱합니다."""

    if len(data) < 20:
        raise PacketFormatError("An IPv4 header requires at least 20 bytes")

    version = data[0] >> 4
    ihl_words = data[0] & 0x0F
    if version != 4:
        raise PacketFormatError(f"The version field is not IPv4: {version}")
    if ihl_words < 5:
        raise PacketFormatError(f"The IPv4 IHL is too small: {ihl_words}")

    header_length = ihl_words * 4
    if len(data) < header_length:
        raise PacketFormatError("The IPv4 header, including options, is truncated")

    total_length = int.from_bytes(data[2:4], "big")
    if total_length < header_length:
        raise PacketFormatError("The IPv4 total length is smaller than its header")
    if total_length > len(data):
        raise PacketFormatError("The input is shorter than the IPv4 total length")

    flags_and_offset = int.from_bytes(data[6:8], "big")
    header = data[:header_length]
    return IPv4Packet(
        header_length=header_length,
        dscp=data[1] >> 2,
        ecn=data[1] & 0b11,
        total_length=total_length,
        identification=int.from_bytes(data[4:6], "big"),
        flags=(flags_and_offset >> 13) & 0b111,
        fragment_offset=flags_and_offset & 0x1FFF,
        ttl=data[8],
        protocol=data[9],
        header_checksum=int.from_bytes(data[10:12], "big"),
        checksum_valid=checksum_is_valid(header),
        source=ipaddress.IPv4Address(data[12:16]),
        destination=ipaddress.IPv4Address(data[16:20]),
        options=data[20:header_length],
        payload=data[header_length:total_length],
    )


_FLAG_NAMES: Final[tuple[tuple[int, str], ...]] = (
    (0x100, "NS"),
    (0x080, "CWR"),
    (0x040, "ECE"),
    (0x020, "URG"),
    (0x010, "ACK"),
    (0x008, "PSH"),
    (0x004, "RST"),
    (0x002, "SYN"),
    (0x001, "FIN"),
)


# [Implementation 2-2] TCP length and checksum validation
# Data Offset으로 헤더 길이를 확인하고 두 IPv4 주소가 있을 때만 체크섬을 검증합니다.
def parse_tcp(
    data: bytes,
    *,
    source: str | ipaddress.IPv4Address | None = None,
    destination: str | ipaddress.IPv4Address | None = None,
) -> TCPSegment:
    """TCP 세그먼트를 파싱하고 필요하면 IPv4 의사 헤더 체크섬을 검증합니다."""

    if len(data) < 20:
        raise PacketFormatError("A TCP header requires at least 20 bytes")

    data_offset_words = data[12] >> 4
    if data_offset_words < 5:
        raise PacketFormatError(f"The TCP data offset is too small: {data_offset_words}")
    header_length = data_offset_words * 4
    if len(data) < header_length:
        raise PacketFormatError("The TCP header, including options, is truncated")

    raw_flags = ((data[12] & 0x01) << 8) | data[13]
    flags = tuple(name for bit, name in _FLAG_NAMES if raw_flags & bit)

    checksum_valid: bool | None = None
    if (source is None) != (destination is None):
        raise ValueError("TCP checksum validation requires both source and destination")
    if source is not None and destination is not None:
        checksum_valid = tcp_checksum_ipv4(source, destination, data) == 0

    return TCPSegment(
        source_port=int.from_bytes(data[0:2], "big"),
        destination_port=int.from_bytes(data[2:4], "big"),
        sequence_number=int.from_bytes(data[4:8], "big"),
        acknowledgment_number=int.from_bytes(data[8:12], "big"),
        header_length=header_length,
        flags=flags,
        window_size=int.from_bytes(data[14:16], "big"),
        checksum=int.from_bytes(data[16:18], "big"),
        checksum_valid=checksum_valid,
        urgent_pointer=int.from_bytes(data[18:20], "big"),
        options=data[20:header_length],
        payload=data[header_length:],
    )


# [Implementation 2-3] Supported packet decoding
# 지원하지 않는 EtherType, 상위 프로토콜 또는 단편은 TCP로 억지 해석하지 않습니다.
def decode_ethernet_ipv4_tcp(data: bytes) -> DecodedPacket:
    """지원하는 헤더만 순서대로 파싱하고 나머지 페이로드는 그대로 둡니다."""

    ethernet = parse_ethernet(data)
    if ethernet.ethertype != ETHERTYPE_IPV4:
        return DecodedPacket(ethernet=ethernet, ipv4=None, tcp=None)

    ipv4 = parse_ipv4(ethernet.payload)
    more_fragments = bool(ipv4.flags & 0b001)
    if ipv4.protocol != IP_PROTOCOL_TCP or ipv4.fragment_offset != 0 or more_fragments:
        return DecodedPacket(ethernet=ethernet, ipv4=ipv4, tcp=None)

    tcp = parse_tcp(
        ipv4.payload,
        source=ipv4.source,
        destination=ipv4.destination,
    )
    return DecodedPacket(ethernet=ethernet, ipv4=ipv4, tcp=tcp)
