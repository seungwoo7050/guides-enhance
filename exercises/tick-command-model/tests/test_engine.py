from pathlib import Path
import unittest

import tick_command_model


class ImplementationBoundaryTest(unittest.TestCase):
    def test_public_package_boundary_is_importable(self) -> None:
        self.assertTrue(callable(tick_command_model.run_scenario))

    def test_current_engine_stage_has_no_future_markers(self) -> None:
        source = (Path(__file__).parents[1] / "src/tick_command_model/engine.py").read_text()
        self.assertIn('[Implementation 6]', source)
        self.assertIn('[Implementation 6-1]', source)
        self.assertIn('[Implementation 6-2]', source)



if __name__ == "__main__":
    unittest.main()
