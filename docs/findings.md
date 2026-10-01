# Gate A findings — retained state versus emitted prediction

Date: 2026-10-01  
Experiment: continuous soma output to an observation-trained predictive reader  
Receipt: [`results/gate_a_receipt.json`](../results/gate_a_receipt.json)

## Question

Can a receiver restricted to the history of a sender's emitted soma voltage learn useful forecasts of the observed process, without branch-voltage access or hidden-state training labels?

Gate A keeps the V2 passive cable fixed. Only Lorenz `x` is observed and drives the cable. Every forecasting reader is trained against a later **observed `x`** value. Hidden Lorenz `y,z` never enter forecasting training. Whole trajectories are held out for testing.

The primary condition was frozen before the full run: zero input noise, a 20-sample forecast horizon, and four held-out trajectories. Evidence for output-restricted prediction required soma history to beat both instantaneous soma and present input in mean NRMSE and on at least three of four held-out trajectories.

## Primary result: Gate A did not pass

| Arm | Mean NRMSE at h=20, noise=0 ↓ |
|---|---:|
| Raw input delays | **0.6406** |
| Internal cable state | **0.7441** |
| Exponential input traces | 0.7899 |
| Present input | 0.8160 |
| Soma history | 0.8314 |
| Instantaneous soma | 0.9492 |

Soma history beat instantaneous soma, showing that the emitted trace contains useful temporal information. It did **not** beat the present-input baseline in mean error, and it beat both required baselines on only one of four test trajectories (seed 102). The predeclared criterion therefore fails.

This is not a failure of retention inside the sender. The privileged 19-compartment cable state reaches 0.7441 NRMSE, better than the present input's 0.8160 on the same future-prediction task. What failed is the stronger V3 step: this particular one-dimensional soma output history, sampled and read as specified, did not expose that retained predictive information well enough to outperform the present observation.

## Horizon structure

Zero-noise mean NRMSE:

| Arm | h=1 | h=5 | h=20 |
|---|---:|---:|---:|
| Present input | 0.0551 | 0.2693 | 0.8160 |
| Raw input delays | **0.0163** | **0.0844** | **0.6406** |
| Exponential input traces | 0.0805 | 0.2272 | 0.7899 |
| Internal cable state | 0.0460 | 0.1715 | 0.7441 |
| Instantaneous soma | 0.6404 | 0.7411 | 0.9492 |
| Soma history | 0.1655 | 0.3139 | 0.8314 |

Three distinctions matter.

First, the internal cable state consistently improves on the present input. The passive dendritic dynamics therefore retain predictive information relevant to future observations, not only information decodable into V2's hidden `y,z` labels.

Second, the soma bottleneck is severe. One soma sample is poor at every horizon, and a 19-sample soma history recovers some of the lost information but not enough to match the internal compartment ensemble or ordinary input delays.

Third, explicit delay coordinates remain the strongest representation in this benchmark. Gate A therefore supplies no evidence that this passive cable is a superior predictive memory. Its value here is as a physical history-bearing mechanism whose internal observability and external observability are demonstrably different.

## Noise

Adding input noise with standard deviation 0.02 times the clean training-`x` standard deviation barely changes the cable and soma results. At h=20, soma history changes from 0.8314 to 0.8315 NRMSE and internal cable state from 0.7441 to 0.7450. Raw delays degrade from 0.6406 to 0.6640 but remain best.

This does not establish broad robustness; only one declared noise level was tested.

## Negative control

An evaluation-only decoder tried to predict an independent Gaussian future label from zero-noise soma history. The label never affects Lorenz `x`, the cable, or any forecasting reader.

- Mean NRMSE: **0.9947**
- Mean R²: **-0.0045**

That is the expected chance-like outcome. The negative-control model and weights are separate from the forecasting readers.

## What Gate A means

V2 established **retention**: internal cable voltages contain history-dependent distinctions. Gate A now separates retention from **transmission/readability**.

The result is:

> A passive dendritic cable can retain predictive state that is visible in its compartment ensemble, while a single emitted soma-voltage channel can discard enough of that geometry that a downstream history reader no longer gains over the current observation.

That is a useful narrowing of the inverse-model picture. A sender having an informative internal state does not imply that a downstream receiver can recover it from whatever signal crosses the output bottleneck.

The Varjoluotain lesson survives in a more biological form: the measurement channel determines which hidden distinctions remain identifiable. Here the "instrument" is not only the dendritic tree; it is the dendritic tree **plus the soma-output projection plus the receiver's temporal window**.

## Claim boundary

This experiment does not show that a neuron learned an inverse model. The cable parameters are fixed, and the receiver is an external degree-two ridge reader trained with delayed observational targets. No biological mechanism delivering that teaching signal is specified.

It also does not show that predictive state is biologically untransmittable. Gate A tests one passive cable, one soma voltage channel, one 19-sample stride-2 window, and one reader class. A different output code, active conductances, spikes, synapses, or learned morphology could change the answer, but those are new hypotheses rather than repairs to this result.

No constants were tuned after the frozen held-out run. Gates B and C remain unimplemented.
