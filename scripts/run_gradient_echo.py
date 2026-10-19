#!/usr/bin/env python3
"""Test temporal gradients, calibrated artifacts and diagnostic spatial/paired reads."""

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

from emitted_state.gate_a import observed_x, world_for_seed
from emitted_state.gradient_echo import (ARM_KEYS, GradientProtocol, features,
                                        primary_evidence, query_indices, target_indices)
from emitted_state.readout import QuadraticReadout
from scripts.run_gate_p import _score, _summary


SOURCE_FILES = ('emitted_state/cable.py', 'emitted_state/world.py', 'emitted_state/readout.py',
                'emitted_state/gate_a.py', 'emitted_state/gate_p.py',
                'emitted_state/gradient_echo.py', 'scripts/run_gate_p.py',
                'scripts/run_gradient_echo.py', 'docs/gradient_echo_protocol.md')


def _negative(banks, p, target):
    seeds = p.train_seeds + p.test_seeds
    labels = {s: np.random.default_rng(1100000+s).normal(size=p.observe) for s in seeds}
    y = np.concatenate([labels[s][target] for s in p.train_seeds])
    mean, scale = float(y.mean()), float(y.std())
    x = np.concatenate([banks[s]['gradient_ping'] for s in p.train_seeds])
    model = QuadraticReadout(p.ridge_factor).fit(x, (y-mean)/scale)
    return dict(label_seed_formula='1100000 + trajectory_seed',
                **_summary([_score(model,banks[s]['gradient_ping'],
                                   (labels[s][target]-mean)/scale,1.,s) for s in p.test_seeds]))


def run_experiment(protocol=None):
    p = GradientProtocol() if protocol is None else protocol
    idx = query_indices(p)
    targets = {offset: target_indices(idx, offset, p) for offset in (20,39)}
    all_seeds = p.train_seeds+p.test_seeds+p.reused_test_seeds
    worlds = {s: world_for_seed(s,p) for s in all_seeds}
    clean_scale = float(np.concatenate([worlds[s][:,0] for s in p.train_seeds]).std())
    conditions, normalizations, audits = {}, {}, {}
    negative = None
    for noise in p.noise_levels:
        key = f'noise_{noise:g}'
        observed = {s: observed_x(worlds[s],s,noise,clean_scale) for s in all_seeds}
        train = np.concatenate([observed[s] for s in p.train_seeds])
        mean, scale = float(train.mean()), float(train.std())
        if scale <= 0:
            raise ValueError('training scale must be positive')
        normalizations[key] = dict(fit_seeds=list(p.train_seeds),mean=mean,scale=scale)
        banks, local_audits = {}, []
        for seed in all_seeds:
            banks[seed], audit = features((observed[seed]-mean)/scale,idx,p)
            local_audits.append(audit)
        audits[key] = {k: max(a[k] for a in local_audits) for k in local_audits[0]}
        audits[key]['calibrated_prediction_max_difference'] = 0.
        conditions[key] = {}
        for offset, target in targets.items():
            y = np.concatenate([observed[s][target] for s in p.train_seeds])
            models = {a: QuadraticReadout(p.ridge_factor).fit(
                np.concatenate([banks[s][a] for s in p.train_seeds]),y) for a in ARM_KEYS}
            for seed in p.test_seeds+p.reused_test_seeds:
                difference = float(np.max(np.abs(models['raw_ping'].predict(banks[seed]['raw_ping'])
                                                  -models['calibrated_ping'].predict(banks[seed]['calibrated_ping']))))
                audits[key]['calibrated_prediction_max_difference'] = max(
                    audits[key]['calibrated_prediction_max_difference'],difference)
            result = dict(target_offset=offset,availability_offset=19,
                          horizon_after_availability=offset-19,queries_per_trajectory=int(len(idx)))
            for group,seeds in [('fresh',p.test_seeds),('reused',p.reused_test_seeds)]:
                result[group] = dict(arms={a:_summary([
                    _score(models[a],banks[s][a],worlds[s][target,0],scale,s) for s in seeds])
                    for a in ARM_KEYS})
            conditions[key][f'target_{offset}'] = result
        if noise == 0.:
            negative = _negative(banks,p,targets[20])
    primary = primary_evidence(conditions['noise_0']['target_20']['fresh']['arms'],
                               negative,audits['noise_0'])
    return dict(schema_version=1,experiment='Gradient/echo readout follow-up',
                base_commit='e246bbda4b47e76f1f99b3331e01f319439664da',protocol=asdict(p),
                source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCE_FILES},
                runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
                timing=dict(availability_offset=19,primary_target_offset=20,
                            primary_horizon_after_availability=1,secondary_target_offset=39,
                            secondary_horizon_after_availability=20,queries_per_trajectory=int(len(idx)),
                            query_indices_sha256=hashlib.sha256(idx.astype('<i8').tobytes()).hexdigest(),
                            sensory_observations_after_query=0),
                normalization=normalizations,conditions=conditions,controls=audits,
                negative_control=negative,primary_evidence=primary,
                claim_boundary=dict(encoder_and_probe_unchanged=True,
                                    gradient_coordinates_are_temporal_not_spatial=True,
                                    temporal_transform_is_invertible=True,
                                    paired_echo_requires_query_specific_counterfactual=True,
                                    edge_currents_require_all_compartments=True,
                                    primary_readout_uses_only_own_soma_trace=True,
                                    test_targets_never_used_for_fit=True,
                                    fresh_primary_test_seeds=list(p.test_seeds),
                                    biological_learning_claimed=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    p = (GradientProtocol(train_seeds=(10,11),test_seeds=(200,),reused_test_seeds=(100,),
                          burn=50,observe=240,discard=60,sample_stride=8,noise_levels=(0.,))
         if args.quick else GradientProtocol())
    output = args.output or (Path(tempfile.gettempdir())/'gradient_echo_quick.json' if args.quick
                             else ROOT/'results/gradient_echo_receipt.json')
    receipt = run_experiment(p)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    for offset in (20,39):
        print(f'Fresh tests, target q+{offset}:')
        for arm,result in receipt['conditions']['noise_0'][f'target_{offset}']['fresh']['arms'].items():
            print(f"  {arm:28s} {result['mean_nrmse']:.6f}")
    print('Primary passed:',receipt['primary_evidence']['passed'])
    print('Calibrated/raw prediction difference:',receipt['controls']['noise_0']['calibrated_prediction_max_difference'])
    print('Receipt:',output)


if __name__ == '__main__':
    main()
