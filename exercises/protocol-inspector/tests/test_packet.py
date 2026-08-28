from __future__ import annotations

from pathlib import Path
import unittest

from protocol_inspector import (
    PacketFormatError,
    decode_ethernet_ipv4_tcp,
    parse_ethernet,
    parse_ipv4,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def read_hex(name: str) -> bytes:
    chunks: list[str] = []
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip().replace(" ", "")
        if body:
            chunks.append(body)
    return bytes.fromhex("".join(chunks))


class PacketParserTests(unittest.TestCase):
    def test_decodes_valid_syn_frame(self) -> None:
        decoded = decode_ethernet_ipv4_tcp(read_hex("syn-frame.hex"))
        self.assertEqual(decoded.ethernet.destination, "02:00:00:00:00:02")
        self.assertEqual(decoded.ethernet.source, "02:00:00:00:00:01")
        self.assertIsNotNone(decoded.ipv4)
        self.assertIsNotNone(decoded.tcp)
        assert decoded.ipv4 is not None
        assert decoded.tcp is not None
        self.assertEqual(str(decoded.ipv4.source), "192.0.2.10")
        self.assertEqual(str(decoded.ipv4.destination), "198.51.100.20")
        self.assertTrue(decoded.ipv4.checksum_valid)
        self.assertEqual(decoded.tcp.source_port, 49152)
        self.assertEqual(decoded.tcp.destination_port, 443)
        self.assertEqual(decoded.tcp.sequence_number, 0x01020304)
        self.assertEqual(decoded.tcp.flags, ("SYN",))
        self.assertTrue(decoded.tcp.checksum_valid)
        self.assertEqual(decoded.tcp.options, bytes.fromhex("020405b4"))

    def test_vlan_tag_changes_the_payload_offset(self) -> None:
        # 14바이트 고정 오프셋을 쓰는 파서는 VLAN 뒤의 EtherType과 페이로드를 잘못 읽습니다.
        raw = read_hex("syn-frame.hex")
        tagged = raw[:12] + bytes.fromhex("810060640800") + raw[14:]
        frame = parse_ethernet(tagged)
        self.assertIsNotNone(frame.vlan)
        assert frame.vlan is not None
        self.assertEqual(frame.vlan.priority, 3)
        self.assertEqual(frame.vlan.vlan_id, 100)
        self.assertEqual(frame.ethertype, 0x0800)
        self.assertEqual(frame.payload, raw[14:])

    def test_non_ipv4_payload_is_not_misparsed(self) -> None:
        raw = bytes.fromhex("ffffffffffff0200000000010806") + b"arp"
        decoded = decode_ethernet_ipv4_tcp(raw)
        self.assertIsNone(decoded.ipv4)
        self.assertIsNone(decoded.tcp)

    def test_fragmented_packets_are_not_misparsed_as_complete_tcp_segments(self) -> None:
        from protocol_inspector import internet_checksum

        for flags_and_offset in (0x2000, 1):
            with self.subTest(flags_and_offset=flags_and_offset):
                raw = bytearray(read_hex("syn-frame.hex"))
                ip = bytearray(raw[14:])
                ip[6:8] = flags_and_offset.to_bytes(2, "big")
                ip[10:12] = b"\x00\x00"
                ip[10:12] = internet_checksum(bytes(ip[:20])).to_bytes(2, "big")
                raw[14:] = ip
                decoded = decode_ethernet_ipv4_tcp(bytes(raw))
                self.assertIsNotNone(decoded.ipv4)
                self.assertIsNone(decoded.tcp)

    def test_rejects_truncated_and_self_inconsistent_headers(self) -> None:
        with self.assertRaises(PacketFormatError):
            parse_ethernet(b"\x00" * 13)
        with self.assertRaises(PacketFormatError):
            parse_ipv4(bytes.fromhex("4500003c") + b"\x00" * 16)
        with self.assertRaises(PacketFormatError):
            parse_ipv4(bytes.fromhex("44000014") + b"\x00" * 16)


if __name__ == "__main__":
    unittest.main()
