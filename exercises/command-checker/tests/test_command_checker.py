"""Verify the currently implemented command-checker contracts."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from command_checker.model import Case, SpecificationError
from command_checker.process import run_case
from command_checker.specification import load_cases
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).with_name('fixture_program.py')

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

    def test_run_case_preserves_arguments_streams_environment_and_status(self) -> None:
        case = Case(name='channels', args=('channels',), stdout='out', stderr='err', returncode=7, env=(('OUT', 'out'), ('ERR', 'err'), ('CODE', '7')))
        result = run_case(case, (sys.executable, str(FIXTURE)))
        self.assertTrue(result.passed)
        self.assertEqual(result.returncode, 7)

    def test_timeout_and_output_limit_are_distinct_lifecycle_failures(self) -> None:
        timeout_result = run_case(Case(name='timeout', args=('sleep', '2'), timeout=0.1), (sys.executable, str(FIXTURE)))
        self.assertFalse(timeout_result.passed)
        self.assertTrue(timeout_result.timed_out)
        self.assertIn('timeout:', timeout_result.failures[0])
        output_result = run_case(Case(name='limit', args=('flood', 'stdout', '8192'), output_limit=1024), (sys.executable, str(FIXTURE)))
        self.assertFalse(output_result.passed)
        self.assertEqual(output_result.exceeded_stream, 'stdout')
        self.assertEqual(len(output_result.stdout.encode()), 1024)

    @unittest.skipUnless(os.name == 'posix', 'process-group lifecycle requires POSIX')
    def test_timeout_terminates_spawned_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pid_file = Path(temporary) / 'child.pid'
            result = run_case(Case(name='group-timeout', args=('spawn-child',), timeout=2.0, env=(('CHILD_PID_FILE', str(pid_file)),)), (sys.executable, str(FIXTURE)))
            self.assertTrue(result.timed_out)
            self.assertTrue(pid_file.exists())
if __name__ == '__main__':
    unittest.main()
