# V3 progress and handoff

## Current state — 2026-10-01

**Gate A is complete and merged to `main`. Gate C0 has been implemented and its frozen full-protocol result has been measured on `feature/gate-c0-waveform-state-spec`. C0-A and C0-B both passed. CI reproduction is the remaining Gate C0 task.**

Gate A's negative result remains frozen. Gate C0 is a new output-transform experiment, not a repair of Gate A.

## Gate A anchor

Main merge commit: `0f1627b25737556de80c62c2ea949461e3130296`.

Primary Gate A result at zero input noise, horizon 20:

- raw input delays: mean NRMSE 0.6406
- internal cable state: 0.7441
- present input: 0.8160
- soma history: 0.8314
- instantaneous soma: 0.9492
- soma history beat both required baselines on 1/4 held-out trajectories
- predeclared Gate A criterion: **failed**

Interpretation: the passive cable retained useful predictive state internally, but the declared scalar soma-history output/readout did not expose enough of it to beat the present observation. Ordinary raw delays remained better.

## Gate C0 source and question

Empirical motivation: Martin-Burgos et al., *Action potential waveforms are state-dependent* (bioRxiv 2026.09.15.751814; preprint, posted 21 September 2026).

Spec:

`docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`

Implementation plan:

`docs/superpowers/plans/2026-10-01-gate-c0-waveform-state.md`

Branch:

`feature/gate-c0-waveform-state-spec`

Question:

**Does a spike carry a small state-dependent waveform payload that adds useful predictive information beyond the timing of the exact same spikes?**

## Implemented mechanism and controls

- Passive V3 cable unchanged.
- One-way classical Hodgkin–Huxley emitter with standard Na/K/leak parameters, steady-state gates at -65 mV, deterministic RK4 at 0.025 ms.
- Training-only soma normalization and frozen drive `I_emit = 10 + 4*tanh(z_s/2)` uA/cm².
- Spike onset at interpolated upward 0 mV crossing; waveform available only after the complete -1 to +4 ms window.
- Four frozen waveform features: peak amplitude, half-height width, peak sharpness, repolarization slope.
- Eight previous log-ISIs as timing context.
- Width-12 primary arms: timing only, timing + real waveform, timing + deterministic deranged waveform, timing + timing-residualized waveform.
- Training residuals generated leave-one-training-trajectory-out; held-out residualizer fit only to all training trajectories.
- Same event IDs/onset/availability times across primary arms, with event-identity SHA-256 receipts.
- Secondary baselines: waveform only, current observation, raw observed-input delays, privileged 19-compartment cable state.
- Independent Gaussian event-label control with frozen claim veto.

## Frozen full result

Full protocol completed with no scientific retuning after result inspection.

Primary condition: zero input noise, horizon 20.

| Arm | Mean NRMSE | Mean R² |
|---|---:|---:|
| raw input delays | 0.630064 | 0.591062 |
| timing + residual waveform | 0.655386 | 0.556855 |
| timing + real waveform | 0.687272 | 0.512788 |
| internal cable state | 0.748285 | 0.422873 |
| timing only | 0.764132 | 0.397984 |
| timing + shuffled waveform | 0.777386 | 0.376767 |
| current observed input | 0.818706 | 0.309413 |
| waveform only | 0.896009 | 0.173123 |

Predeclared evidence:

- **C0-A passed:** real waveform + timing beat timing-only and shuffled waveform in mean NRMSE and beat both on the same 4/4 held-out trajectories.
- **C0-B passed:** timing + residual waveform beat timing-only in mean NRMSE and on 4/4 held-out trajectories.
- Negative control passed its chance check: mean NRMSE 1.045339, mean R² -0.041728.
- Raw input delays remained better than the best waveform arm; no superiority-over-ordinary-memory claim is supported.

Event viability also passed. At the primary horizon, held-out seeds 100–103 supplied 269, 266, 268, and 267 scored events respectively, all well above the frozen minimum of 50.

Machine-readable evidence: `results/gate_c0_receipt.json`. The repository copy losslessly wraps the frozen 38 KB receipt as zlib+base64 with canonical SHA-256 `798243924a50abef58b8cc45e4574dd773009585445c43b271769141ade2253a`; byte-for-byte round-trip was verified before publication.

Human-readable interpretation: `docs/gate_c0_findings.md`.

## Commands actually run

Before the full result:

```text
python -m unittest tests.test_emitter -v
python -m unittest tests.test_gate_c0 -v
python -m unittest tests.test_gate_c0_receipt -v
python scripts/run_gate_c0.py --quick --output /tmp/gate_c0_quick.json
python -m unittest discover -s tests -v
```

The first two full-run wrappers were terminated by the execution harness at 120 s and 270 s before producing a receipt. No held-out result was written or inspected from those attempts. The exact same frozen command was then allowed to complete without a fixed wrapper kill timer:

```text
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_c0.py --output results/gate_c0_receipt.json
```

After the receipt existed:

```text
python -m unittest discover -s tests -v
```

Result: **23/23 tests passed**.

## Remote checkpoints

- Gate C0 design/spec branch point and planning history remain on this feature branch.
- HH emitter checkpoint: `91e6fc95edc60df2bceac054ece6b8d512a5de5a`
- event-control checkpoint: remote lineage through `b5b164de1a8a758283cc78ce2d2a858997d416cd`
- frozen-runner/test checkpoint: `b58da1e2b9e46ceeb4360a760d4c0ae996c344a3`
- frozen full receipt commit: `5d172ac5a9af8cca59f7ab346922249e0b56ddc4`
- Gate C0 findings commit: `6fb85e90aae22e3ed4af77596f3ebba1711f5fde`
- README result checkpoint: `7eea0f50b7cac50e6db9ef50b1d0cf53956e5f28`

## Scientific boundaries and unresolved caveats

- The active emitter is one illustrative HH compartment driven by an artificial fixed soma-to-current map.
- No axonal propagation, terminal calcium, vesicle release, postsynaptic neuron, or plasticity is modeled.
- The external forecasting reader remains supervised by delayed observed `x`; this is not a biological learning rule.
- Passing C0-A/B does not establish biological waveform coding in general.
- The residual-waveform arm outperforming the raw waveform arm is best read as a coordinate/readout effect, not creation of new information.
- Raw observed-input delays still outperform every spike-derived representation at the primary horizon.

## Precise next action

Complete Gate C0 Task 5 only: add an independent receipt comparator, rerun the exact frozen Gate C0 protocol in CI/local verification, record the successful workflow on the final feature head, and perform whole-branch review. Do **not** design or implement a synapse/full Gate C without a new explicit user request.
