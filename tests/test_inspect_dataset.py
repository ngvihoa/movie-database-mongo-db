import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validation" / "inspect_dataset.py"
SPEC = importlib.util.spec_from_file_location("inspect_dataset", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DatasetInspectionTest(unittest.TestCase):
    def test_current_dataset_integrity(self):
        report = MODULE.inspect(Path(__file__).parents[1] / "dataset")
        self.assertEqual(report["ratingsSmall"]["rows"], 100004)
        self.assertEqual(report["ratingsSmall"]["users"], 671)
        self.assertEqual(report["ratingsSmall"]["joinedRows"], 99810)
        self.assertEqual(report["ratingsSmall"]["rejectedRows"], 194)
        self.assertEqual(report["ratingsSmall"]["duplicateUserMoviePairs"], 0)
        self.assertEqual(report["links"]["duplicateMovieLensIds"], 0)


if __name__ == "__main__":
    unittest.main()
