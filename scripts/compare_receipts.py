#!/usr/bin/env python3
"""Compare Gate A scientific payloads across receipt serializations/runtimes."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


SCIENTIFIC_KEYS = (
    'experiment',
    'v2_source_commit',
    'protocol',
    'conditions',
    'primary_evidence',
    'negative_control',
    'claim_boundary',
)


def _expand_compact_conditions(receipt):
    arms = receipt['arm_order']
    out = {}
    for noise_key, noise_payload in receipt['conditions'].items():
        out[noise_key] = {}
        for horizon_key, horizon_payload in noise_payload.items():
            expanded = {k: v for k, v in horizon_payload.items() if k != 'arms'}
            expanded_arms = {}
            for arm, packed in zip(arms, horizon_payload['arms'], strict=True):
                mean_nrmse, mean_r2, packed_rows = packed
                expanded_arms[arm] = {
                    'mean_nrmse': mean_nrmse,
                    'mean_r2': mean_r2,
                    'per_trajectory': [
                        {'seed': row[0], 'nrmse': row[1], 'r2': row[2]}
                        for row in packed_rows
                    ],
                }
            expanded['arms'] = expanded_arms
            out[noise_key][horizon_key] = expanded
    return out


def normalize_scientific(receipt):
    """Return one verbose, environment-independent scientific payload."""
    data = dict(receipt)
    if isinstance(data.get('conditions'), dict):
        sample_noise = next(iter(data['conditions'].values()), {})
        sample_horizon = next(iter(sample_noise.values()), {}) if isinstance(sample_noise, dict) else {}
        if isinstance(sample_horizon, dict) and isinstance(sample_horizon.get('arms'), list):
            data['conditions'] = _expand_compact_conditions(data)
    return {key: data[key] for key in SCIENTIFIC_KEYS}


def _compare(a, b, path, rtol, atol):
    if isinstance(a, bool) or isinstance(b, bool):
        if a is b:
            return None
        return f'{path}: {a!r} != {b!r}'
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isclose(float(a), float(b), rel_tol=rtol, abs_tol=atol):
            return None
        return f'{path}: {a!r} != {b!r}'
    if type(a) is not type(b):
        return f'{path}: type {type(a).__name__} != {type(b).__name__}'
    if isinstance(a, dict):
        if set(a) != set(b):
            return f'{path}: keys {sorted(a)} != {sorted(b)}'
        for key in sorted(a):
            mismatch = _compare(a[key], b[key], f'{path}.{key}', rtol, atol)
            if mismatch:
                return mismatch
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f'{path}: length {len(a)} != {len(b)}'
        for i, (left, right) in enumerate(zip(a, b)):
            mismatch = _compare(left, right, f'{path}[{i}]', rtol, atol)
            if mismatch:
                return mismatch
        return None
    if a != b:
        return f'{path}: {a!r} != {b!r}'
    return None


def compare_scientific(left, right, rtol=1e-9, atol=1e-10):
    a = normalize_scientific(left)
    b = normalize_scientific(right)
    mismatch = _compare(a, b, '$', rtol, atol)
    return mismatch is None, 'scientific payloads match' if mismatch is None else mismatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('expected', type=Path)
    parser.add_argument('observed', type=Path)
    parser.add_argument('--rtol', type=float, default=1e-9)
    parser.add_argument('--atol', type=float, default=1e-10)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding='utf-8'))
    observed = json.loads(args.observed.read_text(encoding='utf-8'))
    ok, message = compare_scientific(expected, observed, args.rtol, args.atol)
    print(message)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
