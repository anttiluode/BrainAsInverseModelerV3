# V3 progress and handoff

## Current state — 2026-10-01

**Gate A is complete and merged to `main`. Gate C0 has an approved written specification and a self-reviewed implementation plan on `feature/gate-c0-waveform-state-spec`; implementation has not started.**

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

## Gate C0 design and plan

Spec:

`docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`

Implementation plan:

`docs/superpowers/plans/2026-10-01-gate-c0-waveform-state.md`

Branch:

`feature/gate-c0-waveform-state-spec`

Key checkpoints:

- initial written Gate C0 spec: `f2449ade6de8a6b82298303e6421315942b78945`
- spec self-review fixes: `a10231147d26eb3c576c068ad1a4d71647b40cae`
- written spec approval recorded: `4fd9cc98f68a962b0d6dc54330cf72f23db2bd89`
- initial implementation plan: `28a66a2839575b87f102251009e5d56c923a9d39`
- plan self-review fixes: `18d4fd7ad12b5466139223540c07fb6eb6d2e523`

### Central question

**Does a spike carry a small state-dependent waveform payload that adds useful predictive information beyond the timing of the exact same spikes?**

### Frozen implementation structure

1. Add a tested one-way classical Hodgkin-Huxley emitter and exact four-feature waveform extractor.
2. Build event-centric timing, real-waveform, deterministic-shuffle, and leave-one-trajectory-out residual-waveform controls using identical spike events.
3. Add the frozen experiment runner, event viability rule, C0-A/C0-B evidence logic, and independent Gaussian event-label control.
4. Run the full protocol once and preserve either a positive, negative, or `not_viable` result without retuning.
5. Add an independent Gate C0 receipt comparator and GitHub Actions reproduction while leaving the Gate A comparator intact.

The plan also freezes the previously qualitative independent-label control operationally: positive C0 claims are invalid if mean negative-control NRMSE is below 0.90 or mean R² exceeds 0.05; independent label seeds are `700000 + trajectory_seed`.

### Scientific locks

- Passive V3 cable and Gate A result remain unchanged.
- HH constants, soma-to-emitter drive, spike threshold, waveform windows/features, shuffle seeds, residualization, reader class, train/test split, horizons, noise levels, and event viability threshold are fixed before the full run.
- All primary arms share exact event identity, onset time, and waveform-availability time.
- Any required primary trajectory with fewer than 50 scored events makes the fixed channel `not_viable`; no gain/bias search follows.
- C0-A requires real waveform to beat timing-only and shuffled waveform in mean NRMSE and on the same at least 3/4 held-out trajectories.
- C0-B requires residual waveform to beat timing-only in mean NRMSE and on at least 3/4 held-out trajectories.
- No synapse, postsynaptic neuron, Gate B, or full Gate C is part of this implementation.

## Authorization state

The user approved the chat design and then approved the written Gate C0 specification. That authorized creation and self-review of the implementation plan.

**Implementation is still paused until the user reviews the implementation plan and chooses/approves an execution approach.** No Gate C0 simulation code, tests, dependencies, receipts, CI changes, or numerical results have been added.

## Precise next action

Ask the user to review `docs/superpowers/plans/2026-10-01-gate-c0-waveform-state.md` and approve execution. In this ChatGPT harness, use native task-by-task execution with `superpowers:executing-plans` and TDD; a subagent runner is not exposed here. Do not begin implementation before that approval.
