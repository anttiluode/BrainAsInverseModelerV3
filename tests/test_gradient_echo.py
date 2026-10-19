import importlib
import importlib.util
import unittest

import numpy as np

from emitted_state.cable import make_cable
from emitted_state.readout import QuadraticReadout


class GradientEchoTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('emitted_state.gradient_echo'),
                             'gradient/echo readouts are not implemented')
        self.m = importlib.import_module('emitted_state.gradient_echo')

    def test_temporal_slopes_are_invertible_coordinates_of_same_samples(self):
        trace = np.random.default_rng(12).normal(size=(13, 19))
        features = self.m.temporal_coordinates(trace)
        np.testing.assert_allclose(np.cumsum(features, axis=1), trace, atol=1e-14)
        np.testing.assert_array_equal(features[:, 0], trace[:, 0])
        for value in [np.zeros((3, 18)), np.full((2, 19), np.nan)]:
            with self.assertRaises(ValueError):
                self.m.temporal_coordinates(value)

    def test_spatial_current_coordinates_are_invertible_and_sum_proximal_flux(self):
        cable = make_cable()
        state = np.random.default_rng(8).normal(size=(10, 19))
        coordinates, matrix = self.m.edge_current_coordinates(state, cable)
        self.assertEqual(np.linalg.matrix_rank(matrix), 19)
        np.testing.assert_allclose(np.linalg.solve(matrix, coordinates.T).T, state, atol=1e-12)
        np.testing.assert_allclose(coordinates[:, 0], state[:, 0])
        edges = [(i, j) for i in range(19) for j in range(i+1, 19)
                 if cable.conductance[i, j] < 0]
        proximal = [k+1 for k, (i, j) in enumerate(edges) if i == 0]
        flux = sum(-cable.conductance[0, j]*(state[:, j]-state[:, 0]) for j in [1,4,7,10,13,16])
        np.testing.assert_allclose(coordinates[:, proximal].sum(axis=1), flux, atol=1e-14)

    def test_fixed_artifact_subtraction_cannot_change_standardized_predictions(self):
        rng = np.random.default_rng(91)
        x, test = rng.normal(size=(220, 19)), rng.normal(size=(35, 19))
        y = x[:, 1]*x[:, 3] + x[:, 5]
        artifact = np.linspace(.1, 100., 19)
        raw = QuadraticReadout().fit(x, y)
        calibrated = QuadraticReadout().fit(x-artifact, y)
        np.testing.assert_allclose(raw.predict(test), calibrated.predict(test-artifact), atol=1e-10)

    def test_features_are_causal_and_exact_echo_is_explicitly_diagnostic(self):
        p = self.m.GradientProtocol(burn=0, observe=160, discard=30)
        signal = np.sin(np.arange(160)/11.)
        idx = self.m.query_indices(p)[:4]
        bank, audit = self.m.features(signal, idx, p)
        changed = signal.copy()
        changed[idx[-1]+1:] += 40.
        other, _ = self.m.features(changed, idx, p)
        for arm in self.m.ARM_KEYS:
            self.assertEqual(bank[arm].shape, (4, 19))
            np.testing.assert_allclose(bank[arm], other[arm], atol=1e-12)
        np.testing.assert_allclose(bank['paired_echo_diagnostic'],
                                   (bank['raw_ping']-bank['raw_wait'])/p.pulse_na)
        self.assertEqual(audit['fixed_echo_range'],
                         float(np.max(np.ptp(bank['fixed_echo_diagnostic'],axis=0))))
        self.assertEqual(audit['active_echo_range'],
                         float(np.max(np.ptp(bank['paired_echo_diagnostic'],axis=0))))
        self.assertLess(audit['fixed_echo_range'], 1e-10)
        self.assertGreater(audit['active_echo_range'], 1e-7)

    def test_fresh_holdouts_and_target_clocks_are_fixed(self):
        p = self.m.GradientProtocol()
        self.assertEqual(p.test_seeds, (200,201,202,203))
        self.assertEqual(p.reused_test_seeds, (100,101,102,103))
        self.assertFalse(set(p.train_seeds)&set(p.test_seeds+p.reused_test_seeds))
        q = self.m.query_indices(p)
        np.testing.assert_array_equal(self.m.target_indices(q, 20, p), q+20)
        np.testing.assert_array_equal(self.m.target_indices(q, 39, p), q+39)
        with self.assertRaises(ValueError):
            self.m.target_indices(q, 19, p)

    def test_primary_requires_pulse_and_coordinate_benefit_on_same_fresh_seeds(self):
        def metric(values):
            return dict(mean_nrmse=float(np.mean(values)),
                        per_trajectory=[dict(seed=200+i,nrmse=v) for i,v in enumerate(values)])
        arms = {a: metric([1.,1.,1.,1.]) for a in self.m.ARM_KEYS}
        arms['gradient_ping'] = metric([.8,.8,.8,1.1])
        negative = dict(mean_nrmse=1., mean_r2=0.)
        controls = dict(calibrated_prediction_max_difference=0., fixed_echo_range=0.)
        self.assertTrue(self.m.primary_evidence(arms,negative,controls)['passed'])
        arms['gradient_wait'] = metric([.7,.7,.7,.7])
        self.assertFalse(self.m.primary_evidence(arms,negative,controls)['passed'])

    def test_reduced_receipt_retains_both_clocks_and_separates_fresh_and_reused(self):
        runner = importlib.import_module('scripts.run_gradient_echo')
        p = self.m.GradientProtocol(train_seeds=(10,11), test_seeds=(200,),
                                   reused_test_seeds=(100,),burn=50,observe=240,
                                   discard=60,sample_stride=8,noise_levels=(0.,))
        r = runner.run_experiment(p)
        self.assertEqual(r['timing']['availability_offset'],19)
        self.assertEqual(set(r['conditions']['noise_0']),{'target_20','target_39'})
        for condition in r['conditions']['noise_0'].values():
            for arm in self.m.ARM_KEYS:
                self.assertEqual(condition['fresh']['arms'][arm]['per_trajectory'][0]['seed'],200)
                self.assertEqual(condition['reused']['arms'][arm]['per_trajectory'][0]['seed'],100)
                self.assertTrue(np.isfinite(condition['fresh']['arms'][arm]['mean_nrmse']))
