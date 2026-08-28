"""Verify the currently implemented command-checker contracts."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from command_checker.model import SpecificationError
from command_checker.specification import load_cases
ROOT = Path(__file__).resolve().parents[1]

class CommandCheckerTests(unittest.TestCase):

    def write_cases(self, directory: Path, payload: object) -> Path:
        path = directory / 'cases.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    def test_load_cases_validates_and_resolves_relative_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / 'work'
            work.mkdir()
            path = self.write_cases(root, [{'name': 'contract', 'args': ['a', 'b'], 'timeout': 0.5, 'cwd': 'work', 'env': {'B': '2', 'A': '1'}, 'output_limit': 100}])
            cases = load_cases(path)
            self.assertEqual(cases[0].cwd, work.resolve())
            self.assertEqual(cases[0].env, (('A', '1'), ('B', '2')))
            self.write_cases(root, [{'name': 'x', 'unknown': True}])
            with self.assertRaises(SpecificationError):
                load_cases(path)
if __name__ == '__main__':
    unittest.main()
