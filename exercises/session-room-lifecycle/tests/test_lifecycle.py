from pathlib import Path
import unittest

import session_room_lifecycle


class ImplementationBoundaryTest(unittest.TestCase):
    def test_public_package_boundary_is_importable(self) -> None:
        self.assertTrue(callable(session_room_lifecycle.run_scenario))

    def test_current_engine_stage_has_no_future_markers(self) -> None:
        source = (Path(__file__).parents[1] / "src/session_room_lifecycle/engine.py").read_text()
        self.assertIn('[Implementation 2]', source)
        self.assertNotIn('[Implementation 3]', source)


if __name__ == "__main__":
    unittest.main()
