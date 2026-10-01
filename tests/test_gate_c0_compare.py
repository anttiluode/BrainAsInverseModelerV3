import base64
import copy
import hashlib
import json
import unittest
import zlib
from pathlib import Path

from scripts.compare_gate_c0_receipts import compare_scientific, normalize_scientific


WRAPPER = Path('results/gate_c0_receipt.json')


def _decoded_compact():
    wrapper = json.loads(WRAPPER.read_text(encoding='utf-8'))
    raw = zlib.decompress(base64.b64decode(wrapper['payload_zlib_base64']))
    assert hashlib.sha256(raw).hexdigest() == wrapper['canonical_sha256']
    return json.loads(raw)


def _verbose_from_compact(compact):
    """Independent test-side expansion of the frozen schema-2 packing."""
    out = copy.deepcopy(compact)
    arm_order = out.pop('arm_order')
    horizon_order = out.pop('horizon_order')
    exclusion_order = out.pop('event_exclusion_order')
    out['schema_version'] = 1

    event_counts = {}
    for noise_key, packed_rows in out['event_counts'].items():
        event_counts[noise_key] = {}
        for row in packed_rows:
            (seed, detected, valid, table_events, exclusions, scored,
             waveform, soma_norm, digest) = row
            event_counts[noise_key][str(seed)] = {
                'detected_spikes': detected,
                'valid_waveforms': valid,
                'table_events': table_events,
                'exclusions': dict(zip(exclusion_order, exclusions, strict=True)),
                'scored': dict(zip(horizon_order, scored, strict=True)),
                'waveform_features': {
                    'count': waveform[0],
                    'mean': waveform[1],
                    'std': waveform[2],
                    'min': waveform[3],
                    'max': waveform[4],
                },
                'soma_normalization': {'mean': soma_norm[0], 'scale': soma_norm[1]},
                'event_identity_sha256': digest,
            }
    out['event_counts'] = event_counts

    conditions = {}
    for noise_key, packed in out['conditions'].items():
        conditions[noise_key] = {}
        for horizon_key in horizon_order:
            arms = {}
            for arm, arm_row in zip(arm_order, packed['horizons'][horizon_key], strict=True):
                mean_nrmse, mean_r2, trajectories = arm_row
                arms[arm] = {
                    'mean_nrmse': mean_nrmse,
                    'mean_r2': mean_r2,
                    'per_trajectory': [
                        {
                            'seed': row[0], 'nrmse': row[1], 'r2': row[2],
                            'event_identity_sha256': row[3], 'events': row[4],
                        }
                        for row in trajectories
                    ],
                }
            conditions[noise_key][horizon_key] = {
                'training_observed_mean': packed['training_observed_mean'],
                'training_observed_scale': packed['training_observed_scale'],
                'timing_normalization': copy.deepcopy(packed['timing_normalization']),
                'residualization_provenance': copy.deepcopy(packed['residualization_provenance']),
                'arms': arms,
            }
    out['conditions'] = conditions

    negative = out['negative_control']
    negative['per_trajectory'] = [
        {'seed': row[0], 'nrmse': row[1], 'r2': row[2], 'events': row[3]}
        for row in negative['per_trajectory']
    ]
    return out


class GateC0ReceiptCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = json.loads(WRAPPER.read_text(encoding='utf-8'))
        cls.compact = _decoded_compact()
        cls.verbose = _verbose_from_compact(cls.compact)

    def test_wrapper_compact_and_verbose_compare_equal(self):
        for candidate in (self.compact, self.verbose):
            ok, message = compare_scientific(self.wrapper, candidate)
            self.assertTrue(ok, message)

    def test_runtime_metadata_is_ignored(self):
        changed = copy.deepcopy(self.verbose)
        changed['runtime'] = {'python': 'different', 'numpy': 'different', 'scipy': 'different'}
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertTrue(ok, message)

    def test_changed_forecast_metric_is_detected(self):
        changed = copy.deepcopy(self.compact)
        changed['conditions']['noise_0']['horizons']['horizon_20'][1][0] += 1e-3
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertFalse(ok)
        self.assertIn('timing_real_waveform', message)

    def test_changed_event_count_is_detected(self):
        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][1] += 1
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertFalse(ok)
        self.assertIn('detected_spikes', message)

    def test_changed_exclusion_count_is_detected(self):
        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][4][0] += 1
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertFalse(ok)
        self.assertIn('boundary', message)

    def test_changed_event_identity_is_detected(self):
        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][-1] = '0' * 64
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertFalse(ok)
        self.assertIn('event_identity_sha256', message)

    def test_portable_mode_ignores_event_identity_digests(self):
        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][-1] = '0' * 64
        changed['conditions']['noise_0']['horizons']['horizon_1'][0][2][0][3] = '1' * 64
        ok, message = compare_scientific(self.wrapper, changed, portable=True)
        self.assertTrue(ok, message)

    def test_portable_mode_still_detects_scientific_changes(self):
        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][-1] = '0' * 64
        changed['conditions']['noise_0']['horizons']['horizon_20'][1][0] += 1e-3
        ok, message = compare_scientific(self.wrapper, changed, portable=True)
        self.assertFalse(ok)
        self.assertIn('timing_real_waveform', message)

        changed = copy.deepcopy(self.compact)
        changed['event_counts']['noise_0'][0][-1] = '0' * 64
        source = next(iter(changed['source_sha256']))
        changed['source_sha256'][source] = '0' * 64
        ok, message = compare_scientific(self.wrapper, changed, portable=True)
        self.assertFalse(ok)
        self.assertIn('source_sha256', message)

    def test_changed_evidence_boolean_is_detected(self):
        changed = copy.deepcopy(self.compact)
        changed['primary_evidence']['c0_a']['passed'] = False
        ok, message = compare_scientific(self.wrapper, changed)
        self.assertFalse(ok)
        self.assertIn('primary_evidence', message)

    def test_wrapper_hash_is_verified(self):
        broken = copy.deepcopy(self.wrapper)
        broken['canonical_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'canonical SHA-256'):
            normalize_scientific(broken)


if __name__ == '__main__':
    unittest.main()
