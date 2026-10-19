# Gate P: a readable return response did not improve prediction

2026-10-19. Frozen full-protocol result. Both P-access and P-forecast failed.
Protocol/implementation were committed as `099984a` before full evaluation.

## What was tested

The existing passive 19-compartment encoder was unchanged. At each query its
state was copied into a separate interrogation episode. Local branch voltage
set a held, bounded synthetic leak-conductance change. One arm received a
0.01 nA one-ms soma pulse; the matched arm had identical gates and no pulse.
Both supplied nineteen soma samples to the same quadratic-reader class.

All arms had a nineteen-sample sensory blackout. Readout was available at q+19;
the forecast target was x at q+39, twenty samples beyond availability. Historical
controls stopped observing at q. These numbers therefore cannot be compared
directly with the earlier Gate A h=20 table, which had no such blackout.

Six training trajectories and four separate test trajectories were used, with
866 queries per trajectory. The test seeds are the existing V3 benchmark seeds,
not a new confirmation cohort. Only future observed x entered training. The
local gate did not use forecast targets. Its equation and constants are in the
[predeclared protocol](gate_p_protocol.md).

## Primary result

Mean NRMSE at input noise zero; lower is better:

| Arm | NRMSE |
|---|---:|
| Active gate, no pulse | **0.991765** |
| Active gate, pulse | 0.992047 |
| Present input | 0.993123 |
| Raw input delays | 0.999127 |
| Fixed cable, no pulse | 1.000201 |
| Fixed cable, pulse | 1.000201 |
| Internal cable state (privileged) | 1.007594 |
| Soma history | 1.023574 |
| Reset state, pulse | 1.027299 |

The pulse arm was slightly worse than the matched active-no-pulse arm on **all
four** test trajectories. It won against all three matched controls jointly on
**zero of four**, below the required three. P-access fails. P-forecast also fails.
The error difference is small; this experiment does not establish a general
harmful effect of pinging. It supplies no evidence for a useful pulse advantage.

The active-no-pulse arm's small improvement over the passive arms cannot be
credited to the returning pulse. This is exactly why it was a primary control.
All forecast errors are near one at this blackout-plus-forecast separation;
no representation demonstrates strong forecasting here under the fixed reader.

Secondary 2% input-noise condition agrees: active-no-pulse 0.991448, active-pulse
0.991729, fixed-no-pulse and fixed-pulse both 0.999976.

## Mechanism and negative controls

- The fixed-cable incremental echo was state-independent: maximum range
  `3.997e-15 mV` across queries.
- The active-gate incremental echo varied with state: maximum range
  `0.015118 mV` across queries.
- Two constructed states with equal initial soma voltage produced active
  incremental echoes differing by `0.001154 mV`; the fixed-cable difference
  was `1.665e-16 mV`.
- Resetting the full state made the pulse trace identical across queries.
- Independent Gaussian-label decoding remained chance-like: NRMSE `0.990504`,
  mean R² `-0.001615`.

Thus the proposed response mechanism is present, but its usefulness criterion
failed. No primary reader received counterfactual pulse-minus-no-pulse subtraction;
that difference was calculated only to audit the simulated mechanism.

## Interpretation and boundaries

This does not rescue Gate A's output bottleneck and does not invalidate its
retention result. It also does not refute all returning-probe approaches.
The result concerns one engineered voltage-to-held-conductance mapping, one
pulse, a nineteen-sample blackout, a twenty-sample forecast after readout, and
one quadratic reader class. The mechanism is a snapshot assay using copies of
the encoder state, not a deployed continuous feedback loop or learned memory.
There is no demonstrated biological learning, object segmentation, image
generation, or superiority over conventional memory.

The useful distinction is: **a state-dependent response can exist without
adding useful information for the declared downstream prediction task.**

## Reproduction

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_p.py --output /tmp/gate_p_verify.json
python scripts/compare_gate_p_receipts.py results/gate_p_receipt.json /tmp/gate_p_verify.json
python -m unittest discover -s tests -v
```

Windows: `python scripts/run_gate_p.py --output gate_p_verify.json` (CPU only).
The optional `--quick` mode defaults to a temporary smoke receipt and is not the
full experiment. The [full JSON receipt](../results/gate_p_receipt.json) retains
both noise conditions, individual trajectory results, timing, hashes, controls,
normalization provenance and the failed verdicts. No scientific constants were
changed after inspecting the full result.
