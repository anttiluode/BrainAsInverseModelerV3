import unittest

import numpy as np

from emitted_state.gate_c0 import ALL_ARMS, GateC0Protocol
from scripts.run_gate_c0 import (
    _negative_control_passes,
    _primary_evidence_from_arms,
    run_experiment,
)


class GateC0ReceiptTests(unittest.TestCase):
    def test_reduced_receipt_is_complete_and_finite(self):
        protocol = GateC0Protocol(
            train_seeds=(10, 11),
            test_seeds=(100, 101),
            burn=80,
            observe=500,
            min_primary_events=5,
        )
        receipt = run_experiment(protocol)
        for key in (
            "protocol", "emitter", "event_counts", "conditions", "primary_evidence",
            "negative_control", "claim_boundary", "source_sha256", "runtime",
        ):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["primary_evidence"]["status"], "complete")
        self.assertEqual(set(receipt["conditions"]), {"noise_0", "noise_0.02"})
        for noise_payload in receipt["conditions"].values():
            self.assertEqual(set(noise_payload), {"horizon_1", "horizon_5", "horizon_20"})
            for horizon_payload in noise_payload.values():
                self.assertEqual(set(horizon_payload["arms"]), set(ALL_ARMS))
                for arm in ALL_ARMS:
                    summary = horizon_payload["arms"][arm]
                    self.assertTrue(np.isfinite(summary["mean_nrmse"]))
                    self.assertTrue(np.isfinite(summary["mean_r2"]))
                    self.assertEqual(len(summary["per_trajectory"]), 2)
        self.assertIn("python", receipt["runtime"])
        self.assertIn("numpy", receipt["runtime"])
        self.assertIn("scipy", receipt["runtime"])

    def test_impossible_threshold_returns_not_viable_receipt(self):
        protocol = GateC0Protocol(
            train_seeds=(10, 11),
            test_seeds=(100, 101),
            burn=40,
            observe=240,
            min_primary_events=10_000,
        )
        receipt = run_experiment(protocol)
        primary = receipt["primary_evidence"]
        self.assertEqual(primary["status"], "not_viable")
        self.assertGreaterEqual(len(primary["subthreshold_trajectories"]), 4)
        self.assertEqual(receipt["protocol"]["emitter_bias"], 10.0)
        self.assertEqual(receipt["protocol"]["emitter_gain"], 4.0)
        self.assertIn("event_counts", receipt)

    def test_c0a_requires_same_three_trajectories_to_beat_both_controls(self):
        arms = self._primary_metrics(
            real=[0.5, 0.5, 0.5, 0.5],
            timing=[0.6, 0.6, 0.4, 0.4],
            shuffled=[0.4, 0.4, 0.6, 0.6],
            residual=[0.7, 0.7, 0.7, 0.7],
        )
        evidence = _primary_evidence_from_arms(arms, negative_control_passed=True)
        self.assertFalse(evidence["c0_a"]["criterion_passed"])

        arms = self._primary_metrics(
            real=[0.4, 0.4, 0.4, 0.7],
            timing=[0.5, 0.5, 0.5, 0.6],
            shuffled=[0.6, 0.6, 0.6, 0.65],
            residual=[0.4, 0.4, 0.4, 0.7],
        )
        evidence = _primary_evidence_from_arms(arms, negative_control_passed=True)
        self.assertTrue(evidence["c0_a"]["criterion_passed"])
        self.assertEqual(evidence["c0_a"]["joint_win_seeds"], [100, 101, 102])
        self.assertTrue(evidence["c0_b"]["criterion_passed"])

    def test_negative_control_threshold_and_veto(self):
        self.assertTrue(_negative_control_passes(0.95, 0.0))
        self.assertFalse(_negative_control_passes(0.89, 0.0))
        self.assertFalse(_negative_control_passes(0.95, 0.051))
        arms = self._primary_metrics(
            real=[0.4, 0.4, 0.4, 0.4],
            timing=[0.6, 0.6, 0.6, 0.6],
            shuffled=[0.7, 0.7, 0.7, 0.7],
            residual=[0.4, 0.4, 0.4, 0.4],
        )
        evidence = _primary_evidence_from_arms(arms, negative_control_passed=False)
        self.assertTrue(evidence["c0_a"]["criterion_passed"])
        self.assertTrue(evidence["c0_b"]["criterion_passed"])
        self.assertFalse(evidence["c0_a"]["claim_valid"])
        self.assertFalse(evidence["c0_b"]["claim_valid"])
        self.assertFalse(evidence["c0_a"]["passed"])
        self.assertFalse(evidence["c0_b"]["passed"])

    @staticmethod
    def _primary_metrics(real, timing, shuffled, residual):
        seeds = [100, 101, 102, 103]
        def summary(values):
            return {
                "mean_nrmse": float(np.mean(values)),
                "mean_r2": 0.0,
                "per_trajectory": [
                    {"seed": seed, "nrmse": float(value), "r2": 0.0}
                    for seed, value in zip(seeds, values)
                ],
            }
        return {
            "timing_real_waveform": summary(real),
            "timing_only": summary(timing),
            "timing_shuffled_waveform": summary(shuffled),
            "timing_residual_waveform": summary(residual),
        }


if __name__ == "__main__":
    unittest.main()
