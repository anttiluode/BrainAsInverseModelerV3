#!/usr/bin/env python3
"""Run the frozen Gate A emitted-state forecasting experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy

from emitted_state.cable import make_cable
from emitted_state.gate_a import (
    ARM_KEYS,
    Protocol,
    feature_bank,
    fit_forecasters,
    observed_x,
    r2_score,
    scored_indices,
    world_for_seed,
)
from emitted_state.readout import QuadraticReadout, normalized_rmse


V2_SOURCE_COMMIT = "795be2c7e8c4ba25112983fdc9ac2ad00ca232d0"
SOURCE_FILES = (
    "emitted_state/cable.py",
    "emitted_state/world.py",
    "emitted_state/readout.py",
    "emitted_state/gate_a.py",
    "scripts/run_gate_a.py",
)


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    return value


def _hashes():
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def _worlds(protocol: Protocol):
    seeds = tuple(protocol.train_seeds) + tuple(protocol.test_seeds)
    return {seed: world_for_seed(seed, protocol) for seed in seeds}


def _feature_caches(observed_by_seed, seeds, mean, scale, protocol):
    cable = make_cable(diverse=True)
    return {
        seed: feature_bank((observed_by_seed[seed] - mean) / scale, cable, protocol)
        for seed in seeds
    }


def _fit_for_horizon(train_banks, observed_train, protocol, horizon):
    idx = scored_indices(protocol.observe, protocol.discard, protocol.sample_stride, horizon)
    features = {
        arm: np.concatenate([train_banks[seed][arm][idx] for seed in protocol.train_seeds], axis=0)
        for arm in ARM_KEYS
    }
    targets = np.concatenate([observed_train[seed][idx + horizon] for seed in protocol.train_seeds])
    return fit_forecasters(features, targets, protocol.ridge_factor), idx


def _evaluate_horizon(models, test_banks, worlds, protocol, horizon, scale):
    idx = scored_indices(protocol.observe, protocol.discard, protocol.sample_stride, horizon)
    per_arm = {arm: [] for arm in ARM_KEYS}
    for seed in protocol.test_seeds:
        truth = worlds[seed][idx + horizon, 0]
        for arm in ARM_KEYS:
            pred = models[arm].predict(test_banks[seed][arm][idx])[:, 0]
            per_arm[arm].append({
                "seed": int(seed),
                "nrmse": normalized_rmse(truth, pred, scale),
                "r2": r2_score(truth, pred),
            })
    return {
        "sample_count_per_trajectory": int(idx.size),
        "arms": {
            arm: {
                "mean_nrmse": float(np.mean([row["nrmse"] for row in rows])),
                "mean_r2": float(np.mean([row["r2"] for row in rows])),
                "per_trajectory": rows,
            }
            for arm, rows in per_arm.items()
        },
    }


def _negative_control(zero_train_banks, zero_test_banks, protocol):
    horizon = 20
    idx = scored_indices(protocol.observe, protocol.discard, protocol.sample_stride, horizon)
    train_labels = {}
    for seed in protocol.train_seeds:
        rng = np.random.default_rng(500000 + int(seed))
        train_labels[seed] = rng.normal(size=protocol.observe)
    train_target = np.concatenate([train_labels[seed][idx + horizon] for seed in protocol.train_seeds])
    target_mean = float(train_target.mean())
    target_scale = float(train_target.std())
    if target_scale <= 0:
        raise RuntimeError("negative-control training labels unexpectedly degenerate")
    x_train = np.concatenate([zero_train_banks[seed]["soma_history"][idx] for seed in protocol.train_seeds], axis=0)
    model = QuadraticReadout(protocol.ridge_factor).fit(x_train, (train_target - target_mean) / target_scale)

    rows = []
    for seed in protocol.test_seeds:
        rng = np.random.default_rng(500000 + int(seed))
        labels = rng.normal(size=protocol.observe)
        truth = (labels[idx + horizon] - target_mean) / target_scale
        pred = model.predict(zero_test_banks[seed]["soma_history"][idx])[:, 0]
        rows.append({
            "seed": int(seed),
            "nrmse": normalized_rmse(truth, pred, 1.0),
            "r2": r2_score(truth, pred),
        })
    return {
        "description": "Independent Gaussian future label decoded from zero-noise soma history; evaluation-only probe.",
        "label_seed_formula": "500000 + trajectory_seed",
        "horizon": horizon,
        "features": "soma_history",
        "mean_nrmse": float(np.mean([row["nrmse"] for row in rows])),
        "mean_r2": float(np.mean([row["r2"] for row in rows])),
        "per_trajectory": rows,
    }


def _primary_evidence(conditions, protocol):
    primary = conditions["noise_0"]["horizon_20"]["arms"]
    soma = primary["soma_history"]
    instant = primary["instantaneous_soma"]
    present = primary["present_input"]
    instant_by_seed = {row["seed"]: row for row in instant["per_trajectory"]}
    present_by_seed = {row["seed"]: row for row in present["per_trajectory"]}
    wins = []
    for row in soma["per_trajectory"]:
        seed = row["seed"]
        if row["nrmse"] < instant_by_seed[seed]["nrmse"] and row["nrmse"] < present_by_seed[seed]["nrmse"]:
            wins.append(seed)
    mean_beats_both = soma["mean_nrmse"] < instant["mean_nrmse"] and soma["mean_nrmse"] < present["mean_nrmse"]
    required_wins = 3
    return {
        "condition": "noise=0, horizon=20",
        "rule": "soma_history mean NRMSE < instantaneous_soma and present_input, with improvement over both on >=3/4 held-out trajectories",
        "soma_history_mean_nrmse": soma["mean_nrmse"],
        "instantaneous_soma_mean_nrmse": instant["mean_nrmse"],
        "present_input_mean_nrmse": present["mean_nrmse"],
        "mean_beats_both": bool(mean_beats_both),
        "trajectory_win_seeds": wins,
        "trajectory_wins": len(wins),
        "required_trajectory_wins": required_wins,
        "test_trajectory_count": len(protocol.test_seeds),
        "passed": bool(mean_beats_both and len(wins) >= required_wins),
    }


def run_experiment(protocol: Protocol | None = None):
    protocol = Protocol() if protocol is None else protocol
    worlds = _worlds(protocol)
    clean_train_x = np.concatenate([worlds[seed][:, 0] for seed in protocol.train_seeds])
    clean_x_scale = float(clean_train_x.std())
    if clean_x_scale <= 0:
        raise RuntimeError("clean training x is degenerate")

    conditions = {}
    zero_train_banks = None
    zero_test_banks = None

    for noise_level in protocol.noise_levels:
        observed_train = {
            seed: observed_x(worlds[seed], seed, noise_level, clean_x_scale)
            for seed in protocol.train_seeds
        }
        observed_test = {
            seed: observed_x(worlds[seed], seed, noise_level, clean_x_scale)
            for seed in protocol.test_seeds
        }
        training_observed = np.concatenate([observed_train[seed] for seed in protocol.train_seeds])
        observed_mean = float(training_observed.mean())
        observed_scale = float(training_observed.std())
        if observed_scale <= 0:
            raise RuntimeError("observed training x is degenerate")

        train_banks = _feature_caches(observed_train, protocol.train_seeds, observed_mean, observed_scale, protocol)
        test_banks = _feature_caches(observed_test, protocol.test_seeds, observed_mean, observed_scale, protocol)
        if noise_level == 0.0:
            zero_train_banks = train_banks
            zero_test_banks = test_banks

        noise_key = f"noise_{noise_level:g}"
        conditions[noise_key] = {}
        for horizon in protocol.horizons:
            models, _ = _fit_for_horizon(train_banks, observed_train, protocol, horizon)
            payload = _evaluate_horizon(models, test_banks, worlds, protocol, horizon, observed_scale)
            payload["training_observed_mean"] = observed_mean
            payload["training_observed_scale"] = observed_scale
            conditions[noise_key][f"horizon_{horizon}"] = payload

    if zero_train_banks is None or zero_test_banks is None:
        raise RuntimeError("protocol must include zero-noise condition for the predeclared primary and negative control")

    receipt = {
        "schema_version": 1,
        "experiment": "Gate A — emitted soma history to learned observational forecast",
        "v2_source_commit": V2_SOURCE_COMMIT,
        "protocol": asdict(protocol),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "source_sha256": _hashes(),
        "conditions": conditions,
        "primary_evidence": _primary_evidence(conditions, protocol),
        "negative_control": _negative_control(zero_train_banks, zero_test_banks, protocol),
        "claim_boundary": {
            "training_target": "later observed x only",
            "receiver_access": "soma voltage history only for the soma_history arm",
            "hidden_yz_used_for_forecast_fit": False,
            "internal_cable_state_is_privileged_comparison": True,
            "biological_learning_rule_claimed": False,
        },
    }
    return _plain(receipt)


def scientific_payload(receipt):
    return {
        "schema_version": receipt["schema_version"],
        "experiment": receipt["experiment"],
        "v2_source_commit": receipt["v2_source_commit"],
        "protocol": receipt["protocol"],
        "conditions": receipt["conditions"],
        "primary_evidence": receipt["primary_evidence"],
        "negative_control": receipt["negative_control"],
        "claim_boundary": receipt["claim_boundary"],
    }


def _quick_protocol():
    return Protocol(
        train_seeds=(10, 11),
        test_seeds=(100, 101),
        burn=80,
        observe=420,
        discard=80,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run a reduced deterministic smoke protocol.")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "gate_a_receipt.json")
    args = parser.parse_args()
    protocol = _quick_protocol() if args.quick else Protocol()
    receipt = run_experiment(protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    primary = receipt["primary_evidence"]
    print(f"Gate A passed: {primary['passed']}")
    print(f"Soma history NRMSE: {primary['soma_history_mean_nrmse']:.6f}")
    print(f"Instantaneous soma NRMSE: {primary['instantaneous_soma_mean_nrmse']:.6f}")
    print(f"Present input NRMSE: {primary['present_input_mean_nrmse']:.6f}")
    print(f"Trajectory wins: {primary['trajectory_wins']}/{primary['test_trajectory_count']}")
    print(f"Negative-control NRMSE: {receipt['negative_control']['mean_nrmse']:.6f}")
    print(f"Receipt: {args.output}")


if __name__ == "__main__":
    main()
