from __future__ import annotations

import unittest

from protocol_inspector import checksum_is_valid, internet_checksum, tcp_checksum_ipv4


class InternetChecksumTests(unittest.TestCase):
    def test_known_even_length_vector(self) -> None:
        self.assertEqual(internet_checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)

    def test_odd_length_is_padded_on_the_right(self) -> None:
        self.assertEqual(internet_checksum(bytes.fromhex("010203")), 0xFBFD)

    def test_checksum_field_makes_message_valid(self) -> None:
        payload = bytes.fromhex("4500002c1234400040060000c000020ac6336414")
        checksum = internet_checksum(payload)
        completed = payload[:10] + checksum.to_bytes(2, "big") + payload[12:]
        self.assertTrue(checksum_is_valid(completed))

    def test_tcp_pseudo_header_is_part_of_the_checksum(self) -> None:
        segment = bytes.fromhex("c00001bb01020304000000006002faf000000000020405b4")
        checksum = tcp_checksum_ipv4("192.0.2.10", "198.51.100.20", segment)
        completed = segment[:16] + checksum.to_bytes(2, "big") + segment[18:]
        self.assertEqual(
            tcp_checksum_ipv4("192.0.2.10", "198.51.100.20", completed),
            0,
        )
        self.assertNotEqual(
            tcp_checksum_ipv4("192.0.2.11", "198.51.100.20", completed),
            0,
        )


if __name__ == "__main__":
    unittest.main()
