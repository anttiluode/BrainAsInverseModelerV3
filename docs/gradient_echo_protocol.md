# Gradient/echo readout follow-up — 2026-10-19

Frozen before full evaluation. The user requested continuing the inverse-model
repository with Gemini's gradient and baseline-echo proposal. Gates A, C0 and P
remain unchanged. This is a bounded readout comparison using Gate P's existing
encoder, gates, pulse, 19-sample interrogation, and quadratic ridge reader.

## Questions

1. Does reading voltage plus its temporal differences improve on reading raw
   soma voltage, and does the pulse help under that identical readout?
2. Does subtracting the known resting pulse artifact change the answer?
3. Does the exact state-specific paired echo expose useful state? This third
   measurement requires two identically prepared copies and is diagnostic only.
4. Are spatial edge-current coordinates useful with full compartment access?
   These are also privileged diagnostics, not a new soma sensor.

The raw reader already standardizes every feature using training statistics.
Subtracting one fixed pulse waveform is a constant per-column shift and must
leave its standardized features and predictions unchanged (numerical tolerance
1e-8). This tests the suggested “blinding flash” explanation directly.

## Frozen protocol

- Training seeds 10–15; **fresh primary test seeds 200–203**. Old seeds 100–103
  are reported separately as reused-benchmark diagnostics, never fit.
- Same world, burn 1000, observe 4000, discard 500, query stride 4, 19 features,
  training-only normalization and quadratic ridge factor 0.001 as before.
- Noise 0 and 0.02. No pulse, gate, or encoder changes.
- Same eligible queries as Gate P. Availability q+19; primary target **q+20**,
  one sample after availability. Secondary target q+39 reproduces the old
  timing. Neither arm receives input after q. Report both clocks explicitly.
- Temporal-gradient coordinates are `[v_1, v_2-v_1, ..., v_19-v_18]`:
  invertible coordinates of the same nineteen soma samples. They are temporal
  slopes, not spatial gradients. A change in accuracy can reflect the ridge
  reader's coordinate bias; this transform creates no information.
- Calibrated ping is the measured active-ping trace minus the resting pulse
  trace (the reset_ping arm). It uses no query-specific oracle baseline.
- Paired echo is `(active_ping-active_wait)/pulse_na` on identically prepared
  copies. It does use a query-specific counterfactual; never promote it to a
  single-receiver result. Include fixed-cable paired echo as a null diagnostic.
- Spatial-current diagnostic contains soma voltage and the eighteen oriented
  axial currents `g_ij*(v_j-v_i)` on the tree. This is an invertible linear
  reparameterization of the full nineteen voltages, not extra retained data.
- Arms: raw_wait, raw_ping, calibrated_ping, gradient_wait, gradient_ping,
  paired_echo_diagnostic, fixed_echo_diagnostic, edge_currents_diagnostic,
  internal_state_diagnostic, present_input, raw_input_delays.

## Evidence and controls

Primary accessible-readout criterion: gradient_ping beats **both raw_ping and
gradient_wait** in mean NRMSE and on the same >=3/4 fresh test trajectories at
noise zero, target q+20. A win requires error lower by at least 1e-8.
This distinguishes a coordinate benefit from an actual pulse benefit.

Report each diagnostic comparison without making an accessible-readout claim.
Chance control: independent Gaussian future labels (seed 1100000+world seed)
decoded from gradient_ping; mean NRMSE >=0.90 and mean R² <=0.05, or veto a
positive primary claim. Calibration must preserve predictions within 1e-8;
fixed paired echoes must be constant within 1e-10. Pin causal features, exact
target alignment, coordinate invertibility and fresh-test separation in tests.

Commit protocol/code/tests before the full run. Preserve outcomes regardless
of sign. Keep a full receipt and source hashes. No biological-gradient, object
segmentation, improved learning, or extra-memory claim follows from this assay.
