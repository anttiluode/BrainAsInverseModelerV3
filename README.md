# BrainAsInverseModelerV3 — From retained state to useful output

**Can a receiver learn useful predictions of a hidden process from the signal emitted by a history-bearing dendritic cable?**

V2 showed that an illustrative passive cable can retain information about hidden causes in its internal voltages. V3 asks a stricter question: does useful state survive the sender's output bottleneck, and can a receiver use it without hidden-state training labels?

## Gate C0 result — a tiny state-bearing spike payload

Gate C0 is now measured. It keeps the passive V3 sender fixed and adds a one-way classical Hodgkin–Huxley emitter. Every primary comparison uses the **same emitted spikes, onset times, and decision times**. The only extra information supplied to the waveform arms is four measurements of the current spike: peak amplitude, half-height width, peak sharpness, and repolarization slope.

The two predeclared waveform criteria **passed**.

At zero input noise and the primary 20-sample forecast horizon:

| Receiver information | Mean NRMSE ↓ |
|---|---:|
| Raw observed-input delays | **0.6301** |
| Timing + residual waveform | **0.6554** |
| Timing + real waveform | **0.6873** |
| Internal cable state | 0.7483 |
| Timing only | 0.7641 |
| Timing + shuffled waveform | 0.7774 |
| Current observed input | 0.8187 |
| Waveform only | 0.8960 |

Real waveform + timing improved mean NRMSE by **10.1%** relative to timing alone and beat both timing-only and the dimension-matched shuffled-waveform control on **4/4 held-out trajectories**. The timing-residualized waveform arm improved on timing alone by **14.2%** and also won on **4/4** trajectories. The independent Gaussian-label control remained chance-like (NRMSE 1.0453, R² -0.0417), so the frozen claim veto did not fire.

The important boundary is equally clear: this is evidence that a small event-specific waveform payload can carry predictive information beyond spike timing in this synthetic mechanism. It is **not** evidence that biological neurons generally use this code, and raw observed-input delays remain better than the best waveform arm.

Read [`docs/gate_c0_findings.md`](docs/gate_c0_findings.md) and [`results/gate_c0_receipt.json`](results/gate_c0_receipt.json) for the frozen result.

## Gate A result

Gate A asked whether a receiver restricted to causal soma-voltage history could forecast later observed `x`. Hidden Lorenz `y,z` never entered forecast training.

The predeclared primary Gate A test **did not pass**.

At zero input noise and a 20-sample forecast horizon:

| Representation | Mean NRMSE ↓ |
|---|---:|
| Raw input delays | **0.6406** |
| Internal cable state | **0.7441** |
| Present input | 0.8160 |
| Soma history | 0.8314 |
| Instantaneous soma | 0.9492 |

The internal cable state predicted the future better than the current observation, so useful predictive information remained inside the sender. But the declared soma-history reader did not preserve that advantage. This established a separation between **retention** and **output readability**.

Gate C0 does not overwrite or rescue Gate A. It tests a new nonlinear output transform and finds that active spike shape can expose additional state beyond the timing of the same spikes.

Gate A details: [`docs/findings.md`](docs/findings.md) and [`results/gate_a_receipt.json`](results/gate_a_receipt.json).

## Reproduce

Install and run the unit suite:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Gate A:

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_a.py --output /tmp/gate_a_receipt.json
python scripts/compare_receipts.py results/gate_a_receipt.json /tmp/gate_a_receipt.json
```

Gate C0 (the full HH run is substantially slower):

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_c0.py --output /tmp/gate_c0_receipt.json
python scripts/compare_gate_c0_receipts.py results/gate_c0_receipt.json /tmp/gate_c0_receipt.json
```

The Gate C0 protocol uses training trajectories 10–15, held-out trajectories 100–103, forecast horizons 1/5/20, input-noise levels 0/0.02, and a frozen one-way HH emitter at 0.025 ms integration step.

## Current progression

| Gate | Question | Status |
|---|---|---|
| A — scalar output and prediction | Does soma-voltage history support learned prediction on new trajectories? | **Measured: primary criterion failed** |
| C0 — state-bearing spike | Does waveform add useful information beyond timing of the same spikes? | **Measured: C0-A and C0-B passed** |
| B — interruptions and ambiguity | Does retained distinction help through a sensory gap? | Not designed/executed yet |
| C — synaptic transmission | Does the waveform distinction survive presynaptic release and reception? | Not designed/executed yet |

No later gate starts automatically from the positive C0 result.

## Scientific boundary

The passive cable and active emitter are illustrative mechanisms, not fitted biological neurons. Forecast readers are external supervised quadratic ridge models trained using delayed observations; no biological teaching pathway is claimed. Gate C0 does not model axonal propagation, presynaptic calcium/vesicle release, a postsynaptic neuron, or plasticity. A passing reader establishes information access under the declared simulation and controls, not a universal neural code or a complete inverse model.

## Lineage

[BrainAsInverseModeler](https://github.com/anttiluode/BrainAsInverseModeler) →
[BrainAsInverseModelerV2](https://github.com/anttiluode/BrainAsInverseModelerV2) →
this repository.

[Varjoluotain](https://github.com/anttiluode/Varjoluotain) supplies the inverse-problem lesson: the measurement channel determines which hidden distinctions reach the observer, and a good forward fit does not uniquely establish hidden causes.
