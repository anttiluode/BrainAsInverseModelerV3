# V3 progress and handoff

## Current state — 2026-10-01

**Gate A has been implemented and measured on `feature/gate-a-output-prediction`. Gates B and C have not started.**

The frozen full Gate A protocol was run once after the reduced-protocol tests passed. No scientific constants were tuned after viewing held-out results.

## Source and question

V2 source anchor: `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`.

Question: can a receiver use emitted soma history to learn useful forecasts of the observed world, without hidden-state training labels or access to the sender's branch voltages?

## Completed work

- Ported the pinned V2 passive cable, Lorenz generator, temporal feature functions, and quadratic readout with matching source hashes for `cable.py`, `world.py`, and `readout.py`.
- Added the six frozen Gate A comparison arms with causal timing and equal width 19.
- Added explicit timing, causality, data-separation, constant-signal, and degenerate-feature tests.
- Added deterministic train/test trajectory generation, the two declared input-noise levels, horizons 1/5/20, and observation-only forecast training.
- Added an isolated independent-Gaussian-label negative control.
- Ran the full frozen experiment and wrote `results/gate_a_receipt.json`. The committed receipt uses a lossless compact schema that removes repeated JSON keys while retaining every full-precision arm/horizon/noise/trajectory metric.
- Wrote `docs/findings.md` and updated README with the measured result.

## Measured headline result

Primary condition: zero input noise, horizon 20.

- raw input delays: mean NRMSE 0.6406
- internal cable state: 0.7441
- present input: 0.8160
- soma history: 0.8314
- instantaneous soma: 0.9492
- soma history beat both required baselines on 1/4 held-out trajectories
- predeclared Gate A evidence criterion: **failed**
- independent-label negative control: NRMSE 0.9947, R² -0.0045

Interpretation: useful predictive information remains in the internal cable state, but the specified one-dimensional soma-history output does not expose enough of it to outperform the present observation. Ordinary input delays remain substantially better.

## Checks actually run locally

```text
python -m unittest tests.test_core -v
python -m unittest tests.test_gate_a -v
python -m unittest discover -s tests -v
python scripts/run_gate_a.py --quick --output /tmp/gatea-quick.json
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_a.py --output results/gate_a_receipt.json
```

The full suite was rerun after the frozen receipt and documentation were written: **13/13 tests passed**.

## Remote checkpoints

- Gate A implementation plan: `d7ad490a25f4834112ebab0657ffdd2b15e11488`
- Authorization checkpoint: `482f9965347c0b7b80f34b69e0a9bb22d374b1b2`
- Pinned V2 core port: `1ed2ba34872051754ad9cb11bdcdf703c43a620d`
- Causal Gate A protocol: `f0b93f24da5ee5b3fdcde2ff7407299822158bc0`

The result/receipt checkpoint has not yet been published remotely at the time this progress text is authored; use the next commit in branch history for that exact SHA.

## Unresolved caveats

- Gate A uses continuous soma voltage, not spikes or synaptic reception.
- The output reader is an external supervised quadratic ridge model with delayed observational targets; no biological learning pathway is implemented.
- Only one soma-history width/stride and one passive cable are tested. Changing them after seeing this result would be a new experiment, not a rescue of Gate A.
- CI reproducibility is the next implementation task; it must rerun the frozen experiment without overwriting the committed receipt.

## Precise next action

Complete the remote reproducibility checkpoint (Task 4): add CI, rerun tests and the frozen scientific payload in a temporary path, compare it against the committed receipt, then read back the published checkpoint. Do not begin Gate B or C.
