"""Gate A: causal forecasting from emitted soma-voltage history."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cable import Cable, make_cable
from .readout import QuadraticReadout, normalized_rmse
from .world import delay_features, exponential_features, lorenz


ARM_KEYS = (
    "present_input",
    "raw_input_delays",
    "exponential_input_traces",
    "internal_cable_state",
    "instantaneous_soma",
    "soma_history",
)


@dataclass(frozen=True)
class Protocol:
    train_seeds: tuple[int, ...] = (10, 11, 12, 13, 14, 15)
    test_seeds: tuple[int, ...] = (100, 101, 102, 103)
    burn: int = 1000
    observe: int = 4000
    discard: int = 500
    sample_stride: int = 4
    history_size: int = 19
    history_stride: int = 2
    horizons: tuple[int, ...] = (1, 5, 20)
    noise_levels: tuple[float, ...] = (0.0, 0.02)
    world_dt: float = 0.01
    cable_dt_ms: float = 1.0
    drive_na: float = 0.01
    ridge_factor: float = 0.001


def initial_for_seed(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.array([
        rng.uniform(-15.0, 15.0),
        rng.uniform(-15.0, 15.0),
        rng.uniform(5.0, 35.0),
    ])


def world_for_seed(seed: int, protocol: Protocol) -> np.ndarray:
    return lorenz(initial_for_seed(seed), protocol.burn + protocol.observe, protocol.world_dt)[protocol.burn:]


def observed_x(state: np.ndarray, seed: int, noise_level: float, clean_x_scale: float) -> np.ndarray:
    state = np.asarray(state, dtype=float)
    if state.ndim != 2 or state.shape[1] < 1 or not np.all(np.isfinite(state)):
        raise ValueError("state must be a finite matrix with x in column 0")
    if not np.isfinite(noise_level) or noise_level < 0:
        raise ValueError("noise_level must be finite and nonnegative")
    if not np.isfinite(clean_x_scale) or clean_x_scale <= 0:
        raise ValueError("clean_x_scale must be finite and positive")
    x = state[:, 0].copy()
    if noise_level == 0.0:
        return x
    rng = np.random.default_rng(200000 + int(seed) + int(noise_level * 10000))
    return x + noise_level * clean_x_scale * rng.normal(size=x.size)


def feature_bank(observed_x_norm: np.ndarray, cable: Cable, protocol: Protocol) -> dict[str, np.ndarray]:
    signal = np.asarray(observed_x_norm, dtype=float)
    if signal.ndim != 1 or not np.all(np.isfinite(signal)):
        raise ValueError("observed_x_norm must be a finite vector")
    currents = protocol.drive_na * signal[:, None] * np.ones((1, len(cable.ports)))
    internal = cable.encode(currents, protocol.cable_dt_ms)
    soma = internal[:, 0]

    present = np.zeros((signal.size, protocol.history_size), dtype=float)
    present[:, 0] = signal
    instant_soma = np.zeros_like(present)
    instant_soma[:, 0] = soma

    bank = {
        "present_input": present,
        "raw_input_delays": delay_features(signal, protocol.history_size, protocol.history_stride),
        "exponential_input_traces": exponential_features(signal, protocol.cable_dt_ms, protocol.history_size),
        "internal_cable_state": internal,
        "instantaneous_soma": instant_soma,
        "soma_history": delay_features(soma, protocol.history_size, protocol.history_stride),
    }
    for key in ARM_KEYS:
        if bank[key].shape != (signal.size, protocol.history_size):
            raise ValueError(f"arm {key} does not have width {protocol.history_size}")
    return {key: bank[key] for key in ARM_KEYS}


def scored_indices(observe: int, discard: int, stride: int, horizon: int) -> np.ndarray:
    if not all(isinstance(x, (int, np.integer)) for x in (observe, discard, stride, horizon)):
        raise ValueError("observe/discard/stride/horizon must be integers")
    if observe <= 0 or discard < 0 or stride <= 0 or horizon <= 0 or discard >= observe:
        raise ValueError("invalid scoring schedule")
    return np.arange(discard, observe - horizon, stride, dtype=int)


def build_training_rows(
    observed_by_seed: dict[int, np.ndarray],
    seeds: tuple[int, ...],
    observed_mean: float,
    observed_scale: float,
    horizon: int,
    protocol: Protocol,
):
    if not np.isfinite(observed_mean) or not np.isfinite(observed_scale) or observed_scale <= 0:
        raise ValueError("observed normalization must be finite with positive scale")
    cable = make_cable(diverse=True)
    parts = {arm: [] for arm in ARM_KEYS}
    target_parts = []
    indices_by_seed: dict[int, np.ndarray] = {}
    for seed in seeds:
        observed = np.asarray(observed_by_seed[seed], dtype=float)
        if observed.shape != (protocol.observe,) or not np.all(np.isfinite(observed)):
            raise ValueError("each observed trajectory must match protocol.observe")
        normalized = (observed - observed_mean) / observed_scale
        bank = feature_bank(normalized, cable, protocol)
        idx = scored_indices(protocol.observe, protocol.discard, protocol.sample_stride, horizon)
        indices_by_seed[seed] = idx
        for arm in ARM_KEYS:
            parts[arm].append(bank[arm][idx])
        target_parts.append(observed[idx + horizon])
    features = {arm: np.concatenate(parts[arm], axis=0) for arm in ARM_KEYS}
    targets = np.concatenate(target_parts, axis=0)
    return features, targets, indices_by_seed


def fit_forecasters(features_by_arm, targets, ridge_factor):
    targets = np.asarray(targets, dtype=float)
    if targets.ndim != 1 or targets.size == 0 or not np.all(np.isfinite(targets)):
        raise ValueError("targets must be a finite nonempty vector")
    models = {}
    for arm in ARM_KEYS:
        features = np.asarray(features_by_arm[arm], dtype=float)
        if features.ndim != 2 or features.shape[0] != targets.size or features.shape[1] != 19:
            raise ValueError("each feature arm must have shape (targets, 19)")
        models[arm] = QuadraticReadout(ridge_factor).fit(features, targets)
    return models


def r2_score(truth: np.ndarray, prediction: np.ndarray) -> float:
    truth = np.asarray(truth, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    denom = float(np.sum((truth - truth.mean()) ** 2))
    if denom <= 0:
        return 0.0
    return float(1.0 - np.sum((truth - prediction) ** 2) / denom)


def evaluate_forecasters(models, features_by_arm, clean_truth, scale):
    truth = np.asarray(clean_truth, dtype=float)
    result = {}
    for arm in ARM_KEYS:
        pred = models[arm].predict(features_by_arm[arm])[:, 0]
        result[arm] = {
            "nrmse": normalized_rmse(truth, pred, scale),
            "r2": r2_score(truth, pred),
        }
    return result
