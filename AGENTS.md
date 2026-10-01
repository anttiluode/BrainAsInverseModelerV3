# Agent instructions — V3 and Superpowers

## Current authorization and frozen results

Gate A is complete, merged to `main`, and frozen as a negative result.

Gate C0 has been explicitly designed, planned, implemented, and measured on `feature/gate-c0-waveform-state-spec`. Its full result is frozen: C0-A and C0-B passed under the predeclared primary condition, and the independent-label chance control passed. Do not alter the emitter mapping, waveform features, event selection, residualization, reader settings, or evidence thresholds to improve that result.

The current Gate C0 design and plan are:

- `docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`
- `docs/superpowers/plans/2026-10-01-gate-c0-waveform-state.md`

The current authorization is to finish Gate C0 reproducibility/verification only. Do not start Gate B, a synapse, a postsynaptic neuron, or full Gate C without a new explicit user request.

## Read order

1. `README.md`
2. `docs/findings.md`
3. `docs/gate_c0_findings.md`
4. `results/gate_a_receipt.json`
5. `results/gate_c0_receipt.json`
6. Gate C0 spec and implementation plan above
7. `docs/progress.md`

## Superpowers workflow

Use installed Superpowers skills by name.

- **systematic-debugging:** investigate any failed control or reproduction before proposing a change.
- **test-driven-development:** any implementation fix requires a failing test first.
- **verification-before-completion:** claim Gate C0 complete only after the unit suite, full frozen rerun, scientific receipt comparison, and exact-head CI verification pass.
- **requesting-code-review:** perform the whole-branch review before integration; if no subagent tool is available, document that the final review is a self-review.
- **finishing-a-development-branch:** after verification, present the integration decision rather than silently merging.

## Scientific boundaries

### Gate A

- Gate A receiver features contain emitted soma-voltage history only.
- Direct-input and internal-state arms are comparison controls.
- Gate A's failed criterion is frozen. Later positive gates do not retroactively make it pass.

### Gate C0

- The question is whether an active spike waveform carries predictive information beyond timing of the **same spikes**.
- The passive cable stays unchanged and feeds a one-way active emitter.
- Primary controls are timing-only, timing + real waveform, timing + shuffled waveform, and timing + timing-residualized waveform.
- Hidden Lorenz coordinates never enter forecasting fits.
- C0-A and C0-B passed on the frozen full protocol; raw input delays still performed better than the best waveform representation.
- This is an information-access result in a synthetic mechanism, not evidence that biological neurons generally use waveform coding.
- No synaptic release, postsynaptic receiver, biological learning rule, active dendrites, or consciousness/field claim is part of Gate C0.

## Checkpoint discipline

Before any interruption, update `docs/progress.md` with the remote branch/commit, commands actually run, observed result, unresolved issues, and one precise next action. Label any local-only work explicitly.

A checkpoint must let a fresh session resume without the previous chat. User corrections, pauses, and cancellations override current plans immediately.

**Present next action: finish Gate C0 receipt comparison and exact-head CI verification. Do not begin another biological mechanism automatically.**
