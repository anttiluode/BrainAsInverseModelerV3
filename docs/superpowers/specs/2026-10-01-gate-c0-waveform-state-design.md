# Gate C0 design — state-bearing spike emission

Date: 2026-10-01  
Status: approved in chat; written-spec review pending  
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

Data flow:

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

Use a single classical Hodgkin-Huxley-style membrane compartment with standard Na, K and leak conductances:

- `C_m = 1 uF/cm^2`
- `g_Na = 120 mS/cm^2`, `E_Na = 50 mV`
- `g_K = 36 mS/cm^2`, `E_K = -77 mV`
- `g_L = 0.3 mS/cm^2`, `E_L = -54.387 mV`

Use the standard Hodgkin-Huxley `m`, `h`, and `n` gating equations and integrate at `dt = 0.025 ms`.

The passive cable remains on Gate A's 1 ms world/cable schedule. During each 1 ms world interval the active emitter receives a piecewise-constant drive computed from the passive soma voltage.

Normalize passive soma voltage using training trajectories only:

```text
z_s(t) = (s(t) - mean_train_soma) / std_train_soma
```

Map it to active-emitter current with one frozen monotone transform:

```text
I_emit(t) = 10 + 4 * tanh(z_s(t) / 2)   uA/cm^2
```

This mapping is an illustrative coupling, not a fitted biological conductance. It is fixed before held-out evaluation and is not tuned against forecast accuracy, waveform separability, or test trajectories.

If this fixed mapping produces too few valid spikes for the declared analysis, Gate C0 fails as specified. Do not search gain/bias values after seeing held-out outcomes.

## Spike event and feature availability

Define spike onset as an upward crossing of `0 mV` in the active-emitter membrane voltage.

For each detected spike, store a waveform window from `1.0 ms` before onset through `4.0 ms` after onset. Events whose windows overlap the trajectory boundary are excluded.

The waveform is considered available to the receiver only after the full `+4.0 ms` post-onset window has elapsed. Forecast targets must occur after that availability time.

This convention prevents the waveform reader from using samples that are still in the future relative to its declared decision time.

## Tiny-state payload

Extract four robust waveform features from each spike:

1. peak voltage,
2. half-height width,
3. peak sharpness measured over a fixed local neighborhood around the peak,
4. repolarization slope over a fixed post-peak interval.

These features intentionally overlap the paper's emphasis on peak shape and repolarization dynamics while remaining simple enough to test deterministically in a simulated Hodgkin-Huxley waveform.

Do not add or remove waveform features after held-out evaluation. Any richer parameterization is a later experiment.

## Event-centric forecasting dataset

Gate C0 is event-centric rather than sample-centric.

Each scored example corresponds to one emitted spike. Exclude events until at least eight previous spikes exist.

For each event `k`, define an eight-dimensional timing context from the logarithms of the previous eight inter-spike intervals. Normalize timing features using training events only.

Let `a_k` be the first 1 ms world-sample index whose interval begins after the waveform's declared `+4.0 ms` availability time. The forecasting target at horizon `h` is the later observed value:

```text
o(a_k + h)
```

Use the same forecast horizons as Gate A: `h in {1, 5, 20}` world samples. The primary condition is `h = 20`, zero input noise.

Retain Gate A's training trajectories `10..15`, held-out trajectories `100..103`, Lorenz world, input-noise levels `0` and `0.02`, and whole-trajectory separation.

## Primary comparison arms

All timing/waveform arms use the **same spike events and exact same spike times** from one active-emitter simulation.

### 1. Timing only

Features:

- eight previous log-ISI values,
- four zero padding columns.

Width: 12.

This is the baseline for what can be predicted from recent spike timing alone.

### 2. Timing + real waveform

Features:

- the same eight timing features,
- the four real waveform features of the current spike.

Width: 12.

This is the main tiny-state arm.

### 3. Timing + shuffled waveform

Features:

- identical timing context,
- the same four waveform-feature columns after deterministic within-trajectory permutation.

Use independent fixed shuffle seeds for training and held-out trajectories. Preserve waveform-feature marginal distributions and feature count while breaking event-specific state alignment.

Width: 12.

This is the main dimension/capacity control.

### 4. Timing + residual waveform

First fit, on training events only, a separate ridge model predicting the four waveform features from the eight timing-context features. Subtract those predictions to obtain waveform residuals.

The forecasting reader receives:

- the eight timing features,
- four residual waveform features.

Width: 12.

This arm asks whether waveform contributes information not already predictable from recent timing context.

The timing-to-waveform model never sees future forecast targets, hidden Lorenz coordinates, or held-out events.

## Secondary comparison arms

Report, but do not use these to establish the primary tiny-state claim:

- **Waveform only:** four waveform features with eight zero padding columns.
- **Current observed input:** current observed `x` at feature-availability time, padded to width 12.
- **Raw input delays:** 12 causal observed-`x` samples ending at feature-availability time.
- **Internal cable state:** all 19 passive compartment voltages at the event's feature-availability time. This remains a privileged comparison with a different width and cannot support an equal-budget superiority claim.

## Reader

Reuse V3's degree-two ridge readout and training-only preprocessing unless implementation reveals an incompatibility that is documented before any held-out result is inspected.

Fit every forecasting arm against later **observed `x`** on training trajectories only. Hidden Lorenz `y,z` remain excluded from all forecasting fits and feature selection.

Report NRMSE against clean future `x`, normalized using training observed-`x` scale, plus per-trajectory R2 as in Gate A.

## Predeclared evidence criteria

Gate C0 separates two claims.

### Claim C0-A — waveform adds useful information beyond timing

At the primary condition (`noise = 0`, `h = 20`), timing + real waveform must:

1. beat timing-only in mean held-out NRMSE,
2. beat timing + shuffled waveform in mean held-out NRMSE,
3. beat both controls on at least three of four held-out trajectories.

If these conditions fail, Gate C0 provides no evidence that the waveform payload is useful beyond spike timing under this model and reader.

### Claim C0-B — the useful waveform component is not reducible to recent timing context

Timing + residual waveform must beat timing-only in mean primary NRMSE and on at least three of four held-out trajectories.

C0-B may fail even if C0-A passes. In that case the honest interpretation is that waveform is useful but its useful variation is largely predictable from recent spike timing.

Neither claim authorizes a statement that biological neurons generally use waveform coding.

## Required controls

Implementation must include tests or receipts for all of the following:

1. **Same-event identity:** timing-only, real-waveform, shuffled-waveform, and residual-waveform arms use exactly the same spike-event indices and spike times.
2. **Causality:** changing future world input cannot alter already-completed spike waveforms or earlier receiver features.
3. **Feature availability:** forecast targets begin only after the full waveform window is available.
4. **Data separation:** held-out events and future targets never affect normalization, residualization, readout fitting, or feature choice.
5. **Shuffle integrity:** permutation changes event-waveform pairing while preserving every waveform vector exactly once within each trajectory.
6. **Timing residualization:** the timing-to-waveform predictor is fit only on training events and never uses forecast labels.
7. **Independent hidden-label negative control:** a separate evaluation decoder attempts to predict an independent Gaussian event label; it must remain chance-like and may not feed any forecasting arm.
8. **Degenerate cases:** no-spike, single-spike, constant timing, and constant waveform columns fail cleanly or remain finite as appropriate.
9. **Reproducibility:** record all emitter constants, source hashes, seeds, event counts, excluded events, waveform distributions, per-trajectory metrics, and software versions.

## Failure localization

A negative result must be localized, not generalized.

- If the active emitter barely spikes, this fixed output coupling failed to create a usable event channel.
- If waveforms vary but real waveform does not beat shuffled waveform, the variation is not useful for the declared forecasting task.
- If real waveform beats shuffled waveform but residual waveform fails, waveform carries state that is largely explainable by timing history.
- If residual waveform passes, Gate C0 supports the narrow claim that same-timing spike events can carry a small additional state-dependent payload useful for prediction.

Do not alter Gate A, retune the active-emitter mapping, expand the waveform feature set, or introduce a synapse in response to a negative held-out result.

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

No implementation should begin from this spec until the user reviews this written document and approves proceeding to the implementation-plan stage.
