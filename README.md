# BrainAsInverseModelerV3 — From retained state to useful output

**Can a receiver learn useful predictions of a hidden process from the signal emitted by a history-bearing dendritic cable?**

V2 demonstrated that an illustrative passive cable can retain information about hidden causes. V3 asks whether those distinctions survive access through the soma, and whether a reader can use them to predict later observations.

**Status: planning only, paused on 1 October 2026.** No V3 model, experiment, test suite, website, or result has been implemented. The current user instruction authorizes establishing this brief and explicitly postpones implementation.

## Start here

- [Research question and proposed tests](docs/superpowers/specs/2026-10-01-emitted-state-design.md)
- [Agent and Superpowers instructions](AGENTS.md)
- [Progress and handoff](docs/progress.md)

A later session should read all three before doing anything else. The first candidate experiment is **Gate A: continuous soma output to an observation-trained predictive reader**. It starts with the existing passive cable; spiking, biological learning, and networks are later questions.

## What V2 established

The pinned [V2 checkpoint](https://github.com/anttiluode/BrainAsInverseModelerV2/tree/795be2c7e8c4ba25112983fdc9ac2ad00ca232d0) reports:

- Diverse branches permit recovery of six known-timing pulse amplitudes from a soma trace in zero noise; symmetric branches preserve only their sum.
- A trained evaluator can recover Lorenz hidden coordinates from the cable's internal voltages. Mean normalized error is 0.1774, versus 0.6216 from the present input alone.
- Ordinary delay samples perform better: 0.0777 error.
- Resetting the cable erases its history advantage.
- A good waveform fit can coexist with incorrect inferred causes.

These are **V2 results**, not V3 predictions or measurements. The external evaluator had hidden-state labels during training and access to internal voltages. Those are the two privileges V3 needs to examine.

## The planned progression

| Gate | Question | Access allowed |
|---|---|---|
| A — output and prediction | Does soma history support prediction on new trajectories? | Receiver uses soma output; training targets are later observed input values |
| B — interruptions and ambiguity | Does the retained distinction help through a sensory gap? | Same receiver, explicitly defined gap and reset controls |
| C — neuronal transmission | Do useful distinctions survive spike generation and reception? | A separately specified sender/receiver model |

Only Gate A is the candidate first implementation. B and C require their own designs and explicit scope decisions.

The useful outcome may be a successful transmission mechanism, a clear output bottleneck, or a demonstration that ordinary memory does the job better. Publish the measured outcome either way.

## Lineage

[BrainAsInverseModeler](https://github.com/anttiluode/BrainAsInverseModeler) →
[BrainAsInverseModelerV2](https://github.com/anttiluode/BrainAsInverseModelerV2) →
this planning checkpoint.

[Varjoluotain](https://github.com/anttiluode/Varjoluotain) supplies the inverse-problem lesson: the instrument determines which hidden distinctions reach the measurement, and a successful fit does not settle every hidden cause.
