#!/usr/bin/env python3
"""Compare every Gate P scientific field, including provenance and controls."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compare_receipts import _compare
from scripts.run_gate_p import scientific_payload


def compare_scientific(left, right, rtol=1e-9, atol=1e-10):
    mismatch = _compare(scientific_payload(left), scientific_payload(right), '$', rtol, atol)
    return mismatch is None, 'scientific payloads match' if mismatch is None else mismatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected', type=Path)
    parser.add_argument('observed', type=Path)
    args = parser.parse_args()
    left = json.loads(args.expected.read_text())
    right = json.loads(args.observed.read_text())
    ok, message = compare_scientific(left, right)
    print(message)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
