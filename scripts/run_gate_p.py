#!/usr/bin/env python3
"""Run the predeclared return-pulse assay without altering Gate A or C0."""

import argparse
import hashlib
import json
import platform
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import scipy

from emitted_state.gate_a import observed_x, r2_score, world_for_seed
from emitted_state.gate_p import (ARM_KEYS, ProbeProtocol, evidence, matched_soma_witness,
                                  probe_features, query_indices)
from emitted_state.readout import QuadraticReadout, normalized_rmse

SOURCE_FILES = ('emitted_state/cable.py', 'emitted_state/world.py',
                'emitted_state/readout.py', 'emitted_state/gate_a.py',
                'emitted_state/gate_p.py', 'scripts/run_gate_p.py', 'docs/gate_p_protocol.md')


def _summary(rows):
    return dict(mean_nrmse=float(np.mean([r['nrmse'] for r in rows])),
                mean_r2=float(np.mean([r['r2'] for r in rows])), per_trajectory=rows)


def _score(model, features, truth, scale, seed):
    prediction = model.predict(features)[:, 0]
    return dict(seed=int(seed), nrmse=normalized_rmse(truth, prediction, scale),
                r2=r2_score(truth, prediction))


def _negative_control(banks, protocol, indices, targets):
    labels = {s: np.random.default_rng(900000+s).normal(size=protocol.observe)
              for s in protocol.train_seeds + protocol.test_seeds}
    y = np.concatenate([labels[s][targets] for s in protocol.train_seeds])
    mean, scale = float(y.mean()), float(y.std())
    x = np.concatenate([banks[s]['active_ping'] for s in protocol.train_seeds])
    model = QuadraticReadout(protocol.ridge_factor).fit(x, (y-mean)/scale)
    rows = [_score(model, banks[s]['active_ping'], (labels[s][targets]-mean)/scale, 1., s)
            for s in protocol.test_seeds]
    return dict(description='independent Gaussian labels, active_ping reader; evaluation only',
                label_seed_formula='900000 + trajectory_seed', **_summary(rows))


def run_experiment(protocol=None):
    p = ProbeProtocol() if protocol is None else protocol
    idx = query_indices(p)
    target_idx = idx + p.probe_steps + 20
    all_seeds = p.train_seeds + p.test_seeds
    worlds = {s: world_for_seed(s, p) for s in all_seeds}
    clean_scale = float(np.concatenate([worlds[s][:, 0] for s in p.train_seeds]).std())
    conditions, normalization, controls_by_noise = {}, {}, {}
    negative = None
    for noise in p.noise_levels:
        key = f'noise_{noise:g}'
        observed = {s: observed_x(worlds[s], s, noise, clean_scale) for s in all_seeds}
        train = np.concatenate([observed[s] for s in p.train_seeds])
        mean, scale = float(train.mean()), float(train.std())
        if scale <= 0:
            raise ValueError('training observations have zero variance')
        normalization[key] = dict(fit_seeds=list(p.train_seeds), observed_mean=mean,
                                  observed_scale=scale, clean_noise_scale=clean_scale)
        banks, audits = {}, {}
        for seed in all_seeds:
            banks[seed], audits[seed] = probe_features((observed[seed]-mean)/scale, idx, p)
        controls = {k: max(a[k] for a in audits.values())
                    for k in ('fixed_echo_range', 'active_echo_range', 'reset_trace_range')}
        controls.update(matched_soma_witness(p))
        controls_by_noise[key] = controls
        y = np.concatenate([observed[s][target_idx] for s in p.train_seeds])
        arms = {}
        for arm in ARM_KEYS:
            x = np.concatenate([banks[s][arm] for s in p.train_seeds])
            model = QuadraticReadout(p.ridge_factor).fit(x, y)
            rows = [_score(model, banks[s][arm], worlds[s][target_idx, 0], scale, s)
                    for s in p.test_seeds]
            arms[arm] = _summary(rows)
        conditions[key] = dict(arms=arms, sample_count_per_trajectory=int(len(idx)))
        if noise == 0.:
            negative = _negative_control(banks, p, idx, target_idx)
    primary = evidence(conditions['noise_0']['arms'], controls_by_noise['noise_0'], negative)
    return dict(
        schema_version=1, experiment='Gate P — state-sensitive soma return pulse',
        base_commit='f950bfb30f0f72f92648242b1e802aa38d334a4e', protocol=asdict(p),
        source_sha256={path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_FILES},
        runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        timing=dict(query_first=int(idx[0]), query_last=int(idx[-1]),
                    readout_availability_offset=p.probe_steps, forecast_horizon_after_availability=20,
                    target_offset=p.probe_steps+20, samples_per_trajectory=int(len(idx)),
                    query_indices_sha256=hashlib.sha256(idx.astype('<i8').tobytes()).hexdigest(),
                    target_indices_sha256=hashlib.sha256(target_idx.astype('<i8').tobytes()).hexdigest(),
                    all_arms_share_rows=True, fresh_sensory_samples_during_interrogation=0),
        normalization=normalization, conditions=conditions, controls=controls_by_noise,
        primary_evidence=primary, negative_control=negative,
        claim_boundary=dict(training_target='later observed x only',
                            receiver_access='own soma trace for interrogation arms',
                            hidden_yz_used_for_forecast_fit=False,
                            counterfactual_echo_is_primary_feature=False,
                            synthetic_local_voltage_to_held_conductance=True,
                            snapshot_copies_not_continuous_feedback=True,
                            test_seeds_reuse_earlier_benchmark=True,
                            biological_learning_rule_claimed=False,
                            gate_a_and_c0_unchanged=True))


def scientific_payload(receipt):
    return {k: v for k, v in receipt.items() if k != 'runtime'}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick', action='store_true', help='Engineering smoke run only.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = (Path(tempfile.gettempdir())/'gate_p_quick.json' if args.quick
                       else ROOT/'results/gate_p_receipt.json')
    return args


def main():
    args = parse_args()
    protocol = (ProbeProtocol(train_seeds=(10, 11), test_seeds=(100, 101),
                              burn=80, observe=420, discard=80) if args.quick else ProbeProtocol())
    receipt = run_experiment(protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    for arm, result in receipt['conditions']['noise_0']['arms'].items():
        print(f"{arm:24s} {result['mean_nrmse']:.6f}")
    print('P-access passed:', receipt['primary_evidence']['access_passed'])
    print('P-forecast passed:', receipt['primary_evidence']['forecast_passed'])
    print('Negative-control NRMSE:', receipt['negative_control']['mean_nrmse'])
    print('Receipt:', args.output)


if __name__ == '__main__':
    main()
