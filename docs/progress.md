# V3 progress and handoff

## Current state — 2026-10-01

**Gate A is now authorized for implementation, but code execution has not started yet.**

The initial V3 checkpoint deliberately paused implementation. The user's later instruction on 1 October 2026 explicitly said to continue V3 as planned. That lifts the earlier pause for **Gate A only**. Gates B and C remain deferred and require separate scope decisions.

Work is isolated on branch `feature/gate-a-output-prediction` from main commit `9b44b4b958c198c696c4d1627901d89c7dcfb40f`.

## Source and question

V2 source anchor: `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`.

Question: can a receiver use emitted soma history to learn useful forecasts of the observed world, without hidden-state training labels or access to the sender's branch voltages?

Gate A tests continuous soma output with a fixed degree-two predictive reader. Sensory-gap and spiking gates remain deferred.

## Work completed

- Read and re-established the repository handoff from `AGENTS.md`, the research brief, and the earlier progress checkpoint.
- Verified the pinned V2 core interfaces needed for reuse: passive cable encoding, Lorenz world generation, causal delay/exponential features, and quadratic ridge readout.
- Created the execution branch `feature/gate-a-output-prediction`.
- Wrote and committed the Gate A implementation plan at `docs/superpowers/plans/2026-10-01-gate-a-output-prediction.md` in commit `d7ad490a25f4834112ebab0657ffdd2b15e11488`.
- Self-reviewed the plan against the frozen protocol: all six comparison arms, horizons 1/5/20, noise 0/0.02, trajectory holdout, causality, timing, separation, independent-hidden-label negative control, predeclared success rule, receipt, findings, and CI reproduction are covered.

No V3 simulation code, test code, dependency file, experiment receipt, website result, or V3 numerical measurement has been created yet. Quoted numerical measurements still refer only to V2.

## Implementation scope once plan review is complete

Execute only the four Gate A tasks in the committed plan:

1. provenance-locked V2 core and tests,
2. causal forecast dataset plus six comparison arms,
3. full frozen experiment, negative control, receipt, and findings,
4. independent CI reproducibility checkpoint.

Do not begin Gate B, Gate C, spiking, learned morphology, or biological-learning claims.

## Precise next action

Review `docs/superpowers/plans/2026-10-01-gate-a-output-prediction.md`. If it is accepted, execute it natively on the existing feature branch with TDD and early remote checkpoints. Preserve negative results and do not tune against held-out outcomes.
