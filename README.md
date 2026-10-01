# BrainAsInverseModelerV3 — From retained state to useful output

**Can a receiver learn useful predictions of a hidden process from the signal emitted by a history-bearing dendritic cable?**

V2 showed that an illustrative passive cable can retain information about hidden causes in its internal voltages. V3 asks a stricter question: does useful state survive the sender's output bottleneck, and can a receiver use it without hidden-state training labels?

## Gate A result

Gate A is now measured. The receiver sees only a causal history of soma voltage and is trained against later observed `x` values. Hidden Lorenz `y,z` never enter forecast training.

The predeclared primary test **did not pass**.

At zero input noise and a 20-sample forecast horizon:

| Representation | Mean NRMSE ↓ |
|---|---:|
| Raw input delays | **0.6406** |
| Internal cable state | **0.7441** |
| Present input | 0.8160 |
| Soma history | 0.8314 |
| Instantaneous soma | 0.9492 |

The internal cable state predicts the future better than the current observation, so useful predictive information is retained inside the sender. But the declared soma-history reader does not preserve that advantage. It beats both required baselines on only 1/4 held-out trajectories, versus the frozen requirement of at least 3/4.

This is the main V3 result so far: **retention and downstream readability are different claims**.

Read the full interpretation in [`docs/findings.md`](docs/findings.md) and the machine-readable evidence in [`results/gate_a_receipt.json`](results/gate_a_receipt.json). The committed receipt uses a lossless compact schema: arm and metric names are stored once, while all full-precision per-trajectory values remain present.

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_a.py
```

The published protocol uses training trajectories 10–15, held-out trajectories 100–103, forecast horizons 1/5/20, and input-noise levels 0/0.02. All six readers have width 19 and use the same degree-two ridge readout.

## What V2 established

The pinned V2 source is commit `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`.

V2 found that diverse branch dynamics can make known-timing hidden pulse amplitudes recoverable from a soma trace, while symmetric branches collapse source identity. Its internal 19-compartment state also carried information about withheld Lorenz coordinates. Ordinary delay samples performed better than the cable on that benchmark.

V3 removes two privileges from the actual receiver: no direct access to the 19 internal voltages and no hidden-state labels as training targets.

## Current progression

| Gate | Question | Status |
|---|---|---|
| A — output and prediction | Does soma history support learned prediction on new trajectories? | **Measured: primary criterion failed** |
| B — interruptions and ambiguity | Does retained distinction help through a sensory gap? | Not designed/executed yet |
| C — neuronal transmission | Do useful distinctions survive spike generation and reception? | Not designed/executed yet |

Gate A's negative result is preserved as-is. It does not authorize automatically changing the output code or moving into Gates B/C.

## Scientific boundary

This is an illustrative passive-cable mechanism, not a fitted biological neuron. The external forecasting reader is supervised with delayed observations; no biological teaching pathway is claimed. The result does not establish that dendrites implement Takens embeddings, that soma voltage is the brain's relevant output code, or that predictive information cannot survive more realistic active/spiking transmission.

## Lineage

[BrainAsInverseModeler](https://github.com/anttiluode/BrainAsInverseModeler) →
[BrainAsInverseModelerV2](https://github.com/anttiluode/BrainAsInverseModelerV2) →
this repository.

[Varjoluotain](https://github.com/anttiluode/Varjoluotain) supplies the inverse-problem lesson: the measurement channel determines which hidden distinctions reach the observer, and a good forward fit does not uniquely establish hidden causes.
