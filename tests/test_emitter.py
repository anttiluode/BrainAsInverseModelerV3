import unittest
import numpy as np

from emitted_state.emitter import HHParams, extract_waveform_events, hh_rates, simulate_hh_piecewise, steady_state_gates


class EmitterPhysicsTests(unittest.TestCase):
    def test_hh_singular_rates_and_steady_state_are_finite(self):
        self.assertAlmostEqual(hh_rates(-40.0)[0], 1.0, places=12)
        self.assertAlmostEqual(hh_rates(-55.0)[4], 0.1, places=12)
        rates = hh_rates(-65.0)
        self.assertTrue(np.all(np.isfinite(rates)))
        gates = steady_state_gates(-65.0)
        expected = (rates[0]/(rates[0]+rates[1]), rates[2]/(rates[2]+rates[3]), rates[4]/(rates[4]+rates[5]))
        np.testing.assert_allclose(gates, expected, rtol=0.0, atol=1e-15)
        self.assertTrue(all(0.0 <= x <= 1.0 for x in gates))

    def test_constant_current_simulation_is_deterministic_and_spikes(self):
        current = np.full(100, 10.0)
        ta, va = simulate_hh_piecewise(current)
        tb, vb = simulate_hh_piecewise(current)
        np.testing.assert_array_equal(ta, tb)
        np.testing.assert_array_equal(va, vb)
        self.assertEqual(ta.shape, va.shape)
        self.assertTrue(np.all(np.isfinite(va)))
        self.assertTrue(np.any((va[:-1] < 0.0) & (va[1:] >= 0.0)))
        _, rest = simulate_hh_piecewise(np.zeros(20))
        self.assertTrue(np.all(np.isfinite(rest)))


class WaveformExtractionTests(unittest.TestCase):
    @staticmethod
    def synthetic_single_spike():
        t = np.arange(-2.0, 6.0001, 0.025)
        v = np.full_like(t, -65.0)
        mask = (t > -0.5) & (t <= 0.0)
        v[mask] = -65.0 + 130.0 * (t[mask] + 0.5)
        mask = (t > 0.0) & (t <= 1.0)
        v[mask] = 35.0 * t[mask]
        mask = (t > 1.0) & (t <= 3.0)
        v[mask] = 35.0 - 50.0 * (t[mask] - 1.0)
        return t, v

    def test_piecewise_linear_waveform_features_match_declared_rules(self):
        t, v = self.synthetic_single_spike()
        result = extract_waveform_events(t, v)
        self.assertEqual(len(result.events), 1)
        np.testing.assert_allclose(result.events[0].features, np.array([100.0, 2.1153846153846154, 4.25, -50.0]), rtol=0.0, atol=1e-9)
        self.assertAlmostEqual(result.events[0].onset_ms, 0.0, places=12)
        self.assertAlmostEqual(result.events[0].availability_ms, 4.0, places=12)

    def test_boundary_and_overlap_exclusions_are_counted(self):
        t = np.arange(0.0, 8.0001, 0.025)
        v = np.full_like(t, -65.0)
        onset = 0.5
        mask = (t > onset-0.2) & (t <= onset)
        v[mask] = -65.0 + 325.0*(t[mask]-(onset-0.2))
        mask = (t > onset) & (t <= onset+0.5)
        v[mask] = 30.0 - 190.0*(t[mask]-onset)
        result = extract_waveform_events(t, v)
        self.assertGreaterEqual(result.exclusions.get("boundary",0),1)

        t2 = np.arange(-2.0,10.0001,0.025)
        v2 = np.full_like(t2,-65.0)
        for onset in (0.0,3.0):
            mask=(t2>onset-0.2)&(t2<=onset)
            v2[mask]=-65.0+325.0*(t2[mask]-(onset-0.2))
            mask=(t2>onset)&(t2<=onset+0.5)
            v2[mask]=30.0-190.0*(t2[mask]-onset)
        result2=extract_waveform_events(t2,v2)
        self.assertGreaterEqual(result2.exclusions.get("overlap",0),1)
        self.assertGreaterEqual(len(result2.onset_times_ms),2)

    def test_undefined_waveform_feature_is_excluded(self):
        t=np.arange(-2.0,6.0001,0.025); v=np.full_like(t,-65.0)
        mask=(t>-0.5)&(t<=0.0); v[mask]=-65.0+130.0*(t[mask]+0.5); v[t>0.0]=35.0
        result=extract_waveform_events(t,v)
        self.assertEqual(len(result.events),0)
        self.assertEqual(result.exclusions.get("undefined_feature",0),1)

    def test_valid_event_indexes_full_detected_onset_array(self):
        t,v=self.synthetic_single_spike(); result=extract_waveform_events(t,v)
        self.assertEqual(result.events[0].spike_index,0)
        self.assertEqual(result.onset_times_ms.shape,(1,))


if __name__ == "__main__":
    unittest.main()
