"""Snapshot return-pulse assay; the frozen Gate A encoder stays unchanged."""

from dataclasses import dataclass

import numpy as np

from .cable import make_cable
from .gate_a import Protocol, feature_bank


ARM_KEYS = ('active_wait', 'active_ping', 'fixed_wait', 'fixed_ping',
            'reset_ping', 'present_input', 'raw_input_delays',
            'soma_history', 'internal_cable_state')


@dataclass(frozen=True)
class ProbeProtocol(Protocol):
    horizons: tuple[int, ...] = (20,)
    probe_steps: int = 19
    gate_gain: float = 0.75
    gate_scale_mv: float = 1.0
    pulse_na: float = 0.01


def query_indices(protocol):
    """Only queries with a complete blackout and later forecast target."""
    p = protocol
    integers = (p.observe, p.discard, p.sample_stride, p.probe_steps,
                p.history_size, p.history_stride, p.burn)
    if any(not isinstance(x, (int, np.integer)) for x in integers):
        raise ValueError('sample counts and strides must be integers')
    if (p.history_size != 19 or p.probe_steps != 19 or p.cable_dt_ms != 1.
            or p.horizons != (20,) or p.history_stride != 2):
        raise ValueError('Gate P fixes nineteen one-ms samples, stride-two history, and h=20')
    if p.discard < 0 or p.burn < 0 or p.sample_stride <= 0:
        raise ValueError('invalid query schedule')
    train, test = tuple(p.train_seeds), tuple(p.test_seeds)
    if (not train or not test or len(set(train)) != len(train)
            or len(set(test)) != len(test) or set(train) & set(test)):
        raise ValueError('training and test trajectories must be nonempty, unique and disjoint')
    if 0. not in p.noise_levels or any(not np.isfinite(x) or x < 0 for x in p.noise_levels):
        raise ValueError('noise levels must include zero and be finite and nonnegative')
    idx = np.arange(p.discard, p.observe - p.probe_steps - 20, p.sample_stride)
    if len(idx) == 0:
        raise ValueError('no eligible query/availability/target rows')
    return idx


def interrogate(states, cable, *, steps=19, dt_ms=1., gain=0.75,
                voltage_scale_mv=1., pulse_na=0.01):
    """Exact RC ring-down with a held local gate and a one-interval soma pulse.

    Each row is a separate copy of a state. There is no subsequent sensory input.
    The external reader receives only the resulting soma waveform.
    """
    v = np.asarray(states, dtype=float)
    n = cable.capacitance.size
    if v.ndim != 2 or v.shape[1] != n or len(v) == 0 or not np.all(np.isfinite(v)):
        raise ValueError('states must be a finite nonempty (queries, compartments) matrix')
    if not isinstance(steps, (int, np.integer)) or steps <= 0:
        raise ValueError('steps must be a positive integer')
    if (not np.isfinite(dt_ms) or dt_ms <= 0
            or not np.isfinite(gain) or not 0 <= gain < 1
            or not np.isfinite(voltage_scale_mv) or voltage_scale_mv <= 0
            or not np.isfinite(pulse_na)):
        raise ValueError('invalid pulse/gate parameters')
    leak = cable.conductance.sum(axis=1)
    if np.any(leak <= 0):
        raise ValueError('the interrogation cable requires positive membrane leaks')
    extra = gain * leak * np.tanh(v / voltage_scale_mv)
    extra[:, 0] = 0.  # no direct soma gate: only unreported branch state writes it
    matrices = np.broadcast_to(cable.conductance, (len(v), n, n)).copy()
    diagonal = np.arange(n)
    matrices[:, diagonal, diagonal] += extra
    sqrt_c = np.sqrt(cable.capacitance)
    symmetric = matrices / sqrt_c[None, :, None] / sqrt_c[None, None, :]
    rates, modes = np.linalg.eigh(symmetric)
    if np.any(rates <= 0):
        raise ValueError('interrogation operator must be positive definite')
    decay = np.exp(-rates * dt_ms)
    integral = -np.expm1(-rates * dt_ms) / rates
    amplitudes = np.einsum('nji,nj->ni', modes, v * sqrt_c)
    source = modes[:, 0, :] / sqrt_c[0]
    trace = np.empty((len(v), steps))
    for t in range(steps):
        amplitudes *= decay
        if t == 0:
            amplitudes += integral * source * pulse_na
        trace[:, t] = np.sum(modes[:, 0, :] * amplitudes, axis=1) / sqrt_c[0]
    return trace


def probe_features(signal, indices, protocol):
    """Causal query features: no future observation or forecasting target argument."""
    signal = np.asarray(signal, dtype=float)
    indices = np.asarray(indices)
    if (signal.shape != (protocol.observe,) or not np.all(np.isfinite(signal))
            or indices.ndim != 1 or not np.issubdtype(indices.dtype, np.integer)
            or len(indices) == 0 or np.any(indices < 0) or np.any(indices >= len(signal))):
        raise ValueError('invalid observed signal or query indices')
    cable = make_cable(diverse=True)
    original = feature_bank(signal, cable, protocol)
    states = original['internal_cable_state'][indices]
    common = dict(steps=protocol.probe_steps, dt_ms=protocol.cable_dt_ms,
                  voltage_scale_mv=protocol.gate_scale_mv)
    bank = {}
    for prefix, gain in [('active', protocol.gate_gain), ('fixed', 0.)]:
        for suffix, pulse in [('wait', 0.), ('ping', protocol.pulse_na)]:
            bank[f'{prefix}_{suffix}'] = interrogate(states, cable, gain=gain,
                                                    pulse_na=pulse, **common)
    bank['reset_ping'] = interrogate(np.zeros_like(states), cable,
                                    gain=protocol.gate_gain,
                                    pulse_na=protocol.pulse_na, **common)
    for arm in ('present_input', 'raw_input_delays', 'soma_history', 'internal_cable_state'):
        bank[arm] = original[arm][indices]
    audit = {
        'fixed_echo_range': float(np.max(np.ptp(bank['fixed_ping']-bank['fixed_wait'], axis=0))),
        'active_echo_range': float(np.max(np.ptp(bank['active_ping']-bank['active_wait'], axis=0))),
        'reset_trace_range': float(np.max(np.ptp(bank['reset_ping'], axis=0))),
    }
    return {arm: bank[arm] for arm in ARM_KEYS}, audit


def matched_soma_witness(protocol):
    """Known-answer mechanism check, never a forecast feature or training label."""
    states = np.zeros((2, 19))
    states[:, 0] = .2
    states[0, 1:4] = 2.
    states[1, 4:7] = 2.
    result = {}
    for name, gain in [('fixed', 0.), ('active', protocol.gate_gain)]:
        args = dict(gain=gain, steps=protocol.probe_steps,
                    voltage_scale_mv=protocol.gate_scale_mv, dt_ms=protocol.cable_dt_ms)
        ping = interrogate(states, make_cable(), pulse_na=protocol.pulse_na, **args)
        wait = interrogate(states, make_cable(), pulse_na=0., **args)
        echoes = ping-wait
        result[f'matched_soma_{name}_echo_difference'] = float(np.max(np.abs(echoes[0]-echoes[1])))
    return result


def evidence(scores, controls, negative):
    """Require the same test trajectories to win every matched comparison."""
    comparisons = ('active_wait', 'fixed_wait', 'fixed_ping')
    reference = scores['active_ping']
    peers = {arm: {r['seed']: r['nrmse'] for r in scores[arm]['per_trajectory']}
             for arm in comparisons + ('present_input',)}
    wins = [r['seed'] for r in reference['per_trajectory']
            if all(r['nrmse'] < peers[a][r['seed']]-1e-8 for a in comparisons)]
    means = all(reference['mean_nrmse'] < scores[a]['mean_nrmse']-1e-8 for a in comparisons)
    chance_ok = negative['mean_nrmse'] >= .90 and negative['mean_r2'] <= .05
    controls_ok = (controls['fixed_echo_range'] <= 1e-10
                   and controls['reset_trace_range'] <= 1e-10
                   and controls['active_echo_range'] > 1e-10
                   and controls['matched_soma_fixed_echo_difference'] <= 1e-10
                   and controls['matched_soma_active_echo_difference'] > 1e-7)
    access = means and len(wins) >= 3
    forecast_wins = [r['seed'] for r in reference['per_trajectory']
                     if r['nrmse'] < peers['present_input'][r['seed']]-1e-8]
    forecast = (access and len(forecast_wins) >= 3
                and reference['mean_nrmse'] < scores['present_input']['mean_nrmse']-1e-8)
    return dict(condition='noise=0, h=20 after 19-sample blackout',
                rule='active_ping beats all three matched controls in mean and on same >=3/4 trajectories',
                raw_access_criterion=bool(access), raw_forecast_criterion=bool(forecast),
                access_win_seeds=wins, forecast_win_seeds=forecast_wins,
                required_trajectory_wins=3, negative_control_passed=bool(chance_ok),
                mechanism_controls_passed=bool(controls_ok),
                access_passed=bool(access and chance_ok and controls_ok),
                forecast_passed=bool(forecast and chance_ok and controls_ok))
