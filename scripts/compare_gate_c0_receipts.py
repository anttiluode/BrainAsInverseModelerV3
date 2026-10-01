#!/usr/bin/env python3
"""Compare Gate C0 scientific receipts across verbose/compact/wrapped serializations."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
import zlib
from pathlib import Path


SCIENTIFIC_KEYS = (
    "experiment",
    "protocol",
    "emitter",
    "source_sha256",
    "event_counts",
    "conditions",
    "primary_evidence",
    "negative_control",
    "claim_boundary",
)


def _unwrap(receipt: dict) -> dict:
    data = copy.deepcopy(receipt)
    if data.get("schema_version") != 3:
        return data
    if data.get("encoding") != "zlib+base64":
        raise ValueError("unsupported Gate C0 wrapper encoding")
    try:
        raw = zlib.decompress(base64.b64decode(data["payload_zlib_base64"], validate=True))
    except Exception as exc:
        raise ValueError("invalid Gate C0 wrapped payload") from exc
    observed_sha = hashlib.sha256(raw).hexdigest()
    if observed_sha != data.get("canonical_sha256"):
        raise ValueError("Gate C0 wrapper canonical SHA-256 mismatch")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("wrapped Gate C0 payload is not JSON") from exc


def _expand_compact(receipt: dict) -> dict:
    if receipt.get("schema_version") != 2:
        return receipt
    data = copy.deepcopy(receipt)
    arm_order = data.pop("arm_order")
    horizon_order = data.pop("horizon_order")
    exclusion_order = data.pop("event_exclusion_order")

    event_counts = {}
    for noise_key, packed_rows in data["event_counts"].items():
        expanded_rows = {}
        for row in packed_rows:
            if len(row) != 9:
                raise ValueError("invalid compact Gate C0 event-count row")
            seed, detected, valid, table_events, exclusions, scored, waveform, soma_norm, digest = row
            expanded_rows[str(seed)] = {
                "detected_spikes": detected,
                "valid_waveforms": valid,
                "table_events": table_events,
                "exclusions": dict(zip(exclusion_order, exclusions, strict=True)),
                "scored": dict(zip(horizon_order, scored, strict=True)),
                "waveform_features": {
                    "count": waveform[0],
                    "mean": waveform[1],
                    "std": waveform[2],
                    "min": waveform[3],
                    "max": waveform[4],
                },
                "soma_normalization": {"mean": soma_norm[0], "scale": soma_norm[1]},
                "event_identity_sha256": digest,
            }
        event_counts[noise_key] = expanded_rows
    data["event_counts"] = event_counts

    conditions = {}
    for noise_key, packed in data["conditions"].items():
        noise_payload = {}
        for horizon_key in horizon_order:
            packed_arms = packed["horizons"][horizon_key]
            arms = {}
            for arm, arm_row in zip(arm_order, packed_arms, strict=True):
                mean_nrmse, mean_r2, packed_trajectories = arm_row
                arms[arm] = {
                    "mean_nrmse": mean_nrmse,
                    "mean_r2": mean_r2,
                    "per_trajectory": [
                        {
                            "seed": row[0],
                            "nrmse": row[1],
                            "r2": row[2],
                            "event_identity_sha256": row[3],
                            "events": row[4],
                        }
                        for row in packed_trajectories
                    ],
                }
            noise_payload[horizon_key] = {
                "training_observed_mean": packed["training_observed_mean"],
                "training_observed_scale": packed["training_observed_scale"],
                "timing_normalization": copy.deepcopy(packed["timing_normalization"]),
                "residualization_provenance": copy.deepcopy(packed["residualization_provenance"]),
                "arms": arms,
            }
        conditions[noise_key] = noise_payload
    data["conditions"] = conditions

    negative = data["negative_control"]
    if isinstance(negative.get("per_trajectory"), list) and negative["per_trajectory"] and isinstance(negative["per_trajectory"][0], list):
        negative["per_trajectory"] = [
            {"seed": row[0], "nrmse": row[1], "r2": row[2], "events": row[3]}
            for row in negative["per_trajectory"]
        ]
    data["schema_version"] = 1
    return data


def _drop_event_identity_digests(value):
    """Remove raw-float event digests for cross-machine reproduction only.

    The digest is strict evidence inside the frozen receipt, but it hashes raw
    floating-point onset values and therefore changes with BLAS/CPU kernels at
    last-bit precision. Portable comparison still checks source hashes, event
    counts, exclusions, metrics, evidence booleans, and the negative control.
    """
    if isinstance(value, dict):
        return {
            key: _drop_event_identity_digests(item)
            for key, item in value.items()
            if key != "event_identity_sha256"
        }
    if isinstance(value, list):
        return [_drop_event_identity_digests(item) for item in value]
    return value


def normalize_scientific(receipt: dict, *, portable: bool = False) -> dict:
    """Return one verbose, serialization- and environment-independent payload."""
    data = _expand_compact(_unwrap(receipt))
    missing = [key for key in SCIENTIFIC_KEYS if key not in data]
    if missing:
        raise ValueError(f"Gate C0 receipt missing scientific keys: {missing}")
    payload = {key: copy.deepcopy(data[key]) for key in SCIENTIFIC_KEYS}
    return _drop_event_identity_digests(payload) if portable else payload


def _compare(a, b, path, rtol, atol):
    if isinstance(a, bool) or isinstance(b, bool):
        if type(a) is type(b) and a == b:
            return None
        return f"{path}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isclose(float(a), float(b), rel_tol=rtol, abs_tol=atol):
            return None
        return f"{path}: {a!r} != {b!r}"
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        if set(a) != set(b):
            return f"{path}: keys {sorted(a)} != {sorted(b)}"
        for key in sorted(a):
            mismatch = _compare(a[key], b[key], f"{path}.{key}", rtol, atol)
            if mismatch:
                return mismatch
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for index, (left, right) in enumerate(zip(a, b, strict=True)):
            mismatch = _compare(left, right, f"{path}[{index}]", rtol, atol)
            if mismatch:
                return mismatch
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"
    return None


def compare_scientific(
    left: dict,
    right: dict,
    rtol: float = 1e-9,
    atol: float = 1e-10,
    *,
    portable: bool = False,
):
    a = normalize_scientific(left, portable=portable)
    b = normalize_scientific(right, portable=portable)
    mismatch = _compare(a, b, "$", rtol, atol)
    return mismatch is None, "scientific payloads match" if mismatch is None else mismatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("expected", type=Path)
    parser.add_argument("observed", type=Path)
    parser.add_argument("--rtol", type=float, default=1e-9)
    parser.add_argument("--atol", type=float, default=1e-10)
    parser.add_argument(
        "--portable",
        action="store_true",
        help="ignore hardware-sensitive raw-float event SHA fields only",
    )
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    observed = json.loads(args.observed.read_text(encoding="utf-8"))
    ok, message = compare_scientific(
        expected,
        observed,
        args.rtol,
        args.atol,
        portable=args.portable,
    )
    print(message)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
