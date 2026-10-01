# Agent instructions — V3 and Superpowers

## Current authorization

On 1 October 2026 the user requested a new research brief and Superpowers handoff, and explicitly said **do not start implementation yet**.

The repository is a documentation-only planning checkpoint. Reading the brief is not permission to execute it. Do not add simulation code, test code, dependencies, CI workflows, browser assets, or V3 numerical results under this authorization.

The user's latest explicit instructions take precedence. A later request can authorize a particular gate; record its scope in `docs/progress.md`. Earlier approvals from V1 or V2 do not authorize V3 implementation.

## Read order

1. `README.md`
2. `docs/superpowers/specs/2026-10-01-emitted-state-design.md`
3. `docs/progress.md`

The research brief is a proposed design, not an executable implementation plan. Its numerical protocol has not been run in V3. V2 results must remain attributed to the pinned V2 source.

## Superpowers workflow

Use installed Superpowers skills by name; do not assume a machine-specific skill path.

- **brainstorming:** refine only the gate the user selects. The brief already records the motivation, alternatives, constraints, and candidate protocol. Resolve actual gaps; do not restart the whole conversation.
- **writing-plans:** when planning is requested, prepare a short, reviewable plan for that gate with exact interfaces, tests, commands, and completion criteria. Do not silently turn a planning request into execution.
- **using-git-worktrees:** isolate code changes when implementation is authorized.
- **test-driven-development:** verify physics, causality, data separation, and readout behavior with meaningful tests.
- **systematic-debugging:** investigate a failed control before proposing a fix.
- **verification-before-completion:** claim success only after fresh checks, a recorded receipt, and read-back of the published checkpoint.

Respect the authorized scope and the current user's decisions. Do not invent repeated approval steps for routine choices already covered by their request. Do not launch parallel agents merely because they are available. If a skill is unavailable, say so and preserve the same explicit scope and verification requirements.

## Scientific boundaries

- Gate A receiver features contain emitted soma voltage history only.
- Direct-input and internal-state arms are named comparison controls, not privileged inputs to that receiver.
- Fit using later observed input values as targets. Hidden Lorenz coordinates and clean simulator truth remain evaluation-only.
- Declare the delayed teaching signal: observation-trained prediction is not an autonomous biological learning rule.
- Keep trajectory splits, feature width, decoder class, normalization, and forecast horizons explicit.
- Never present an external decoder's success as proof that the passive cable itself learned an inverse.
- Never claim dendritic superiority from beating the present-only baseline; compare ordinary delays.
- Account for pulse-timing assumptions, noise, calibration, and indistinguishable histories.
- A negative outcome is a valid result. Do not tune against held-out answers to rescue it.

## Checkpoint discipline for later authorized work

Work on one gate at a time. Publish each coherent, verified stage early rather than waiting for a finished website.

Before any handoff or interruption, update `docs/progress.md` with: the remote commit/branch, completed work, commands actually run, observed results, unresolved issues, and one precise next action. Label local-only work as local-only; never imply it survived remotely.

A checkpoint must let a fresh session resume without the previous chat. User corrections, pauses, or cancellations override the current task list immediately. Do not continue implementation in the background after a pause.

**Present next action: wait for a new user instruction. No implementation is authorized.**
