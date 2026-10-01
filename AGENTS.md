# Agent instructions — V3 and Superpowers

## Current authorization

Gate A is complete, merged to `main`, and frozen as a negative result.

On 1 October 2026 the user approved the **Gate C0 state-bearing spike design** in chat. That approval authorizes writing and reviewing the design specification only. Numerical implementation is **not yet authorized**.

The current written design is:

`docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`

Do not add Gate C0 simulation code, tests, dependencies, receipts, CI changes, or numerical results until the user reviews that written spec and explicitly approves proceeding to the implementation-plan stage. After written-spec approval, use the `writing-plans` skill before implementation.

The user's latest explicit instructions always take precedence.

## Read order

1. `README.md`
2. `docs/findings.md`
3. `docs/superpowers/specs/2026-10-01-emitted-state-design.md`
4. `docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`
5. `docs/progress.md`

## Superpowers workflow

Use installed Superpowers skills by name; do not assume a machine-specific skill path.

- **brainstorming:** refine only the selected gate and respect completed design stages.
- **writing-plans:** after written-spec approval, prepare an exact implementation plan with interfaces, tests, commands, and stopping criteria.
- **using-git-worktrees:** isolate implementation work when implementation is authorized.
- **test-driven-development:** verify physics, causality, event identity, data separation, waveform extraction, shuffle controls, and readout behavior.
- **systematic-debugging:** investigate failed controls before changing the model.
- **verification-before-completion:** claim completion only after fresh checks, a frozen receipt, and read-back of the remote checkpoint.

Do not reinterpret design approval as permission to skip the written-spec review or implementation-plan checkpoint.

## Scientific boundaries

### Gate A

- Gate A receiver features contain emitted soma-voltage history only.
- Direct-input and internal-state arms are comparison controls.
- Gate A's failed criterion is frozen. Do not retune its constants or call later gates a repair of Gate A.

### Gate C0

- The question is whether an active spike waveform carries predictive information beyond the timing of the **same spikes**.
- The passive cable stays unchanged and feeds a one-way active emitter.
- The main comparison is timing-only versus timing + real waveform, with a dimension-matched shuffled-waveform control and a timing-residualized waveform control.
- Hidden Lorenz coordinates never enter forecasting fits.
- A passing external reader is an information-access result, not a biological learning rule.
- A negative outcome is valid. Do not tune the active-emitter mapping, waveform feature set, event rule, or held-out criterion after seeing test results.
- Do not introduce synaptic release, a postsynaptic neuron, active dendrites, or consciousness/field claims into Gate C0.

## Checkpoint discipline

Work on one gate at a time. Publish each coherent verified stage early.

Before any handoff or interruption, update `docs/progress.md` with the remote branch/commit, completed work, commands actually run, observed results, unresolved issues, and one precise next action. Label local-only work as local-only.

A checkpoint must let a fresh session resume without the previous chat. User corrections, pauses, and cancellations override all current plans immediately.

**Present next action: user reviews the Gate C0 written spec. No Gate C0 implementation is authorized yet.**
