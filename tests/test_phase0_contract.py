import unittest
from pathlib import Path

from tools.check_phase0 import EXPECTED_PACKAGES, validate


class Phase0ContractTests(unittest.TestCase):
    def test_repository_baseline_is_complete(self) -> None:
        metrics, errors = validate(Path(__file__).resolve().parents[1])
        self.assertEqual([], errors)
        self.assertEqual(len(EXPECTED_PACKAGES), metrics["published_packages"])
        self.assertGreater(metrics["source_lines"], 0)

    def test_root_source_layout_is_importable(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src" / "nova_agent" / "__init__.py"
        self.assertTrue(source.is_file())


if __name__ == "__main__":
    unittest.main()
