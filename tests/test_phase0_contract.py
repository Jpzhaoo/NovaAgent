import unittest
from pathlib import Path

from tools.check_phase0 import EXPECTED_PACKAGES, validate


class Phase0ContractTests(unittest.TestCase):
    def test_repository_baseline_is_complete(self) -> None:
        metrics, errors = validate(Path(__file__).resolve().parents[1])
        self.assertEqual([], errors)
        self.assertEqual(len(EXPECTED_PACKAGES), metrics["published_packages"])
        self.assertGreater(metrics["source_lines"], 0)


if __name__ == "__main__":
    unittest.main()

