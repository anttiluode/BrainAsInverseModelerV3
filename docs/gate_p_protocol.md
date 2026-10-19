# Gate P: can a return pulse expose retained predictive state?

2026-10-19. Protocol frozen before full held-out evaluation. The user authorized
the proposed existing-V3 experiment with “ok do that”. Gate A and C0 stay frozen.

## Question and deliberately synthetic mechanism

Use Gate A's unchanged 19-compartment encoder, Lorenz worlds, six training seeds
10–15, four test seeds 100–103, burn 1000, observation length 4000, discard 500,
query stride 4, input noise 0 and 0.02, and quadratic ridge reader (0.001).
Only later observed x enters forecasting fits. No forecast target selects gates.

At each query copy the encoder state into an isolated interrogation episode.
Disconnect sensory input for 19 one-ms intervals; record soma voltage after each.
Forecast x 20 world samples **after** readout availability: target index q+19+20.
Gate A maps one ms of cable time to one world sample; preserve that convention.
All arms use identical queries, target indices, blackout, and 19-column readers.
Historical controls stop at q; they receive no observations during interrogation.
This is a snapshot assay, not a continuous deployed controller. Original encoder
copies are not changed by interrogation. The 19-sample readout latency is real
in the assay. New scores are not directly comparable to Gate A's h=20 scores.

Let G be the unchanged conductance matrix and l=G*1 its membrane leak vector.
During interrogation only, non-somatic local voltage writes a held conductance:

    G_eff(v) = G + diag(0.75*l*tanh(v / 1 mV)); soma diagonal increment = 0.

This is an engineered, bounded voltage-to-leak rule, not learned morphology,
biological channel kinetics, or an equilibrium-propagation teaching signal.
The gate is held during each readout. G_eff remains positive definite because
at least 25% of every positive leak remains. Propagation is the exact RC solution.
No branch voltage, gate, inferred label, or counterfactual subtraction is delivered
to a primary reader. It sees only its own nineteen soma samples.

Pulse: identical positive 0.01 nA soma current during the first one-ms interval;
zero thereafter. No pulse amplitude, gate gain, or time window tuning after results.

## Arms and evidence

Primary arms: active_wait, active_ping (same G_eff, differing only in pulse),
fixed_wait, fixed_ping (unchanged G, differing only in pulse).
Additional controls: reset_ping (all voltages reset before gate construction),
present_input (one column plus padding), raw_input_delays (19, stride 2),
soma_history (19, stride 2), internal_cable_state (privileged 19 columns).
Use training-only observed-x normalization, then the existing reader's
training-only per-feature standardization. Score mean/per-trajectory NRMSE and R².

P-access: active_ping must beat active_wait, fixed_wait, and fixed_ping in mean
NRMSE and against **all three on the same >=3/4 test trajectories** at noise=0.
This cannot pass just because a nonlinear gate beats a passive cable.
P-forecast (stronger): additionally beat present_input in mean and >=3/4 rows.
Raw delays are a strong baseline, not a prerequisite or a suppressed result.
No rounding-based ties: a win requires NRMSE at least 1e-8 lower.

Checks: fixed_ping minus fixed_wait is input-independent (<=1e-10 range);
reset_ping is input-independent (<=1e-10 range); a matched-soma two-state witness
has identical fixed-cable incremental echoes and distinct active echoes.
Record varying active echo separately as a mechanism diagnostic. Counterfactual
subtraction is available only in the simulator audit, never as a primary feature.
An independent Gaussian-label reader on active_ping (seed 900000+trajectory seed)
must have mean NRMSE >=0.90 and mean R² <=0.05. A failed check vetoes claims.

Training/test separation is preserved, but these test seeds were used by previous
V3 gates: this is a reused benchmark, not a fresh final confirmation cohort.

## Reproduction and limits

Commit protocol, implementation, and tests before the full run. Preserve negative
results unchanged. Smoke runs are engineering checks, not scientific evidence.
Store full protocol, source hashes, timing/row accounting, normalization, controls,
per-trajectory scores and verdicts in results/gate_p_receipt.json. Add a CI rerun
and scientific comparison. Keep the old emitter, encoder, receipts and comparators
unchanged. This tests output access in an engineered synthetic medium, not a
superior memory, biological learning rule, semantic grouping, or image generation.
