import unittest
import numpy as np

from emitted_state.cable import Cable, make_cable
from emitted_state.readout import QuadraticReadout
from emitted_state.world import delay_features, lorenz


class CoreTests(unittest.TestCase):
    def test_single_rc_transition_matches_closed_form(self):
        cable = Cable(np.array([1.0]), np.array([[0.5]]), [0])
        f, h = cable.transition(2.0)
        self.assertAlmostEqual(f[0, 0], np.exp(-1.0), places=12)
        self.assertAlmostEqual(h[0, 0], (1.0 - np.exp(-1.0)) / 0.5, places=12)

    def test_passive_transition_contracts_voltage(self):
        cable = make_cable(diverse=True)
        f, _ = cable.transition(1.0)
        self.assertLess(np.max(np.abs(np.linalg.eigvals(f))), 1.0)

    def test_delay_features_are_causal_and_stride_two(self):
        signal = np.arange(8.0)
        features = delay_features(signal, size=3, stride=2)
        np.testing.assert_array_equal(features[:, 0], signal)
        np.testing.assert_array_equal(features[2:, 1], signal[:-2])
        np.testing.assert_array_equal(features[4:, 2], signal[:-4])
        np.testing.assert_array_equal(features[:2, 1], 0.0)
        np.testing.assert_array_equal(features[:4, 2], 0.0)

    def test_quadratic_readout_constant_column_stays_finite(self):
        x = np.column_stack([np.linspace(-1.0, 1.0, 20), np.ones(20)])
        y = 2.0 * x[:, 0] + 0.25
        model = QuadraticReadout(0.001).fit(x, y)
        pred = model.predict(x)
        self.assertTrue(np.all(np.isfinite(pred)))
        self.assertLess(np.sqrt(np.mean((pred[:, 0] - y) ** 2)), 0.02)

    def test_lorenz_is_deterministic(self):
        initial = np.array([1.0, -2.0, 20.0])
        a = lorenz(initial, 12, dt=0.01)
        b = lorenz(initial, 12, dt=0.01)
        np.testing.assert_allclose(a, b, rtol=0.0, atol=0.0)
        self.assertTrue(np.all(np.isfinite(a)))


if __name__ == '__main__':
    unittest.main()
