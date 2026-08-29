from pathlib import Path
import unittest

import replication_reconnect


class ImplementationBoundaryTest(unittest.TestCase):
    def test_public_package_boundary_is_importable(self) -> None:
        self.assertTrue(callable(replication_reconnect.run_scenario))

    def test_current_engine_stage_has_no_future_markers(self) -> None:
        source = (Path(__file__).parents[1] / "src/replication_reconnect/engine.py").read_text()
        self.assertIn('[Implementation 3]', source)
        self.assertIn('[Implementation 4]', source)
        self.assertIn('[Implementation 4-1]', source)
        self.assertNotIn('[Implementation 5]', source)


if __name__ == "__main__":
    unittest.main()
