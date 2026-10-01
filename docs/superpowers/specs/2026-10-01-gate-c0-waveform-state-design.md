# Gate C0 design — state-bearing spike emission

Date: 2026-10-01  
Status: written specification approved by user; implementation plan pending review  
Scope: design only; no numerical implementation authorized yet

## Purpose

Gate A established a clean negative result: the passive cable retains predictive information internally, but the declared one-dimensional soma-voltage history does not preserve enough of that advantage for the output-restricted reader to beat the present-input baseline.

Gate C0 asks whether the missing output transform could be active spike generation itself.

The central question is:

> **Does a spike carry a small state-dependent waveform payload that adds useful predictive information beyond spike timing alone?**

The intended claim is deliberately narrow. Gate C0 does not ask whether a neuron has learned an inverse model, whether waveform coding is universally used by the brain, or whether spikes transmit the full dendritic state. It asks whether an active emitter can compress some history-dependent internal state into waveform variation that remains usable after conditioning on the timing of the very same spikes.

## Motivation and source boundary

The immediate empirical motivation is Martin-Burgos et al., *Action potential waveforms are state-dependent* (bioRxiv 2026.09.15.751814, posted 21 September 2026; preprint, not peer reviewed).

That paper reports that within-neuron action-potential waveform variability is systematic rather than purely random, that waveform features predict properties of recent injected current, that some information persists over pre-spike windows reaching hundreds of milliseconds, and that waveform state is not reducible to firing rate or inter-spike interval alone. It also discusses prior evidence that presynaptic waveform width/duration can alter downstream synaptic currents.

Gate C0 uses those findings as motivation and as a constraint on what counts as a meaningful experiment. It does **not** import the paper's biological claims into the simulation by assumption.

## Relationship to earlier V3 gates

Gate A remains frozen and unchanged.

- V2: passive dendritic state retained history-dependent information.
- V3 Gate A: a scalar soma-voltage history did not expose enough of that state to beat the present observation under the frozen reader.
- Gate C0: insert an active state-dependent spike-emission stage after the passive sender and test whether waveform shape contributes predictive information beyond the timing of those exact same spikes.

Gate C0 is not the full Gate C described in the original brief. It deliberately stops before synaptic release, a postsynaptic neuron, plasticity, or a biological teaching pathway.

## Selected architecture

Use a one-way active emitter attached to the already-implemented passive cable.

```text
Lorenz x
  -> fixed V3 passive dendritic cable
  -> soma voltage s(t)
  -> one-way conductance-based active emitter
  -> spike events e_k = (time, waveform)
  -> event-based forecasting readers
  -> later observed x
```

The active stage receives the passive soma signal but does not feed current back into the passive cable. This keeps the V2/V3 retained-state mechanism unchanged and isolates the new hypothesis to the emission transform.

## Active emitter model

Use one classical Hodgkin-Huxley membrane compartment with the modern absolute-voltage convention:

- `C_m = 1 uF/cm^2`
- `g_Na = 120 mS/cm^2`, `E_Na = 50 mV`
- `g_K = 36 mS/cm^2`, `E_K = -77 mV`
- `g_L = 0.3 mS/cm^2`, `E_L = -54.387 mV`

Dynamics:

```text
C_m dV/dt = I_emit
            - g_Na m^3 h (V - E_Na)
            - g_K n^4 (V - E_K)
            - g_L (V - E_L)

dx/dt = alpha_x(V) (1 - x) - beta_x(V) x
```

with

```text
alpha_m = 0.1 (V + 40) / (1 - exp(-(V + 40)/10))
beta_m  = 4 exp(-(V + 65)/18)
alpha_h = 0.07 exp(-(V + 65)/20)
beta_h  = 1 / (1 + exp(-(V + 35)/10))
alpha_n = 0.01 (V + 55) / (1 - exp(-(V + 55)/10))
beta_n  = 0.125 exp(-(V + 65)/80)
```

Use the analytic limits at the removable singularities in `alpha_m` and `alpha_n`.

Initialize `V = -65 mV` and initialize `m`, `h`, and `n` to their steady-state values at `-65 mV`. Integrate with deterministic RK4 at `dt = 0.025 ms`.

The passive cable remains on Gate A's 1 ms world/cable schedule. During each 1 ms world interval the active emitter receives a piecewise-constant drive computed from the passive soma voltage.

For each noise condition separately, normalize passive soma voltage using training trajectories only:

```text
z_s(t) = (s(t) - mean_train_soma) / std_train_soma
```

Then use the frozen drive map

```text
I_emit(t) = 10 + 4 * tanh(z_s(t) / 2)   uA/cm^2
```

This is an illustrative coupling, not a fitted biological conductance. It is fixed before held-out evaluation and is not tuned against forecast accuracy, waveform separability, event counts on test trajectories, or test trajectories themselves.

## Spike event and feature availability

Define spike onset as an upward crossing of `0 mV`, with crossing time linearly interpolated between integration samples.

For each onset, store membrane voltage from `1.0 ms` before onset through `4.0 ms` after onset. Exclude an event when:

- the full waveform window crosses a trajectory boundary, or
- another spike onset occurs within its `(0, +4.0 ms]` post-onset feature window.

The waveform is available to the receiver only after `onset + 4.0 ms`. Every comparison arm uses this same decision time.

Let `a_k` be the first 1 ms world-sample index whose interval begins at or after that availability time. Forecast targets must be indexed from `a_k`, never from spike onset.

## Tiny-state payload

Compute a pre-spike baseline `b_k` as mean membrane voltage in `[-1.0, -0.5] ms` relative to onset.

Extract exactly four waveform features:

1. **Peak amplitude:** `V_peak - b_k`, where `V_peak` is the maximum voltage in `[0, +2.0] ms`.
2. **Half-height width:** time between the first rising and first falling crossings of `b_k + 0.5*(V_peak-b_k)`, using linear interpolation.
3. **Peak sharpness:** `V_peak - mean(V(t_peak-0.1 ms), V(t_peak+0.1 ms))`, with linear interpolation at the two sample times.
4. **Repolarization slope:** ordinary least-squares slope of voltage versus time over `[t_peak+0.5 ms, t_peak+2.0 ms]`.

If a feature cannot be defined for a detected event under these rules, exclude that event and record the reason. Do not substitute a different measurement rule.

These four features overlap the paper's emphasis on peak shape and repolarization while keeping the simulated payload small and deterministic. Do not add or remove waveform features after held-out evaluation.

## Event-centric forecasting dataset

Each scored example corresponds to one valid emitted spike.

For spike `k`, require eight completed inter-spike intervals ending at that spike:

```text
[t_k-t_(k-1), t_(k-1)-t_(k-2), ..., t_(k-7)-t_(k-8)]
```

The timing context is the logarithm of these eight positive intervals. Normalize timing features using training events only.

The target for horizon `h` is

```text
o(a_k + h)
```

where `a_k` is the feature-availability index defined above.

Use Gate A's forecast horizons `h in {1, 5, 20}`. The primary condition is `h = 20`, zero input noise.

Retain Gate A's Lorenz world, training trajectories `10..15`, held-out trajectories `100..103`, input-noise levels `0` and `0.02`, and whole-trajectory separation.

A trajectory is viable for the primary analysis only if at least **50 scored events** remain after waveform validity, eight-ISI history, and target-boundary exclusions. If any of the six training trajectories or any of the four held-out trajectories has fewer than 50 primary-condition events, report the event counts and classify the fixed Gate C0 emission channel as **not viable for the declared primary test**. Do not tune the drive map to rescue it.

## Primary comparison arms

All four primary arms use the **same valid spike events, exact same spike times, and exact same feature-availability times**.

### 1. Timing only

- eight log-ISI timing features,
- four zero-padding columns.

Width: 12.

### 2. Timing + real waveform

- the same eight timing features,
- the four real waveform features of the current spike.

Width: 12.

This is the main tiny-state arm.

### 3. Timing + shuffled waveform

- identical timing context,
- the four waveform vectors after deterministic within-trajectory permutation.

Use shuffle seed `500000 + trajectory_seed` for each trajectory. Training and held-out trajectories are shuffled independently because their trajectory seeds differ. The permutation must preserve every four-feature waveform vector exactly once while breaking its event pairing.

Width: 12.

This is the main equal-dimension nuisance control.

### 4. Timing + residual waveform

Predict waveform from timing without using forecast targets.

Use V3's degree-two ridge readout with ridge factor `0.001` to predict the four waveform features from the eight timing features.

For **training-event residuals**, use leave-one-training-trajectory-out residualization: fit on five training trajectories and predict the sixth, repeated across all six. This prevents the forecasting reader from receiving in-sample residuals created by a model trained on the same event.

For **held-out residuals**, fit the timing-to-waveform model once on all six training trajectories and apply it to each held-out trajectory.

The forecasting reader receives eight timing features plus four residual waveform features. Width: 12.

The residualizer never sees future forecast targets, hidden Lorenz coordinates, or held-out waveform targets during fitting.

## Secondary comparison arms

Report these but do not use them to establish the primary tiny-state claim:

- **Waveform only:** four waveform features plus eight zero-padding columns.
- **Current observed input:** observed `x` at `a_k`, padded to width 12.
- **Raw input delays:** 12 causal observed-`x` samples ending at `a_k`.
- **Internal cable state:** all 19 passive compartment voltages at `a_k`. This is privileged and has a different width; it cannot support an equal-budget superiority claim.

## Forecast reader

Reuse V3's degree-two ridge readout, ridge factor `0.001`, intercept handling, and training-only preprocessing.

Fit every forecasting arm against later **observed `x`** on training trajectories only. Hidden Lorenz `y,z` remain excluded from forecasting fits, feature selection, residualization, and hyperparameter choice.

Report NRMSE against clean future `x`, normalized by training observed-`x` scale, plus per-trajectory R2 as in Gate A.

## Predeclared evidence criteria

Gate C0 separates two claims.

### Claim C0-A — waveform adds useful information beyond timing

At the primary condition (`noise = 0`, `h = 20`), timing + real waveform must:

1. have lower mean held-out NRMSE than timing-only,
2. have lower mean held-out NRMSE than timing + shuffled waveform,
3. on the **same at least three of four held-out trajectories**, have lower NRMSE than both timing-only and timing + shuffled waveform.

If these conditions fail, Gate C0 provides no evidence that the waveform payload is useful beyond spike timing under this model and reader.

### Claim C0-B — useful waveform information is not reducible to recent timing context

At the primary condition, timing + residual waveform must:

1. have lower mean held-out NRMSE than timing-only, and
2. have lower NRMSE than timing-only on at least three of four held-out trajectories.

C0-B may fail even if C0-A passes. In that case the interpretation is that waveform is useful but its useful variation is largely predictable from recent timing context.

Neither claim authorizes a statement that biological neurons generally use waveform coding.

## Required controls

Implementation must test or record all of the following:

1. **Same-event identity:** all primary arms use exactly the same event indices, onset times, and availability times.
2. **Causality:** changing world input after an event's `+4 ms` availability time cannot alter that completed event or its features.
3. **Feature availability:** targets are indexed from `a_k`; no waveform sample later than the decision time enters a feature.
4. **Data separation:** held-out events and future targets never affect normalization, residualization, readout fitting, or feature choice.
5. **Shuffle integrity:** each within-trajectory permutation changes event pairing while preserving every waveform vector exactly once.
6. **Residualization integrity:** training residuals are out-of-trajectory predictions; held-out residualizers are fit only on training trajectories.
7. **Independent hidden-label negative control:** a separate evaluation decoder predicts an independent Gaussian event label; it must remain chance-like and never feed a forecasting arm.
8. **Degenerate cases:** no-spike, single-spike, overlapping-spike, constant timing, and constant waveform cases fail cleanly or remain finite as appropriate.
9. **Event viability:** record event counts and every exclusion reason per trajectory.
10. **Reproducibility:** record emitter equations/constants, source hashes, seeds, software versions, waveform-feature distributions, and per-trajectory results.

## Failure localization

A negative result must be localized, not generalized.

- If any required trajectory has fewer than 50 scored primary events, the fixed emission channel is not viable for this declared test.
- If waveforms vary but real waveform does not beat shuffled waveform, the variation is not useful for the declared forecasting task.
- If real waveform beats shuffled waveform but residual waveform fails, waveform carries state that is largely explainable by recent timing history.
- If residual waveform passes, Gate C0 supports the narrow claim that same-event spikes can carry a small additional state-dependent payload useful for prediction.

Do not alter Gate A, retune the active-emitter mapping, expand the waveform feature set, change event selection, or introduce a synapse in response to a negative held-out result.

## Explicit non-goals

Gate C0 does not implement or claim:

- synaptic vesicle release or calcium dynamics,
- a postsynaptic neuron,
- spike-waveform propagation along an axon,
- a biological learning rule,
- active dendritic conductances,
- adaptive morphology,
- consciousness or field-based transmission,
- a complete inverse model of the world.

Those are separate hypotheses.

## Deliverables after implementation authorization

A later implementation plan should produce:

- tested active-emitter module,
- deterministic spike/waveform extraction,
- event-centric dataset builder,
- timing, real-waveform, shuffled-waveform, and residual-waveform readers,
- secondary baselines,
- full frozen receipt,
- human-readable findings,
- CI rerun and scientific-payload comparison.

No implementation should begin from this spec until the user approves a concrete implementation plan and execution approach.
