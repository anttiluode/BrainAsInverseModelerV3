"""Readout-only gradient/echo comparisons; frozen cable and probe are reused."""

from dataclasses import dataclass

import numpy as np

from .cable import make_cable
from .gate_p import ProbeProtocol, probe_features, query_indices as _query_indices


ARM_KEYS = ('raw_wait', 'raw_ping', 'calibrated_ping', 'gradient_wait', 'gradient_ping',
            'paired_echo_diagnostic', 'fixed_echo_diagnostic', 'edge_currents_diagnostic',
            'internal_state_diagnostic', 'present_input', 'raw_input_delays')


@dataclass(frozen=True)
class GradientProtocol(ProbeProtocol):
    test_seeds: tuple[int, ...] = (200, 201, 202, 203)
    reused_test_seeds: tuple[int, ...] = (100, 101, 102, 103)


def query_indices(protocol):
    reused = tuple(protocol.reused_test_seeds)
    if (not reused or len(set(reused)) != len(reused)
            or set(reused) & set(protocol.train_seeds + protocol.test_seeds)):
        raise ValueError('reused diagnostic trajectories must be unique and separate')
    return _query_indices(protocol)


def target_indices(queries, offset, protocol):
    queries = np.asarray(queries)
    if offset not in (20, 39) or offset <= protocol.probe_steps:
        raise ValueError('targets must be q+20 or q+39, after readout availability')
    if (queries.ndim != 1 or len(queries) == 0 or not np.issubdtype(queries.dtype, np.integer)
            or np.any(queries < 0) or np.any(queries + offset >= protocol.observe)):
        raise ValueError('target indices must stay inside the trajectory')
    return queries + offset


def temporal_coordinates(trace):
    values = np.asarray(trace, dtype=float)
    if values.ndim != 2 or values.shape[1] != 19 or not np.all(np.isfinite(values)):
        raise ValueError('nineteen finite soma samples are required')
    return np.column_stack((values[:, 0], np.diff(values, axis=1)))


def edge_current_coordinates(states, cable):
    states = np.asarray(states, dtype=float)
    n = cable.capacitance.size
    if states.ndim != 2 or states.shape[1] != n or not np.all(np.isfinite(states)):
        raise ValueError('states must be finite compartment voltages')
    edges = [(i, j) for i in range(n) for j in range(i+1, n) if cable.conductance[i, j] < 0]
    if len(edges) != n-1:
        raise ValueError('current coordinates require a tree')
    matrix = np.zeros((n, n))
    matrix[0, 0] = 1.
    for row, (i, j) in enumerate(edges, 1):
        g = -cable.conductance[i, j]
        matrix[row, i], matrix[row, j] = -g, g
    if np.linalg.matrix_rank(matrix) != n:
        raise ValueError('tree must be connected to the soma')
    return states @ matrix.T, matrix


def features(signal, queries, protocol):
    original, audit = probe_features(signal, queries, protocol)
    wait, ping = original['active_wait'], original['active_ping']
    if not np.isfinite(protocol.pulse_na) or protocol.pulse_na == 0:
        raise ValueError('susceptibility requires a finite nonzero pulse')
    currents, _ = edge_current_coordinates(original['internal_cable_state'], make_cable())
    bank = dict(raw_wait=wait, raw_ping=ping,
                calibrated_ping=ping-original['reset_ping'],
                gradient_wait=temporal_coordinates(wait), gradient_ping=temporal_coordinates(ping),
                paired_echo_diagnostic=(ping-wait)/protocol.pulse_na,
                fixed_echo_diagnostic=(original['fixed_ping']-original['fixed_wait'])/protocol.pulse_na,
                edge_currents_diagnostic=currents,
                internal_state_diagnostic=original['internal_cable_state'],
                present_input=original['present_input'], raw_input_delays=original['raw_input_delays'])
    # Control tolerances apply to the normalized susceptibility features, not
    # Gate P's inherited unnormalized voltage echoes.
    audit['fixed_echo_range'] = float(np.max(np.ptp(bank['fixed_echo_diagnostic'],axis=0)))
    audit['active_echo_range'] = float(np.max(np.ptp(bank['paired_echo_diagnostic'],axis=0)))
    return {arm: bank[arm] for arm in ARM_KEYS}, audit


def primary_evidence(arms, negative, controls):
    reference = arms['gradient_ping']
    controls_names = ('raw_ping', 'gradient_wait')
    peers = {a: {r['seed']: r['nrmse'] for r in arms[a]['per_trajectory']} for a in controls_names}
    wins = [r['seed'] for r in reference['per_trajectory']
            if all(r['nrmse'] < peers[a][r['seed']]-1e-8 for a in controls_names)]
    means = all(reference['mean_nrmse'] < arms[a]['mean_nrmse']-1e-8 for a in controls_names)
    chance = negative['mean_nrmse'] >= .90 and negative['mean_r2'] <= .05
    calibration = (controls['calibrated_prediction_max_difference'] <= 1e-8
                   and controls['fixed_echo_range'] <= 1e-10)
    return dict(condition='fresh trajectories, noise=0, target=q+20, availability=q+19',
                rule='gradient_ping beats raw_ping and gradient_wait in mean and same >=3/4 trajectories',
                joint_win_seeds=wins, raw_criterion=bool(means and len(wins) >= 3),
                negative_control_passed=bool(chance), calibration_controls_passed=bool(calibration),
                passed=bool(means and len(wins) >= 3 and chance and calibration))
