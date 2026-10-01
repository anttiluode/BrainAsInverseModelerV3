#!/usr/bin/env python3
"""Run the frozen Gate C0 state-bearing spike experiment."""

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

from emitted_state.emitter import HHParams, extract_waveform_events, simulate_hh_piecewise
from emitted_state.gate_a import observed_x, r2_score, world_for_seed
from emitted_state.gate_c0 import (
    ALL_ARMS,
    PRIMARY_ARMS,
    ArmSet,
    GateC0Protocol,
    arm_features,
    build_event_table,
    eligible_rows,
    emitter_current,
    event_identity_sha256,
    fit_forecasters,
    fit_timing_stats,
    passive_state_for_observed,
    residualize_waveforms,
)
from emitted_state.readout import QuadraticReadout, normalized_rmse


SOURCE_FILES = (
    "emitted_state/emitter.py",
    "emitted_state/gate_c0.py",
    "emitted_state/cable.py",
    "emitted_state/world.py",
    "emitted_state/readout.py",
    "scripts/run_gate_c0.py",
)


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    return value


def _hashes():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES}


def _waveform_summary(waveform):
    w = np.asarray(waveform, dtype=float)
    if w.shape[0] == 0:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    return {
        "count": int(w.shape[0]),
        "mean": w.mean(axis=0).tolist(),
        "std": w.std(axis=0).tolist(),
        "min": w.min(axis=0).tolist(),
        "max": w.max(axis=0).tolist(),
    }


def _prepare_noise_condition(worlds, noise_level, clean_x_scale, protocol):
    seeds = tuple(protocol.train_seeds) + tuple(protocol.test_seeds)
    observed = {seed: observed_x(worlds[seed], seed, noise_level, clean_x_scale) for seed in seeds}
    train_observed = np.concatenate([observed[s] for s in protocol.train_seeds])
    observed_mean = float(train_observed.mean())
    observed_scale = float(train_observed.std())
    if observed_scale <= 0:
        raise RuntimeError("observed training x is degenerate")
    passive = {seed: passive_state_for_observed(observed[seed], observed_mean, observed_scale, protocol) for seed in seeds}
    train_soma = np.concatenate([passive[s][:, 0] for s in protocol.train_seeds])
    soma_mean = float(train_soma.mean())
    soma_scale = float(train_soma.std())
    if soma_scale <= 0:
        raise RuntimeError("training soma is degenerate")
    emissions = {}
    tables = {}
    counts = {}
    for seed in seeds:
        current = emitter_current(passive[seed][:, 0], soma_mean, soma_scale, protocol)
        time_ms, voltage_mv = simulate_hh_piecewise(current, interval_ms=protocol.cable_dt_ms, dt_ms=protocol.emitter_dt_ms)
        emission = extract_waveform_events(time_ms, voltage_mv, pre_ms=protocol.waveform_pre_ms, post_ms=protocol.waveform_post_ms)
        table = build_event_table(seed, observed[seed], passive[seed], emission, protocol)
        emissions[seed] = emission
        tables[seed] = table
        counts[seed] = {
            "detected_spikes": int(emission.onset_times_ms.size),
            "valid_waveforms": int(len(emission.events)),
            "table_events": int(table.event_ids.size),
            "exclusions": {
                "boundary": int(table.exclusions.get("boundary", 0)),
                "overlap": int(table.exclusions.get("overlap", 0)),
                "feature_undefined": int(table.exclusions.get("undefined_feature", 0)),
                "missing_eight_isi": int(table.exclusions.get("missing_eight_isi", 0)),
                "availability_boundary": int(table.exclusions.get("availability_boundary", 0)),
            },
            "scored": {f"horizon_{h}": int(eligible_rows(table, h, protocol.observe).size) for h in protocol.horizons},
            "waveform_features": _waveform_summary(table.waveform),
            "soma_normalization": {"mean": soma_mean, "scale": soma_scale},
        }
    return {"observed": observed, "passive": passive, "emissions": emissions, "tables": tables, "observed_mean": observed_mean, "observed_scale": observed_scale, "soma_mean": soma_mean, "soma_scale": soma_scale, "counts": counts}


def _subset_identity(armset: ArmSet, rows: np.ndarray) -> str:
    return event_identity_sha256(ArmSet(armset.event_ids[rows], armset.onset_ms[rows], armset.availability_ms[rows], {}))


def _fit_and_evaluate(bundle, worlds, protocol, horizon):
    train_tables = {s: bundle["tables"][s] for s in protocol.train_seeds}
    test_tables = {s: bundle["tables"][s] for s in protocol.test_seeds}
    timing_mean, timing_scale = fit_timing_stats(train_tables)
    train_resid, test_resid, provenance = residualize_waveforms(train_tables, test_tables, timing_mean, timing_scale, protocol.ridge_factor)
    train_arms = {s: arm_features(train_tables[s], timing_mean, timing_scale, train_resid[s], protocol) for s in protocol.train_seeds}
    test_arms = {s: arm_features(test_tables[s], timing_mean, timing_scale, test_resid[s], protocol) for s in protocol.test_seeds}
    train_rows = {s: eligible_rows(train_tables[s], horizon, protocol.observe) for s in protocol.train_seeds}
    test_rows = {s: eligible_rows(test_tables[s], horizon, protocol.observe) for s in protocol.test_seeds}
    train_features = {arm: np.concatenate([train_arms[s].features[arm][train_rows[s]] for s in protocol.train_seeds], axis=0) for arm in ALL_ARMS}
    train_targets = np.concatenate([bundle["observed"][s][train_tables[s].availability_index[train_rows[s]] + horizon] for s in protocol.train_seeds])
    models = fit_forecasters(train_features, train_targets, protocol.ridge_factor)
    per_arm = {arm: [] for arm in ALL_ARMS}
    identities_by_seed = {}
    for seed in protocol.test_seeds:
        rows = test_rows[seed]
        identity = _subset_identity(test_arms[seed], rows)
        identities_by_seed[seed] = identity
        truth = worlds[seed][test_tables[seed].availability_index[rows] + horizon, 0]
        for arm in ALL_ARMS:
            pred = models[arm].predict(test_arms[seed].features[arm][rows])[:, 0]
            per_arm[arm].append({"seed": int(seed), "nrmse": normalized_rmse(truth, pred, bundle["observed_scale"]), "r2": r2_score(truth, pred), "event_identity_sha256": identity, "events": int(rows.size)})
    for seed, identity in identities_by_seed.items():
        observed_identities = {arm: next(r for r in per_arm[arm] if r["seed"] == seed)["event_identity_sha256"] for arm in PRIMARY_ARMS}
        if len(set(observed_identities.values())) != 1 or next(iter(observed_identities.values())) != identity:
            raise RuntimeError("primary arms do not share event identity")
    return {"training_observed_mean": bundle["observed_mean"], "training_observed_scale": bundle["observed_scale"], "timing_normalization": {"mean": timing_mean, "scale": timing_scale}, "residualization_provenance": provenance, "arms": {arm: {"mean_nrmse": float(np.mean([r["nrmse"] for r in rows])), "mean_r2": float(np.mean([r["r2"] for r in rows])), "per_trajectory": rows} for arm, rows in per_arm.items()}}, train_arms, test_arms


def _negative_control_passes(mean_nrmse: float, mean_r2: float) -> bool:
    return bool(mean_nrmse >= 0.90 and mean_r2 <= 0.05)


def _negative_control(bundle, protocol, train_arms, test_arms):
    horizon = 20
    train_tables = {s: bundle["tables"][s] for s in protocol.train_seeds}
    test_tables = {s: bundle["tables"][s] for s in protocol.test_seeds}
    train_rows = {s: eligible_rows(train_tables[s], horizon, protocol.observe) for s in protocol.train_seeds}
    test_rows = {s: eligible_rows(test_tables[s], horizon, protocol.observe) for s in protocol.test_seeds}
    train_labels = {}
    for seed in protocol.train_seeds:
        rng = np.random.default_rng(protocol.negative_label_seed_base + int(seed))
        train_labels[seed] = rng.normal(size=train_rows[seed].size)
    y = np.concatenate([train_labels[s] for s in protocol.train_seeds])
    mean = float(y.mean())
    scale = float(y.std())
    if scale <= 0:
        raise RuntimeError("negative-control labels unexpectedly degenerate")
    x = np.concatenate([train_arms[s].features["timing_real_waveform"][train_rows[s]] for s in protocol.train_seeds])
    model = QuadraticReadout(protocol.ridge_factor).fit(x, (y - mean) / scale)
    rows = []
    for seed in protocol.test_seeds:
        rng = np.random.default_rng(protocol.negative_label_seed_base + int(seed))
        labels = rng.normal(size=test_rows[seed].size)
        truth = (labels - mean) / scale
        pred = model.predict(test_arms[seed].features["timing_real_waveform"][test_rows[seed]])[:, 0]
        rows.append({"seed": int(seed), "nrmse": normalized_rmse(truth, pred, 1.0), "r2": r2_score(truth, pred), "events": int(test_rows[seed].size)})
    mean_nrmse = float(np.mean([r["nrmse"] for r in rows]))
    mean_r2 = float(np.mean([r["r2"] for r in rows]))
    return {"description": "Independent Gaussian event labels decoded from timing+real-waveform features; evaluation-only probe.", "label_seed_formula": f"{protocol.negative_label_seed_base} + trajectory_seed", "horizon": horizon, "mean_nrmse": mean_nrmse, "mean_r2": mean_r2, "per_trajectory": rows, "chance_rule": "mean NRMSE >= 0.90 and mean R2 <= 0.05", "passed_chance_check": _negative_control_passes(mean_nrmse, mean_r2)}


def _summary_by_seed(summary):
    return {int(r["seed"]): r for r in summary["per_trajectory"]}


def _primary_evidence_from_arms(arms, negative_control_passed):
    real = arms["timing_real_waveform"]
    timing = arms["timing_only"]
    shuffled = arms["timing_shuffled_waveform"]
    residual = arms["timing_residual_waveform"]
    real_by = _summary_by_seed(real)
    timing_by = _summary_by_seed(timing)
    shuffled_by = _summary_by_seed(shuffled)
    residual_by = _summary_by_seed(residual)
    seeds = sorted(real_by)
    joint = [s for s in seeds if real_by[s]["nrmse"] < timing_by[s]["nrmse"] and real_by[s]["nrmse"] < shuffled_by[s]["nrmse"]]
    residual_wins = [s for s in seeds if residual_by[s]["nrmse"] < timing_by[s]["nrmse"]]
    c0a_criterion = bool(real["mean_nrmse"] < timing["mean_nrmse"] and real["mean_nrmse"] < shuffled["mean_nrmse"] and len(joint) >= 3)
    c0b_criterion = bool(residual["mean_nrmse"] < timing["mean_nrmse"] and len(residual_wins) >= 3)
    return {"c0_a": {"rule": "real waveform mean NRMSE beats timing-only and shuffled, and beats both on the same >=3/4 held-out trajectories", "criterion_passed": c0a_criterion, "joint_win_seeds": joint, "joint_wins": len(joint), "claim_valid": bool(negative_control_passed), "passed": bool(c0a_criterion and negative_control_passed)}, "c0_b": {"rule": "residual waveform mean NRMSE beats timing-only and wins on >=3/4 held-out trajectories", "criterion_passed": c0b_criterion, "win_seeds": residual_wins, "wins": len(residual_wins), "claim_valid": bool(negative_control_passed), "passed": bool(c0b_criterion and negative_control_passed)}}


def run_experiment(protocol: GateC0Protocol | None = None) -> dict:
    protocol = GateC0Protocol() if protocol is None else protocol
    seeds = tuple(protocol.train_seeds) + tuple(protocol.test_seeds)
    worlds = {seed: world_for_seed(seed, protocol) for seed in seeds}
    clean_train_x = np.concatenate([worlds[s][:, 0] for s in protocol.train_seeds])
    clean_x_scale = float(clean_train_x.std())
    if clean_x_scale <= 0:
        raise RuntimeError("clean training x is degenerate")
    bundles = {}
    event_counts = {}
    for noise_level in protocol.noise_levels:
        key = f"noise_{noise_level:g}"
        bundle = _prepare_noise_condition(worlds, noise_level, clean_x_scale, protocol)
        bundles[key] = bundle
        event_counts[key] = bundle["counts"]
    primary_bundle = bundles.get("noise_0")
    if primary_bundle is None:
        raise RuntimeError("protocol must contain the zero-noise primary condition")
    subthreshold = []
    for seed in seeds:
        count = int(eligible_rows(primary_bundle["tables"][seed], 20, protocol.observe).size)
        if count < protocol.min_primary_events:
            subthreshold.append({"seed": int(seed), "scored_events": count, "required": int(protocol.min_primary_events)})
    emitter_payload = {"model": "classical Hodgkin-Huxley one-compartment emitter", "hh_params": asdict(HHParams()), "dt_ms": protocol.emitter_dt_ms, "drive": "emitter_bias + emitter_gain*tanh(z_s/emitter_tanh_scale)", "one_way": True, "spike_threshold_mv": 0.0, "waveform_window_ms": [-protocol.waveform_pre_ms, protocol.waveform_post_ms], "waveform_features": ["peak_amplitude", "half_height_width", "peak_sharpness", "repolarization_slope"]}
    if subthreshold:
        receipt = {"schema_version": 1, "experiment": "Gate C0 — state-bearing spike waveform beyond timing", "protocol": asdict(protocol), "emitter": emitter_payload, "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}, "source_sha256": _hashes(), "event_counts": event_counts, "conditions": {}, "primary_evidence": {"status": "not_viable", "condition": "noise=0, horizon=20", "subthreshold_trajectories": subthreshold, "c0_a": {"criterion_passed": False, "claim_valid": False, "passed": False}, "c0_b": {"criterion_passed": False, "claim_valid": False, "passed": False}}, "negative_control": {"status": "not_run", "passed_chance_check": None}, "claim_boundary": {"gate_a_unchanged": True, "same_spikes_compared_across_primary_arms": True, "synapse_or_postsynaptic_neuron_implemented": False, "biological_waveform_coding_claimed": False}}
        return _plain(receipt)
    conditions = {}
    arm_cache = {}
    for noise_key, bundle in bundles.items():
        conditions[noise_key] = {}
        arm_cache[noise_key] = {}
        for horizon in protocol.horizons:
            payload, train_arms, test_arms = _fit_and_evaluate(bundle, worlds, protocol, horizon)
            conditions[noise_key][f"horizon_{horizon}"] = payload
            if horizon == 20:
                arm_cache[noise_key] = {"train": train_arms, "test": test_arms}
        for seed in seeds:
            table = bundle["tables"][seed]
            rows = eligible_rows(table, 20, protocol.observe)
            armset = (arm_cache[noise_key]["train"] if seed in protocol.train_seeds else arm_cache[noise_key]["test"])[seed]
            event_counts[noise_key][seed]["event_identity_sha256"] = _subset_identity(armset, rows)
    negative = _negative_control(bundles["noise_0"], protocol, arm_cache["noise_0"]["train"], arm_cache["noise_0"]["test"])
    evidence = _primary_evidence_from_arms(conditions["noise_0"]["horizon_20"]["arms"], negative["passed_chance_check"])
    primary = {"status": "complete", "condition": "noise=0, horizon=20", **evidence}
    receipt = {"schema_version": 1, "experiment": "Gate C0 — state-bearing spike waveform beyond timing", "protocol": asdict(protocol), "emitter": emitter_payload, "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}, "source_sha256": _hashes(), "event_counts": event_counts, "conditions": conditions, "primary_evidence": primary, "negative_control": negative, "claim_boundary": {"forecast_training_target": "later observed x only", "same_spikes_compared_across_primary_arms": True, "hidden_yz_used_for_forecast_fit": False, "internal_cable_state_is_privileged_comparison": True, "synapse_or_postsynaptic_neuron_implemented": False, "biological_waveform_coding_claimed": False}}
    return _plain(receipt)


def scientific_payload(receipt: dict) -> dict:
    keys = ("schema_version", "experiment", "protocol", "emitter", "source_sha256", "event_counts", "conditions", "primary_evidence", "negative_control", "claim_boundary")
    return {key: receipt[key] for key in keys}


def _quick_protocol():
    return GateC0Protocol(train_seeds=(10, 11), test_seeds=(100, 101), burn=80, observe=500, min_primary_events=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "gate_c0_receipt.json")
    args = parser.parse_args()
    protocol = _quick_protocol() if args.quick else GateC0Protocol()
    receipt = run_experiment(protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    primary = receipt["primary_evidence"]
    print(f"Gate C0 status: {primary['status']}")
    if primary["status"] == "complete":
        print(f"C0-A passed: {primary['c0_a']['passed']}")
        print(f"C0-B passed: {primary['c0_b']['passed']}")
        print(f"Negative control chance check: {receipt['negative_control']['passed_chance_check']}")
    else:
        print(f"Subthreshold trajectories: {len(primary['subthreshold_trajectories'])}")
    print(f"Receipt: {args.output}")


if __name__ == "__main__":
    main()
