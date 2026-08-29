from pathlib import Path
import unittest

import replication_reconnect


class ImplementationBoundaryTest(unittest.TestCase):
    def test_public_package_boundary_is_importable(self) -> None:
        self.assertTrue(callable(replication_reconnect.run_scenario))

    def test_current_engine_stage_has_no_future_markers(self) -> None:
        source = (Path(__file__).parents[1] / "src/replication_reconnect/engine.py").read_text()
        self.assertIn('[Implementation 2]', source)
        self.assertIn('[Implementation 2-1]', source)
        self.assertIn('[Implementation 2-2]', source)
        self.assertNotIn('[Implementation 3]', source)


if __name__ == "__main__":
    unittest.main()
