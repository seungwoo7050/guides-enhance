from pathlib import Path
import unittest

import trust_abuse


class ImplementationBoundaryTest(unittest.TestCase):
    def test_public_package_boundary_is_importable(self) -> None:
        self.assertTrue(callable(trust_abuse.run_scenario))

    def test_current_engine_stage_has_no_future_markers(self) -> None:
        source = (Path(__file__).parents[1] / "src/trust_abuse/engine.py").read_text()
        self.assertIn('[Implementation 3]', source)
        self.assertIn('[Implementation 4]', source)
        self.assertNotIn('[Implementation 5]', source)


if __name__ == "__main__":
    unittest.main()
