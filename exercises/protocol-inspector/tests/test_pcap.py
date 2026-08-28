from __future__ import annotations

import struct
import unittest

from protocol_inspector import PacketFormatError, parse_pcap


def capture(payload: bytes, *, included: int | None = None) -> bytes:
    stored = len(payload) if included is None else included
    global_header = b"\xd4\xc3\xb2\xa1" + struct.pack(
        "<HHIIII", 2, 4, 0, 0, 65535, 1
    )
    packet_header = struct.pack("<IIII", 10, 250, stored, len(payload))
    return global_header + packet_header + payload[:stored]


class PcapTests(unittest.TestCase):
    def test_reads_classic_little_endian_capture(self) -> None:
        parsed = parse_pcap(capture(b"ethernet-frame"))
        self.assertEqual(parsed.byte_order, "little")
        self.assertEqual(parsed.timestamp_resolution, "microseconds")
        self.assertEqual(parsed.link_type, 1)
        self.assertEqual(parsed.packets[0].data, b"ethernet-frame")
        self.assertEqual(parsed.packets[0].original_length, 14)

    def test_accepts_snaplen_truncation(self) -> None:
        parsed = parse_pcap(capture(b"0123456789", included=4))
        self.assertEqual(parsed.packets[0].data, b"0123")
        self.assertEqual(parsed.packets[0].original_length, 10)

    def test_rejects_truncated_or_inconsistent_records(self) -> None:
        # 선언 길이만 믿고 짧은 레코드를 읽거나 남은 바이트를 무시하는 구현을 검출합니다.
        for raw in (
            b"\xd4\xc3\xb2\xa1",
            capture(b"abc")[:-1],
            capture(b"abc") + b"\x00",
        ):
            with self.subTest(length=len(raw)):
                with self.assertRaises(PacketFormatError):
                    parse_pcap(raw)

    def test_rejects_timestamp_fraction_outside_resolution(self) -> None:
        raw = bytearray(capture(b"x"))
        raw[28:32] = (1_000_000).to_bytes(4, "little")
        with self.assertRaises(PacketFormatError):
            parse_pcap(bytes(raw))


if __name__ == "__main__":
    unittest.main()
