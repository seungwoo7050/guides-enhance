"""인터넷 체크섬과 IPv4 TCP 의사 헤더 체크섬을 계산합니다."""

from __future__ import annotations

import ipaddress


# [Implementation 1] Internet checksum calculation
# 홀수 길이는 계산할 때만 0바이트를 덧붙이고 16비트 올림을 다시 더합니다.
def internet_checksum(data: bytes) -> int:
    """16비트 1의 보수 합을 계산해 최종 1의 보수 값을 반환합니다.

    checksum 필드를 0으로 둔 입력에는 생성할 값을 반환합니다. 전송된 checksum을
    포함한 전체 header를 넣었을 때 0이면 입력이 유효합니다.
    """

    if len(data) % 2:
        data += b"\x00"

    total = 0
    for offset in range(0, len(data), 2):
        total += int.from_bytes(data[offset : offset + 2], "big")
        total = (total & 0xFFFF) + (total >> 16)

    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def checksum_is_valid(data: bytes) -> bool:
    """전송된 체크섬을 포함한 전체 입력이 유효한지 확인합니다."""

    return internet_checksum(data) == 0


# [Implementation 1-1] IPv4 TCP pseudo-header checksum
# 출발지·목적지 주소, 프로토콜 번호와 TCP 길이를 세그먼트 앞에 붙여 계산합니다.
def tcp_checksum_ipv4(
    source: str | ipaddress.IPv4Address,
    destination: str | ipaddress.IPv4Address,
    segment: bytes,
) -> int:
    """IPv4 의사 헤더를 포함한 TCP 체크섬을 계산합니다."""

    source_address = ipaddress.IPv4Address(source)
    destination_address = ipaddress.IPv4Address(destination)
    if len(segment) > 0xFFFF:
        raise ValueError("A TCP segment cannot exceed 65535 bytes")

    pseudo_header = (
        source_address.packed
        + destination_address.packed
        + b"\x00"
        + b"\x06"
        + len(segment).to_bytes(2, "big")
    )
    return internet_checksum(pseudo_header + segment)
