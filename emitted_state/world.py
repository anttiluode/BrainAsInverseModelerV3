"""Synthetic hidden world and strictly causal temporal feature banks."""

import numpy as np


def _lorenz_derivative(state):
    x, y, z = state
    return np.array([10.0 * (y - x), x * (28.0 - z) - y, x * y - (8.0 / 3.0) * z])


def lorenz(initial, steps, dt=0.01):
    initial = np.asarray(initial, dtype=float)
    if initial.shape != (3,) or not np.all(np.isfinite(initial)):
        raise ValueError("initial must be a finite three-vector")
    if not isinstance(steps, (int, np.integer)) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    state = initial.copy()
    out = np.empty((int(steps), 3), dtype=float)
    for t in range(int(steps)):
        k1 = _lorenz_derivative(state)
        k2 = _lorenz_derivative(state + 0.5 * dt * k1)
        k3 = _lorenz_derivative(state + 0.5 * dt * k2)
        k4 = _lorenz_derivative(state + dt * k3)
        state = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        out[t] = state
    return out


def delay_features(signal, size=19, stride=2):
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1 or not np.all(np.isfinite(signal)):
        raise ValueError("signal must be a finite vector")
    if not isinstance(size, (int, np.integer)) or size <= 0:
        raise ValueError("size must be a positive integer")
    if not isinstance(stride, (int, np.integer)) or stride <= 0:
        raise ValueError("stride must be a positive integer")
    n = signal.size
    out = np.zeros((n, int(size)), dtype=float)
    for j in range(int(size)):
        lag = j * int(stride)
        if lag == 0:
            out[:, j] = signal
        elif lag < n:
            out[lag:, j] = signal[:-lag]
    return out


def exponential_features(signal, dt_ms=1.0, size=19):
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1 or not np.all(np.isfinite(signal)):
        raise ValueError("signal must be a finite vector")
    if not np.isfinite(dt_ms) or dt_ms <= 0:
        raise ValueError("dt_ms must be finite and positive")
    if not isinstance(size, (int, np.integer)) or size <= 0:
        raise ValueError("size must be a positive integer")
    taus = np.geomspace(3.0, 96.0, int(size))
    decay = np.exp(-dt_ms / taus)
    state = np.zeros(int(size), dtype=float)
    out = np.empty((signal.size, int(size)), dtype=float)
    for t, value in enumerate(signal):
        state = decay * state + (1.0 - decay) * value
        out[t] = state
    return out
