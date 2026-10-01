# V3 research brief — retained state, emitted signal, prediction

Date: 2026-10-01  
Status: proposed design; implementation deliberately paused  
Scope of this commit: establish the question and handoff only

## Intended outcome

The user wants a small, resumable successor to V2, with a question that a later session can follow through. The immediate request is documentation, not another long build.

V1 asked what a neuron can retain, emit, and make recoverable downstream. V2 tested retention and a calibrated soma-trace inverse. V3 should connect retained history to useful output without granting the receiver direct access to every compartment or hidden-state training labels.

## Main question

**Can a receiver learn useful predictions of an observable hidden process from the emitted signal of a dendritic cable, using later observations as its training targets?**

The first test separates three claims:

1. **Retention:** the sender's internal state carries predictive information.
2. **Transmission:** enough of that information is accessible in soma voltage history.
3. **Use:** a declared reader can turn the accessible history into predictions on new trajectories.

Success at the third claim with an external supervised reader is an information-access result. It does not establish a biological learning rule or a full neuronal world model.

## Starting evidence

Pin reuse to V2 commit `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`:
[code](https://github.com/anttiluode/BrainAsInverseModelerV2/tree/795be2c7e8c4ba25112983fdc9ac2ad00ca232d0),
[receipt](https://github.com/anttiluode/BrainAsInverseModelerV2/blob/795be2c7e8c4ba25112983fdc9ac2ad00ca232d0/results/receipt.json).

Its 19-compartment passive cable uses six diverse branches and exact constant-input RC transitions. In the hidden-state benchmark, only Lorenz x drives the cable. An external quadratic decoder recovers y,z from all compartment voltages.

Reported mean errors are 0.1774 for diverse cable state, 0.6216 for present x, and 0.0777 for raw delays. An instantaneous soma voltage gives 0.6777. This last result does not determine what a history of soma voltage can expose.

All values above belong to V2. V3 has no measurements.

## Alternatives and selected first step

| Approach | What it resolves | Main cost or limitation |
|---|---|---|
| Continuous soma voltage and a fixed predictive reader | Whether useful information survives the output channel | External readout and delayed teaching targets remain |
| Spiking sender and receiving neuron immediately | Transmission through more realistic constraints | New nonlinear dynamics would obscure where failure occurs |
| Adaptive morphology or learned branch parameters immediately | Whether the instrument can improve its own representation | Adds optimization before establishing a readable output |

Start with continuous soma voltage. Keep the existing cable fixed. Test prediction before introducing spike generation or growth. Spiking and intrinsic learning are later gates, not additions to the first implementation.

## Gate A — continuous output to predictive reader

### Proposed frozen protocol

These are design values for a later plan. Record any requested revisions before collecting V3 results.

- World: V2 Lorenz parameters (10, 28, 8/3), RK4 step 0.01.
- Sender: V2 diverse passive cable, driven identically at its six distal ports by 0.01 nA times normalized observed x.
- Timing: one world sample drives one 1 ms cable interval. This is an illustrative mapping, not a fitted biological timescale.
- Trajectories: training seeds 10–15; held-out seeds 100–103.
- Schedule: 1,000 world burn-in steps, then 4,000 observed steps. Start scored features at index 500, stride 4. For each horizon, exclude indices whose targets fall outside the trajectory.
- Input noise: standard deviations 0 and 0.02 times the clean training-x standard deviation. Preserve V2's noise seeds: 200000 + trajectory seed + integer(noise level × 10000).
- Feature width: 19 for every reader. History features use the current sample and 18 previous samples at stride 2.
- Decoder: V2's degree-two ridge readout, ridge factor 0.001, intercept unpenalized. Fit preprocessing and coefficients on training trajectories only; no held-out tuning.
- Forecast horizons: 1, 5, and 20 samples. The primary comparison is the 20-sample horizon with zero input noise. All other cases remain reported secondary comparisons.

### Training and access

Let observed input be o(t), cable state be v(t), and emitted signal be soma voltage s(t).

At prediction time t, the output receiver's features may use s(t) and earlier emitted samples only. It receives neither o(t), future samples, hidden y,z, nor branch voltages.

Fit its reader against o(t+h), available later as a delayed teaching target on training trajectories. This is observation-trained supervision. An actual biological route delivering this target has not been specified.

Use observed training data for normalization. Clean simulator x and hidden y,z must not affect receiver fitting, feature selection, or hyperparameter choice. Clean x(t+h) is allowed only as evaluation truth. The simulator may use clean training statistics to define a channel's declared noise amplitude.

Fit each noise condition separately, with the same decoder settings. Report prediction NRMSE against clean future x, normalized by the training observed-x standard deviation, and per-trajectory R². Hold out entire trajectories.

### Required comparison arms

| Arm | Features at t | Purpose |
|---|---|---|
| Present input | Current observed x, padded to width 19 | Instantaneous baseline |
| Raw input delays | 19 causal observed-x samples | Ordinary memory baseline |
| Exponential input traces | V2's 19 causal traces | Simple physical filter comparison |
| Internal cable state | 19 compartment voltages | Privileged comparison for sender retention |
| Instantaneous soma | Current soma voltage, padded to width 19 | Single-sample output bottleneck |
| Soma history | 19 causal soma samples | Actual output-restricted receiver |

All arms train on the same future-observation targets and scored training indices. The internal-state arm is a comparison, not a mathematical upper bound: the soma-history arm has access to a temporal sequence.

### Evidence and failure criteria

- Prediction evidence requires the soma-history arm to outperform both the instantaneous-soma and present-input baselines on mean held-out primary NRMSE, with an improvement on at least three of four test trajectories.
- Report every arm, horizon, noise condition, and trajectory. Compare with raw delays even if delays win.
- If internal state helps but soma history does not, localize the failure to accessible output, sampling, or this reader; do not declare the hidden information biologically untransmittable.
- If neither internal state nor output improves prediction, the V2 y,z-decoding result has not carried over to this predictive task.
- A superiority claim over ordinary memory requires additional evidence; passing the first comparison is insufficient.
- Use “learned observational forecast” for a passing external reader. Reserve biological-learning claims for a separately implemented and tested mechanism.

## Gate B — same present, interruption, ambiguity

Deferred until Gate A is reported.

Find held-out moments with nearly equal present input and soma value but different histories and future observations. Report both successful and failed receiver distinctions, with the pair-selection rule declared in advance.

Specify a finite sensory gap and compare continued sender state, reset sender state, and matched direct-input memory. Zero drive, frozen voltage, and a missing-sample marker are different gap models; choose and document one before running.

This gate asks whether history matters when new evidence stops. It must compare against memory baselines that retain their own history through the same gap.

## Gate C — neuronal emission and reception

Deferred; no spiking model is chosen in this brief.

Specify spike generation, synaptic reception, reader plasticity, the teaching signal or objective, and information budgets in a new design. Compare rate/timing access with any waveform access.

The question becomes whether distinctions needed for prediction survive the complete sender-to-receiver pathway. State-dependent waveforms, distributed fields, and consciousness remain hypotheses outside Gate A.

## Verification requirements for later implementation

The implementation plan must include checks for:

1. Causality: changing future input cannot alter earlier sender states or receiver features.
2. Separation: fitting cannot access held-out targets or hidden-coordinate labels.
3. Timing: target indices and sender output use the declared post-interval convention.
4. Negative control: a separate evaluation probe checks that an independent hidden variable never entering the observed process stays unrecoverable on held-out trajectories. That probe may fit independent labels; its features, targets, and weights must never feed the forecasting reader.
5. Constant and degenerate signals: normalization and rank deficiency stay finite.
6. Reproducibility: exact source hashes, seeds, settings, versions, and per-trajectory results accompany the full receipt.

The first runnable checkpoint should validate reuse of the pinned V2 core and its existing controls. It is not permission to rerun or port that core during this documentation-only session.

## Deliverables and stopping point

Current deliverables: README, AGENTS instructions, this brief, and a progress/handoff record. No implementation plan, dependencies, simulation, CI, or website belongs to this commit.

After a later explicit start request, prepare a bounded Gate A implementation plan and carry out only the authorized work. Publish a verified experiment and readable findings before deciding whether a demo or another gate is useful.

**Current stopping point: documents published; implementation not started.**
