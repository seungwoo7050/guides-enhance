from __future__ import annotations

import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / "fixtures"


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "protocol_inspector", *args],
            cwd=PROJECT,
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_decode_outputs_layered_json(self) -> None:
        result = self.run_cli("decode", str(FIXTURES / "syn-frame.hex"))
        self.assertEqual(result.returncode, 0, result.stderr)
        decoded = json.loads(result.stdout)
        self.assertEqual(decoded["ethernet"]["ethertype"], 0x0800)
        self.assertEqual(decoded["ipv4"]["ttl"], 64)
        self.assertEqual(decoded["tcp"]["flags"], ["SYN"])

    def test_route_uses_longest_prefix(self) -> None:
        result = self.run_cli(
            "route",
            "--table",
            str(FIXTURES / "routes.json"),
            "--destination",
            "10.20.30.8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        route = json.loads(result.stdout)
        self.assertEqual(route["interface"], "lan0")
        self.assertEqual(route["network"], "10.20.30.0/24")

    def test_tcp_trace_starts_from_closed(self) -> None:
        result = self.run_cli(
            "tcp",
            "--role",
            "client",
            "--events",
            "active-open,receive-syn-ack",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["CLOSED", "SYN-SENT", "ESTABLISHED"])

    def test_pcap_reports_record_lengths(self) -> None:
        raw = (
            b"\xd4\xc3\xb2\xa1"
            + struct.pack("<HHIIII", 2, 4, 0, 0, 65535, 1)
            + struct.pack("<IIII", 3, 500, 4, 8)
            + b"abcd"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.pcap"
            path.write_bytes(raw)
            result = self.run_cli("pcap", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        capture = json.loads(result.stdout)
        self.assertEqual(capture["link_type"], 1)
        self.assertEqual(capture["packets"][0]["captured_length"], 4)
        self.assertEqual(capture["packets"][0]["original_length"], 8)


if __name__ == "__main__":
    unittest.main()
