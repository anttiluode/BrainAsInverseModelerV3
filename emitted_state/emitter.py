"""One-way Hodgkin-Huxley spike emitter and frozen waveform features for Gate C0."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class HHParams:
    c_m: float = 1.0
    g_na: float = 120.0
    e_na: float = 50.0
    g_k: float = 36.0
    e_k: float = -77.0
    g_l: float = 0.3
    e_l: float = -54.387


@dataclass(frozen=True)
class WaveformEvent:
    spike_index: int
    onset_ms: float
    availability_ms: float
    features: np.ndarray = field(repr=False)


@dataclass(frozen=True)
class EmissionResult:
    onset_times_ms: np.ndarray = field(repr=False)
    events: tuple[WaveformEvent, ...]
    exclusions: dict[str, int]


def _ratio_limit(numerator_scale: float, x: float, denominator_scale: float) -> float:
    """Return numerator_scale*x/(1-exp(-x/denominator_scale)) stably."""
    if abs(x) < 1e-10:
        return numerator_scale * denominator_scale
    return numerator_scale * x / (-np.expm1(-x / denominator_scale))


def hh_rates(v_mv: float) -> tuple[float, float, float, float, float, float]:
    v = float(v_mv)
    if not np.isfinite(v):
        raise ValueError("v_mv must be finite")
    alpha_m = _ratio_limit(0.1, v + 40.0, 10.0)
    beta_m = 4.0 * np.exp(-(v + 65.0) / 18.0)
    alpha_h = 0.07 * np.exp(-(v + 65.0) / 20.0)
    beta_h = 1.0 / (1.0 + np.exp(-(v + 35.0) / 10.0))
    alpha_n = _ratio_limit(0.01, v + 55.0, 10.0)
    beta_n = 0.125 * np.exp(-(v + 65.0) / 80.0)
    return tuple(float(x) for x in (alpha_m, beta_m, alpha_h, beta_h, alpha_n, beta_n))


def steady_state_gates(v_mv: float) -> tuple[float, float, float]:
    am, bm, ah, bh, an, bn = hh_rates(v_mv)
    return am / (am + bm), ah / (ah + bh), an / (an + bn)


def _derivative(state: np.ndarray, current: float, params: HHParams) -> np.ndarray:
    v, m, h, n = state
    am, bm, ah, bh, an, bn = hh_rates(v)
    i_na = params.g_na * (m**3) * h * (v - params.e_na)
    i_k = params.g_k * (n**4) * (v - params.e_k)
    i_l = params.g_l * (v - params.e_l)
    dv = (current - i_na - i_k - i_l) / params.c_m
    dm = am * (1.0 - m) - bm * m
    dh = ah * (1.0 - h) - bh * h
    dn = an * (1.0 - n) - bn * n
    return np.array([dv, dm, dh, dn], dtype=float)


def simulate_hh_piecewise(current_by_interval: np.ndarray, interval_ms: float = 1.0, dt_ms: float = 0.025, params: HHParams = HHParams()) -> tuple[np.ndarray, np.ndarray]:
    current = np.asarray(current_by_interval, dtype=float)
    if current.ndim != 1 or not np.all(np.isfinite(current)):
        raise ValueError("current_by_interval must be a finite vector")
    if not np.isfinite(interval_ms) or interval_ms <= 0 or not np.isfinite(dt_ms) or dt_ms <= 0:
        raise ValueError("interval_ms and dt_ms must be finite and positive")
    ratio = interval_ms / dt_ms
    substeps = int(round(ratio))
    if substeps <= 0 or abs(ratio - substeps) > 1e-12:
        raise ValueError("interval_ms / dt_ms must be a positive integer")
    total_steps = current.size * substeps
    times = np.arange(total_steps + 1, dtype=float) * dt_ms
    voltage = np.empty(total_steps + 1, dtype=float)
    m0, h0, n0 = steady_state_gates(-65.0)
    state = np.array([-65.0, m0, h0, n0], dtype=float)
    voltage[0] = state[0]
    out_idx = 0
    for i_emit in current:
        for _ in range(substeps):
            k1 = _derivative(state, float(i_emit), params)
            k2 = _derivative(state + 0.5 * dt_ms * k1, float(i_emit), params)
            k3 = _derivative(state + 0.5 * dt_ms * k2, float(i_emit), params)
            k4 = _derivative(state + dt_ms * k3, float(i_emit), params)
            state = state + (dt_ms / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            out_idx += 1
            voltage[out_idx] = state[0]
    if not np.all(np.isfinite(voltage)):
        raise FloatingPointError("HH simulation produced non-finite voltage")
    return times, voltage


def _interp(t: np.ndarray, v: np.ndarray, x: float) -> float:
    if x < t[0] or x > t[-1]:
        raise ValueError("interpolation request outside trace")
    return float(np.interp(x, t, v))


def _crossing_time(t0: float, v0: float, t1: float, v1: float, level: float) -> float:
    if v1 == v0:
        return float(t0)
    return float(t0 + (level - v0) * (t1 - t0) / (v1 - v0))


def _first_rising_crossing(t: np.ndarray, v: np.ndarray, level: float, lo: float, hi: float) -> float | None:
    mask = (t[:-1] >= lo) & (t[1:] <= hi + 1e-12)
    idx = np.flatnonzero(mask & (v[:-1] < level) & (v[1:] >= level))
    if idx.size == 0:
        return None
    i = int(idx[0])
    return _crossing_time(t[i], v[i], t[i + 1], v[i + 1], level)


def _first_falling_crossing(t: np.ndarray, v: np.ndarray, level: float, lo: float, hi: float) -> float | None:
    mask = (t[:-1] >= lo - 1e-12) & (t[1:] <= hi + 1e-12)
    idx = np.flatnonzero(mask & (v[:-1] >= level) & (v[1:] < level))
    if idx.size == 0:
        return None
    i = int(idx[0])
    return _crossing_time(t[i], v[i], t[i + 1], v[i + 1], level)


def _features_for_event(t: np.ndarray, v: np.ndarray, onset: float) -> np.ndarray | None:
    baseline_grid = t[(t >= onset - 1.0 - 1e-12) & (t <= onset - 0.5 + 1e-12)]
    if baseline_grid.size == 0:
        return None
    baseline = float(np.mean(np.interp(baseline_grid, t, v)))
    peak_mask = (t >= onset - 1e-12) & (t <= onset + 2.0 + 1e-12)
    peak_idx = np.flatnonzero(peak_mask)
    if peak_idx.size == 0:
        return None
    local_i = int(peak_idx[np.argmax(v[peak_idx])])
    t_peak = float(t[local_i])
    v_peak = float(v[local_i])
    amplitude = v_peak - baseline
    if not np.isfinite(amplitude) or amplitude <= 0:
        return None
    half = baseline + 0.5 * amplitude
    rising = _first_rising_crossing(t, v, half, onset - 1.0, t_peak)
    falling = _first_falling_crossing(t, v, half, t_peak, onset + 4.0)
    if rising is None or falling is None or falling <= rising:
        return None
    width = falling - rising
    if t_peak - 0.1 < t[0] or t_peak + 0.1 > t[-1]:
        return None
    sharpness = v_peak - 0.5 * (_interp(t, v, t_peak - 0.1) + _interp(t, v, t_peak + 0.1))
    lo = t_peak + 0.5
    hi = t_peak + 2.0
    slope_mask = (t >= lo - 1e-12) & (t <= hi + 1e-12)
    slope_t = t[slope_mask]
    slope_v = v[slope_mask]
    if slope_t.size < 2:
        return None
    centered = slope_t - slope_t.mean()
    denom = float(centered @ centered)
    if denom <= 0:
        return None
    slope = float(centered @ (slope_v - slope_v.mean()) / denom)
    features = np.array([amplitude, width, sharpness, slope], dtype=float)
    return features if np.all(np.isfinite(features)) else None


def extract_waveform_events(time_ms: np.ndarray, voltage_mv: np.ndarray, pre_ms: float = 1.0, post_ms: float = 4.0) -> EmissionResult:
    t = np.asarray(time_ms, dtype=float)
    v = np.asarray(voltage_mv, dtype=float)
    if t.ndim != 1 or v.ndim != 1 or t.shape != v.shape or t.size < 2:
        raise ValueError("time_ms and voltage_mv must be matching vectors")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(v)) or not np.all(np.diff(t) > 0):
        raise ValueError("trace must be finite with strictly increasing time")
    if pre_ms != 1.0 or post_ms != 4.0:
        raise ValueError("Gate C0 waveform window is frozen at [-1,+4] ms")
    crossing_indices = np.flatnonzero((v[:-1] < 0.0) & (v[1:] >= 0.0))
    onset_times = np.array([_crossing_time(t[i], v[i], t[i + 1], v[i + 1], 0.0) for i in crossing_indices], dtype=float)
    exclusions = {"boundary": 0, "overlap": 0, "undefined_feature": 0}
    events: list[WaveformEvent] = []
    for spike_index, onset in enumerate(onset_times):
        if onset - pre_ms < t[0] - 1e-12 or onset + post_ms > t[-1] + 1e-12:
            exclusions["boundary"] += 1
            continue
        if spike_index + 1 < onset_times.size and onset_times[spike_index + 1] <= onset + post_ms + 1e-12:
            exclusions["overlap"] += 1
            continue
        features = _features_for_event(t, v, float(onset))
        if features is None:
            exclusions["undefined_feature"] += 1
            continue
        events.append(WaveformEvent(spike_index, float(onset), float(onset + post_ms), features))
    return EmissionResult(onset_times, tuple(events), exclusions)
