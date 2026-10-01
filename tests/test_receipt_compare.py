import copy
import json
import unittest
from pathlib import Path

from scripts.compare_receipts import normalize_scientific, compare_scientific


class ReceiptCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compact = json.loads(Path('results/gate_a_receipt.json').read_text())
        cls.verbose = normalize_scientific(cls.compact)

    def test_compact_and_verbose_scientific_payloads_compare_equal(self):
        ok, message = compare_scientific(self.compact, self.verbose, rtol=1e-9, atol=1e-10)
        self.assertTrue(ok, message)

    def test_runtime_metadata_is_ignored(self):
        verbose = copy.deepcopy(self.verbose)
        verbose['runtime'] = {'python': 'different'}
        ok, message = compare_scientific(self.compact, verbose, rtol=1e-9, atol=1e-10)
        self.assertTrue(ok, message)

    def test_changed_scientific_metric_is_detected(self):
        verbose = copy.deepcopy(self.verbose)
        verbose['conditions']['noise_0']['horizon_20']['arms']['soma_history']['mean_nrmse'] += 1e-3
        ok, message = compare_scientific(self.compact, verbose, rtol=1e-9, atol=1e-10)
        self.assertFalse(ok)
        self.assertIn('soma_history', message)


if __name__ == '__main__':
    unittest.main()
