import copy
import importlib
import importlib.util
import unittest


class GatePComparisonTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.compare_gate_p_receipts'),
                             'Gate P receipt comparison is not implemented')
        self.compare = importlib.import_module('scripts.compare_gate_p_receipts').compare_scientific
        self.receipt = dict(source_sha256={'encoder': 'abc'}, runtime={'python': 'a'},
                            timing={'target_offset': 39},
                            conditions={'noise_0': {'score': .5}},
                            primary_evidence={'access_passed': False})

    def test_runtime_is_ignored_but_metrics_timing_source_and_verdict_are_checked(self):
        other = copy.deepcopy(self.receipt)
        other['runtime']['python'] = 'b'
        self.assertTrue(self.compare(self.receipt, other)[0])
        for key, field, value in [('source_sha256', 'encoder', 'changed'),
                                   ('timing', 'target_offset', 20),
                                   ('primary_evidence', 'access_passed', True)]:
            other = copy.deepcopy(self.receipt)
            other[key][field] = value
            self.assertFalse(self.compare(self.receipt, other)[0])
        other = copy.deepcopy(self.receipt)
        other['conditions']['noise_0']['score'] += .001
        self.assertFalse(self.compare(self.receipt, other)[0])

    def test_removed_control_section_is_detected(self):
        other = copy.deepcopy(self.receipt)
        del other['timing']
        self.assertFalse(self.compare(self.receipt, other)[0])
