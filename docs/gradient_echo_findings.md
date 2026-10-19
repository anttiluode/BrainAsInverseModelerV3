# Reading voltage changes exposes useful predictive state

2026-10-19. Follow-up requested after Gemini's gradient/echo critique.
Protocol and code were committed locally before full evaluation (`2e3a23f`,
then review correction `ea32c83`). No scientific constants changed after results.

## Main result on four fresh trajectories

Readout availability is q+19; the primary prediction target is q+20.
Thus the last sensory input is twenty samples before the target, and the
nineteen-sample interrogation leaves one sample until it. Every arm has the same
blackout and target. These are fresh seeds 200–203, separate from fitting and
the old test trajectories. Mean NRMSE at noise zero, lower is better:

| Readout | Access | Error |
|---|---|---:|
| Voltage + temporal changes, no pulse | Own 19-sample soma trace | **0.393459** |
| Voltage + temporal changes, pulse | Own 19-sample soma trace | 0.395142 |
| Exact paired susceptibility | Two identically prepared copies (diagnostic) | 0.406551 |
| Raw input delays | Last 19 stride-two input samples | 0.635349 |
| Raw soma voltage, no pulse | Own 19-sample soma trace | 0.674525 |
| Raw soma voltage, pulse | Own 19-sample soma trace | 0.675743 |
| Calibrated soma voltage, pulse | Own trace minus known resting pulse | 0.675743 |
| Spatial edge currents + soma | All compartments (diagnostic) | 0.683690 |
| Internal voltages | All compartments (diagnostic) | 0.745506 |
| Present input | Last input only | 0.825817 |
| Fixed-cable paired echo | Two copies, no state-sensitive gate | 1.011325 |

The voltage-change reader reduces error by **41.7%** relative to the raw
no-pulse soma trace and **38.1%** relative to raw input delays, winning both
comparisons on **4/4 fresh trajectories**. The same direction survives 2% input
noise: gradient-wait 0.393712, raw-wait 0.674335, input delays 0.657676.

The pulse is slightly worse on all four fresh trajectories at this primary
target. Therefore the predeclared joint criterion (gradient-ping beats both
raw-ping and gradient-wait) **fails**. The strong observed coordinate/readout
benefit must be distinguished from an unsupported primary pulse benefit.

## What changed, exactly?

The encoder, state-sensitive held gates, pulse and reader class were unchanged.
The temporal readout is only:

```text
[v1, v2-v1, v3-v2, ..., v19-v18]
```

These are invertible coordinates of the same nineteen measured soma samples.
They emphasize small changes between decay samples. The fixed standardized
quadratic ridge reader can use these coordinates more effectively. Because the
transform is invertible and linear, both coordinate systems span the same
unregularized degree-two function family; regularization and conditioning are
coordinate-dependent. This is a useful readout/preconditioning result, not
creation of information or uniquely new neuronal expressivity. It does not yet
establish superiority over a separately optimized conventional reader.

The voltage changes are **temporal derivatives**. The separately tested spatial
coordinates are actual axial currents `g_ij*(v_j-v_i)` on eighteen tree edges,
plus soma voltage. They also preserve all nineteen internal voltages invertibly
but need privileged compartment access. Their modest gain over the internal
voltage reader does not support the assertion that useful information lives
only in spatial derivatives.

## Echo isolation and the flash hypothesis

Subtracting the fixed resting-pulse waveform changes the calibrated predictions
by at most **5.79e-12** in the zero-noise runs. Training-only standardization
already removes that constant per-column shift. In this deterministic,
unsaturated simulation, a common pulse artifact therefore is not the explanation
for the poor raw-trace readout. Measurement noise, clipping, or a varying artifact
would be different mechanisms, and are not present here.

Subtracting the **state-specific unpulsed trajectory** is different: it isolates
the held operator's susceptibility. This diagnostic does expose useful state
(0.406551 NRMSE), but requires two identically prepared copies. An ordinary
single-trace receiver was not given that counterfactual. Its no-pulse temporal
readout actually scores better (0.393459). No practical echo-extraction method
or advantage over the accessible gradient reader has been demonstrated.

The original Gate P held branch gates fixed during each interrogation. Its
pulse changed voltages but did not overwrite a persistent learned memory rule;
no such rule exists in that frozen assay. Its reader was quadratic, not linear.

## The earlier 39-sample separation

The follow-up also preserves Gate P's old target q+39, twenty samples beyond
availability. Fresh-test errors there are:

| Readout | Error |
|---|---:|
| Paired susceptibility (diagnostic) | 0.877773 |
| Gradient + pulse | 0.880640 |
| Gradient without pulse | 0.881041 |
| Raw input delays | 0.979634 |
| Raw voltage without pulse | 0.980608 |
| Raw voltage + pulse | 0.981059 |

Temporal coordinates help at the original longer separation too. The pulse has
a **small secondary** improvement over gradient-wait there (about 0.046%, 4/4
fresh trajectories); it does not turn the failed q+20 primary criterion into a
pass. The old seeds 100–103 are reported separately in the receipt, and their
raw q+39 scores reproduce Gate P's original results.

## Controls, scope and reproduction

- Independent Gaussian labels remain chance-like: NRMSE 0.982778, R² -0.001298.
- Normalized fixed-cable echoes are constant to 3.997e-13 mV/nA.
- Feature causality, target clocks, fresh/reused separation, and coordinate
  invertibility are unit-tested. Hidden Lorenz y,z never enter forecasting fits.
- This remains one synthetic encoder, one engineered held gate, one fixed
  reader, and four fresh test trajectories. No biological gradient learning,
  semantic object grouping, or broad architecture superiority is established.

The useful conclusion is specific: **how the soma trace is read matters greatly;
voltage changes make retained state easier for this reader to use.** The earlier
negative Gate P result remains intact, while its broad “near-unpredictable”
impression is narrowed to that raw-voltage readout and timing.

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_gradient_echo.py --output /tmp/gradient_echo_verify.json
python scripts/compare_gate_p_receipts.py results/gradient_echo_receipt.json /tmp/gradient_echo_verify.json
python -m unittest discover -s tests -v
```

The existing comparator checks every scientific field and source hash, ignoring
only runtime versions. Full evidence: [receipt](../results/gradient_echo_receipt.json).
Predeclared design: [protocol](gradient_echo_protocol.md).
