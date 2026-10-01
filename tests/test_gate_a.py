import inspect
import unittest

import numpy as np

from emitted_state.cable import make_cable
from emitted_state.gate_a import (
    ARM_KEYS,
    Protocol,
    build_training_rows,
    feature_bank,
    fit_forecasters,
    observed_x,
    scored_indices,
    world_for_seed,
)


class GateAFeatureTests(unittest.TestCase):
    def setUp(self):
        self.protocol = Protocol()
        self.cable = make_cable(diverse=True)

    def test_feature_bank_has_six_width_19_arms_and_causal_soma_history(self):
        signal = np.linspace(-1.0, 1.0, 80)
        bank = feature_bank(signal, self.cable, self.protocol)
        self.assertEqual(tuple(bank), ARM_KEYS)
        for features in bank.values():
            self.assertEqual(features.shape, (80, 19))
            self.assertTrue(np.all(np.isfinite(features)))

        soma = bank["internal_cable_state"][:, 0]
        np.testing.assert_allclose(bank["soma_history"][:, 0], soma)
        np.testing.assert_allclose(bank["soma_history"][2:, 1], soma[:-2])
        np.testing.assert_allclose(bank["soma_history"][4:, 2], soma[:-4])
        np.testing.assert_allclose(bank["instantaneous_soma"][:, 0], soma)
        np.testing.assert_allclose(bank["instantaneous_soma"][:, 1:], 0.0)

    def test_scored_indices_exclude_targets_beyond_observation(self):
        idx = scored_indices(observe=40, discard=5, stride=4, horizon=5)
        np.testing.assert_array_equal(idx, np.arange(5, 35, 4))
        self.assertTrue(np.all(idx + 5 < 40))

    def test_future_change_does_not_change_earlier_features(self):
        signal = np.sin(np.linspace(0.0, 3.0, 120))
        changed = signal.copy()
        cutoff = 59
        changed[cutoff + 1:] += 1000.0
        base = feature_bank(signal, self.cable, self.protocol)
        perturbed = feature_bank(changed, self.cable, self.protocol)
        for arm in ARM_KEYS:
            np.testing.assert_allclose(base[arm][:cutoff + 1], perturbed[arm][:cutoff + 1], rtol=0.0, atol=1e-12)

    def test_observed_x_is_deterministic_and_noise_zero_is_clean(self):
        state = world_for_seed(10, Protocol(burn=20, observe=50))
        clean = state[:, 0]
        zero = observed_x(state, 10, 0.0, clean.std())
        noisy_a = observed_x(state, 10, 0.02, clean.std())
        noisy_b = observed_x(state, 10, 0.02, clean.std())
        np.testing.assert_allclose(zero, clean)
        np.testing.assert_allclose(noisy_a, noisy_b)
        self.assertGreater(np.max(np.abs(noisy_a - clean)), 0.0)


class GateATrainingTests(unittest.TestCase):
    def test_fit_interface_has_no_hidden_or_clean_truth_parameter(self):
        parameters = set(inspect.signature(fit_forecasters).parameters)
        self.assertEqual(parameters, {"features_by_arm", "targets", "ridge_factor"})
        self.assertNotIn("hidden", parameters)
        self.assertNotIn("clean", parameters)

    def test_build_training_rows_aligns_future_observed_target(self):
        protocol = Protocol(burn=0, observe=80, discard=10, sample_stride=4)
        observed = {10: np.linspace(-3.0, 4.0, protocol.observe)}
        mean = float(observed[10].mean())
        scale = float(observed[10].std())
        features, targets, indices = build_training_rows(
            observed_by_seed=observed,
            seeds=(10,),
            observed_mean=mean,
            observed_scale=scale,
            horizon=5,
            protocol=protocol,
        )
        expected_idx = scored_indices(80, 10, 4, 5)
        np.testing.assert_array_equal(indices[10], expected_idx)
        np.testing.assert_allclose(targets, observed[10][expected_idx + 5])
        for arm in ARM_KEYS:
            self.assertEqual(features[arm].shape, (len(expected_idx), 19))

    def test_constant_degenerate_features_fit_finitely(self):
        rows = 40
        features = {arm: np.zeros((rows, 19)) for arm in ARM_KEYS}
        targets = np.full(rows, 2.5)
        models = fit_forecasters(features, targets, ridge_factor=0.001)
        for model in models.values():
            pred = model.predict(np.zeros((3, 19)))
            self.assertTrue(np.all(np.isfinite(pred)))
            np.testing.assert_allclose(pred[:, 0], 2.5, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
