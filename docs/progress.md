# V3 progress and handoff

## Current state — 2026-10-01

**Gate A is complete and merged to `main`. Gate C0 has an approved chat design and a self-reviewed written specification on `feature/gate-c0-waveform-state-spec`; implementation has not started.**

Gate A's negative result remains frozen. Gate C0 is a new hypothesis, not a repair of Gate A.

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

Post-merge GitHub Actions on `0f1627b2` passed unit tests, reran the frozen Gate A experiment, and matched the regenerated scientific payload to the committed receipt.

## New empirical motivation

The user supplied Martin-Burgos et al., *Action potential waveforms are state-dependent* (bioRxiv 2026.09.15.751814; preprint, posted 21 September 2026).

The paper motivates a narrower test: a spike may be an event with a small state-dependent waveform payload rather than only a binary timestamp. Gate C0 does not assume that conclusion; it tests whether a simple active emitter can make waveform features useful beyond spike timing on the V3 forecasting task.

## Gate C0 written design

Spec:

`docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`

Branch:

`feature/gate-c0-waveform-state-spec`

Design checkpoint commits:

- initial written Gate C0 spec: `f2449ade6de8a6b82298303e6421315942b78945`
- authorization/read-order update: `050857ae5517d80ce62f9447af7d29abc884711a`
- initial handoff: `9df9a20509f7364179e7700e5d48f3ec31e69533`
- spec self-review fixes: `a10231147d26eb3c576c068ad1a4d71647b40cae`

### Central question

**Does a spike carry a small state-dependent waveform payload that adds useful predictive information beyond the timing of the exact same spikes?**

### Frozen design choices pending user review

- Keep the passive V3 cable unchanged.
- Add a one-way Hodgkin-Huxley active emitter; no feedback into the passive cable.
- Exact modern-voltage HH equations, standard Na/K/leak parameters, steady-state initialization at -65 mV, deterministic RK4 at 0.025 ms.
- Training-only soma normalization and fixed drive mapping `I_emit = 10 + 4*tanh(z_s/2)` uA/cm².
- Spike onset: linearly interpolated upward 0 mV crossing.
- Waveform window: -1 ms to +4 ms around onset; forecast features become available only after +4 ms.
- Exactly four waveform features with fixed measurement rules: peak amplitude, half-height width, peak sharpness, repolarization slope.
- Event-centric examples with the eight most recent completed log-ISIs as timing context.
- Same V3 train/test trajectory split, noise levels, and forecast horizons 1/5/20; primary condition remains zero noise, horizon 20.
- Primary width-12 arms: timing only, timing + real waveform, timing + deterministic within-trajectory shuffled waveform, timing + timing-residualized waveform.
- Training residuals use leave-one-training-trajectory-out waveform-from-timing predictions; held-out residualization is fit only on the six training trajectories.
- A required trajectory needs at least 50 scored primary events; otherwise the fixed emission channel is declared non-viable rather than retuned.
- Secondary arms: waveform only, current observed input, raw observed-input delays, privileged internal cable state.
- Reuse V3's degree-two ridge reader with ridge factor 0.001.

### Predeclared claim structure

C0-A supports “waveform adds useful information beyond timing” only if timing + real waveform beats both timing-only and timing + shuffled waveform in mean primary NRMSE and, on the **same at least 3/4 held-out trajectories**, beats both controls.

C0-B supports “useful waveform information is not reducible to recent timing context” only if timing + residual waveform beats timing-only in mean primary NRMSE and on at least 3/4 held-out trajectories.

A negative result is retained. Do not retune the emitter mapping, add waveform features, alter event selection, or introduce synapses after viewing held-out outcomes.

## Spec self-review

Completed before user review.

Resolved ambiguities:

- exact HH equations, voltage convention, initialization, and integrator are explicit;
- waveform features now have exact measurement windows and interpolation rules;
- the fixed event-viability threshold is explicit;
- shuffle seeds and residualization data separation are explicit;
- the C0-A 3/4 criterion now explicitly requires the same held-out trajectories to beat both controls.

No Gate C0 code or numerical result was produced during design/spec work.

## Authorization state

The user approved the **chat design**. Under the Superpowers brainstorming workflow, that permits writing and self-reviewing this specification but does not yet authorize implementation.

No Gate C0 simulation code, tests, dependencies, receipts, CI changes, or numerical results have been added.

## Precise next action

Ask the user to review the written Gate C0 specification. If they approve the written spec, invoke `writing-plans` and prepare a concrete implementation plan. Do not implement Gate C0 before that plan-stage approval.
