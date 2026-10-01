# V3 progress and handoff

## Current state — 2026-10-01

**Planning only. Implementation has not started.**

The user requested the beginning of the successor tests in a new empty repository and explicitly postponed implementation after prior sessions failed to finish reliably.

V3 initially contained only LICENSE at main commit `c01246b6f31811ed52fbd806213f163bfdc81ff6`. This checkpoint adds README, AGENTS.md, the Superpowers research brief, and this progress record. The license is preserved.

## Source and question

V2 source anchor: `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`.

Question: can a receiver use emitted soma history to learn useful forecasts of the observed world, without hidden-state training labels or access to the sender's branch voltages?

The first candidate is Gate A: continuous soma output with a fixed degree-two predictive reader. Later sensory-gap and spiking gates remain deferred.

## Work completed

- Recorded the research question, alternatives, proposed protocol, comparison arms, failure criteria, and claim boundaries.
- Established Superpowers instructions and an explicit implementation pause.
- Defined checkpoint requirements so the work can survive a session interruption.

No V3 simulation, code test, dependency installation, experiment receipt, website, or numerical result exists. Quoted measurements refer only to V2.

This file is included in the initial planning commit on main. Use Git history for that commit's exact SHA; do not invent a receipt or a self-referential commit hash.

## Precise next action

Wait for the user's next instruction.

If they request a plan, prepare only a Gate A implementation plan. If they explicitly request implementation, read AGENTS.md and the brief, resolve any requested protocol changes, then plan and execute the authorized gate with early verified remote checkpoints. Do not automatically begin Gates B or C.

Before a later handoff, replace this section with the actual branch/commit, completed stages, checks run, measured findings, outstanding issues, and one next action. Preserve failed results and distinguish remote work from local-only work.
