"""Passive RC cable: nF, microSiemens, nA, mV and ms.

Values describe an illustrative circuit, not a fitted biological neuron.
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import expm


@dataclass
class Cable:
    capacitance: np.ndarray
    conductance: np.ndarray
    ports: list[int]

    def __post_init__(self):
        self.capacitance = np.array(self.capacitance, dtype=float, copy=True)
        self.conductance = np.array(self.conductance, dtype=float, copy=True)
        n = self.capacitance.size
        if self.capacitance.ndim != 1 or n == 0 or not np.all(np.isfinite(self.capacitance)):
            raise ValueError("Capacitance must be a finite nonempty vector.")
        if np.any(self.capacitance <= 0):
            raise ValueError("Capacitance must be positive.")
        if self.conductance.shape != (n, n) or not np.all(np.isfinite(self.conductance)):
            raise ValueError("Conductance must be a finite square matrix.")
        if not np.allclose(self.conductance, self.conductance.T, atol=1e-12):
            raise ValueError("The passive conductance matrix must be symmetric.")
        if np.linalg.eigvalsh(self.conductance).min() < -1e-12:
            raise ValueError("The conductance matrix must be positive semidefinite.")
        if not self.ports or any(not isinstance(p, (int, np.integer)) or p < 0 or p >= n for p in self.ports):
            raise ValueError("Each input port must index a compartment.")
        self.ports = list(self.ports)

    def transition(self, dt_ms):
        """Exact constant-input transition v_next = F v + H i."""
        if not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError("dt_ms must be finite and positive.")
        n, m = self.capacitance.size, len(self.ports)
        generator = np.zeros((n + m, n + m))
        generator[:n, :n] = -self.conductance / self.capacitance[:, None]
        for j, port in enumerate(self.ports):
            generator[port, n + j] = 1.0 / self.capacitance[port]
        transition = expm(generator * dt_ms)
        return transition[:n, :n], transition[:n, n:]

    def encode(self, currents, dt_ms=1.0):
        """Voltages after each input interval, starting at rest; no future samples."""
        currents = np.asarray(currents, dtype=float)
        if currents.ndim != 2 or currents.shape[1] != len(self.ports) or not np.all(np.isfinite(currents)):
            raise ValueError("Currents must have shape (time, input ports) and finite values.")
        f, h = self.transition(dt_ms)
        state = np.zeros(self.capacitance.size)
        history = np.empty((len(currents), state.size))
        for t, current in enumerate(currents):
            state = f @ state + h @ current
            history[t] = state
        return history


def make_cable(diverse=True, tau_scale=1.0):
    if not np.isfinite(tau_scale) or tau_scale <= 0:
        raise ValueError("tau_scale must be finite and positive.")
    taus = np.array([3, 6, 12, 24, 48, 96], dtype=float) if diverse else np.full(6, 24.0)
    axial = np.array([0.012, 0.009, 0.006, 0.004, 0.0025, 0.0015]) if diverse else np.full(6, 0.004)
    capacitance = np.full(19, 0.01)
    capacitance[0] = 0.05
    leak = np.concatenate(([0.005], np.repeat(0.01 / (taus * tau_scale), 3)))
    conductance = np.diag(leak)
    for branch, g in enumerate(axial):
        nodes = [0, 1 + 3 * branch, 2 + 3 * branch, 3 + 3 * branch]
        for a, b in zip(nodes[:-1], nodes[1:]):
            conductance[a, a] += g
            conductance[b, b] += g
            conductance[a, b] -= g
            conductance[b, a] -= g
    return Cable(capacitance, conductance, [3, 6, 9, 12, 15, 18])


def impulse_operator(cable, dt_ms=0.5, steps=400, pulse_ms=1.0, current_na=0.01):
    """One soma impulse-response column per distal branch input."""
    if not isinstance(steps, int) or steps <= 0:
        raise ValueError("steps must be a positive integer.")
    if not np.isfinite(pulse_ms) or pulse_ms <= 0 or not np.isfinite(current_na):
        raise ValueError("Pulse duration must be positive and pulse current finite.")
    f, h = cable.transition(dt_ms)
    intervals = pulse_ms / dt_ms
    if not np.isclose(intervals, round(intervals)) or intervals > steps:
        raise ValueError("The pulse must occupy an integer number of sample intervals.")
    m = len(cable.ports)
    state = np.zeros((cable.capacitance.size, m))
    operator = np.empty((steps, m))
    for t in range(steps):
        state = f @ state
        if t < round(intervals):
            state += current_na * h
        operator[t] = state[0]
    return operator
