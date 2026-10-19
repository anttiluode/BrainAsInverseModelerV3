import importlib
import importlib.util
import unittest
import numpy as np
from scipy.linalg import expm

from emitted_state.cable import Cable, make_cable


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('emitted_state.gate_p'),
                             'return-probe experiment is not implemented')
        self.p = importlib.import_module('emitted_state.gate_p')

    def test_exact_probe_matches_independent_augmented_matrix_exponential(self):
        cable = Cable(np.array([0.05, 0.02]),
                      np.array([[0.02, -0.01], [-0.01, 0.015]]), [1])
        states = np.array([[0.3, -0.4], [0.2, 0.8]])
        traces = self.p.interrogate(states, cable, steps=5, dt_ms=0.7,
                                   gain=0.75, voltage_scale_mv=1., pulse_na=0.01)
        for i, state in enumerate(states):
            leak = cable.conductance.sum(axis=1)
            added = 0.75 * leak * np.tanh(state)
            added[0] = 0.
            operator = cable.conductance + np.diag(added)
            augmented = np.zeros((3, 3))
            augmented[:2, :2] = -operator / cable.capacitance[:, None]
            augmented[0, 2] = 1. / cable.capacitance[0]
            full = expm(0.7 * augmented)
            value = state.copy()
            expected = []
            for t in range(5):
                value = full[:2, :2] @ value + full[:2, 2] * (0.01 if t == 0 else 0.)
                expected.append(value[0])
            np.testing.assert_allclose(traces[i], expected, atol=2e-14, rtol=2e-13)

    def test_linear_echo_is_constant_but_state_sensitive_echo_is_not(self):
        cable = make_cable()
        states = np.zeros((2, 19))
        states[:, 0] = 0.2  # same initial soma; distinct unreported branch states
        states[0, 1:4] = 2.
        states[1, 4:7] = 2.
        echoes = []
        for gain in [0., 0.75]:
            wait = self.p.interrogate(states, cable, gain=gain, pulse_na=0.)
            ping = self.p.interrogate(states, cable, gain=gain, pulse_na=0.01)
            echoes.append(ping - wait)
        np.testing.assert_allclose(echoes[0][0], echoes[0][1], atol=1e-13)
        self.assertGreater(np.max(np.abs(echoes[1][0]-echoes[1][1])), 1e-7)

    def test_blackout_features_are_causal_and_targets_start_after_availability(self):
        protocol = self.p.ProbeProtocol(observe=100, discard=20)
        signal = np.sin(np.arange(100) / 8.)
        idx = self.p.query_indices(protocol)
        self.assertTrue(np.all(idx + 19 + 20 < 100))
        base, audit = self.p.probe_features(signal, idx, protocol)
        changed = signal.copy()
        cutoff = idx[2]
        changed[cutoff+1:] += 99.
        other, _ = self.p.probe_features(changed, idx[:3], protocol)
        for arm in self.p.ARM_KEYS:
            self.assertEqual(base[arm].shape, (len(idx), 19))
            np.testing.assert_allclose(base[arm][:3], other[arm], atol=1e-11)
        self.assertLess(audit['fixed_echo_range'], 1e-10)
        self.assertLess(audit['reset_trace_range'], 1e-10)
        self.assertGreater(audit['active_echo_range'], 1e-7)

    def test_invalid_physical_and_split_protocols_are_rejected(self):
        for kwargs in [{'gain': 1.}, {'voltage_scale_mv': 0.}, {'steps': 0}, {'dt_ms': -1.}]:
            with self.assertRaises(ValueError):
                self.p.interrogate(np.zeros((2, 19)), make_cable(), **kwargs)
        for kwargs in [{'train_seeds': (10,), 'test_seeds': (10,)},
                       {'probe_steps': 18}, {'observe': 40, 'discard': 20}]:
            with self.assertRaises(ValueError):
                self.p.query_indices(self.p.ProbeProtocol(**kwargs))

    def test_evidence_requires_same_trajectories_and_pulse_specific_improvement(self):
        def metric(values):
            return {'mean_nrmse': float(np.mean(values)),
                    'per_trajectory': [{'seed': i, 'nrmse': x} for i, x in enumerate(values)]}
        scores = {a: metric([1., 1., 1., 1.]) for a in self.p.ARM_KEYS}
        scores['active_ping'] = metric([.8, .8, .8, 1.1])
        controls = {'fixed_echo_range': 0., 'reset_trace_range': 0.,
                    'active_echo_range': .01, 'matched_soma_active_echo_difference': .01,
                    'matched_soma_fixed_echo_difference': 0.}
        negative = {'mean_nrmse': 1., 'mean_r2': 0.}
        self.assertTrue(self.p.evidence(scores, controls, negative)['access_passed'])
        scores['active_wait'] = metric([.7, .7, .7, .7])
        self.assertFalse(self.p.evidence(scores, controls, negative)['access_passed'])
        scores['active_wait'] = metric([1., 1., 1., 1.])
        scores['fixed_wait'] = metric([1., .7, 1., 1.])
        self.assertFalse(self.p.evidence(scores, controls, negative)['access_passed'])
        scores['fixed_wait'] = metric([1., 1., 1., 1.])
        self.assertFalse(self.p.evidence(scores, controls,
                         {'mean_nrmse': .8, 'mean_r2': .2})['access_passed'])

    def test_reduced_run_has_finite_metrics_and_shared_row_accounting(self):
        runner = importlib.import_module('scripts.run_gate_p')
        protocol = self.p.ProbeProtocol(train_seeds=(10, 11), test_seeds=(100, 101),
                                       burn=50, observe=240, discard=60,
                                       sample_stride=8, noise_levels=(0.,))
        receipt = runner.run_experiment(protocol)
        self.assertEqual(set(receipt['conditions']), {'noise_0'})
        self.assertEqual(receipt['timing']['target_offset'], 39)
        self.assertEqual(receipt['normalization']['noise_0']['fit_seeds'], [10, 11])
        for result in receipt['conditions']['noise_0']['arms'].values():
            self.assertTrue(np.isfinite(result['mean_nrmse']))
            self.assertEqual(len(result['per_trajectory']), 2)
        self.assertFalse(receipt['claim_boundary']['counterfactual_echo_is_primary_feature'])
        self.assertIn('access_passed', receipt['primary_evidence'])

    def test_smoke_cli_cannot_overwrite_full_receipt_by_default(self):
        runner = importlib.import_module('scripts.run_gate_p')
        self.assertTrue(hasattr(runner, 'parse_args'), 'CLI output selection must be inspectable')
        full = runner.parse_args([])
        quick = runner.parse_args(['--quick'])
        self.assertNotEqual(full.output, quick.output)
        self.assertNotIn('results', quick.output.parts)
        explicit = runner.parse_args(['--quick', '--output', '/tmp/custom-probe.json'])
        self.assertEqual(str(explicit.output), '/tmp/custom-probe.json')


if __name__ == '__main__':
    unittest.main()
