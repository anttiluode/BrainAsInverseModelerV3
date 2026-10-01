# Gate A Emitted-State Prediction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether a reader restricted to the sender's emitted soma-voltage history can learn held-out forecasts of later observed input values, without hidden-state labels or branch-voltage access.

**Architecture:** Reuse the pinned V2 passive cable, Lorenz generator, causal temporal features, and degree-two ridge reader as a provenance-locked core. Add one Gate A experiment layer that constructs six equal-width comparison arms, trains only on future observed-x targets, evaluates on held-out trajectories against clean future x, and writes a complete receipt plus findings. No spiking, morphology learning, sensory-gap logic, or Gate B/C work belongs here.

**Tech Stack:** Python 3.12+, NumPy, SciPy, `unittest`, JSON receipts, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-01-emitted-state-design.md`

## Global Constraints

- Pin scientific reuse to BrainAsInverseModelerV2 commit `795be2c7e8c4ba25112983fdc9ac2ad00ca232d0`; preserve copied numerical core behavior and record source hashes.
- Lorenz parameters `(10, 28, 8/3)`, RK4 step `0.01`; cable interval `1 ms`; distal drive `0.01 nA * normalized observed x` identically on all six ports.
- Train seeds `10..15`; held-out seeds `100..103`; burn-in `1000`; observe `4000`; score from index `500` with stride `4`.
- Noise levels `0` and `0.02 * clean training-x std`; seed formula `200000 + trajectory_seed + int(noise_level * 10000)`.
- Every reader feature vector has width 19. History arms use current sample plus 18 previous samples at stride 2.
- Decoder is the V2 degree-two ridge readout with ridge factor `0.001`, intercept unpenalized; all preprocessing is fit on training trajectories only.
- Forecast horizons are `1, 5, 20`; primary condition is horizon `20`, zero input noise.
- Receiver fitting may use only emitted soma history and later observed x targets. Hidden Lorenz y/z and clean future x are evaluation-only and may not affect model selection or fitting.
- Gate A stops after verified results, receipt, findings, README/progress update, and CI. Do not begin Gates B or C or add spiking.

## Review Focus

- **Temporal leakage:** shifting any future observed samples must not change features at earlier times; add explicit causality tests in Task 2.
- **Train/test leakage:** held-out trajectories and clean/hidden labels must never enter fit statistics or coefficients; add sentinel-based separation tests in Task 2.
- **Target indexing:** post-interval soma sample at time `t` predicts observed `x[t+h]`, and rows without a valid target are excluded; pin exact indices in Task 2 tests.
- **Degenerate signals:** constant/zero features must stay finite through normalization and ridge fitting; pin in Task 1/2 tests.
- **Unrecoverable variable:** an independent hidden label that never enters the observed process should remain at chance-like held-out reconstruction and must be isolated from the forecasting reader; implement as an evaluation-only negative control in Task 3.

---

### Task 1: Provenance-locked V2 core

**Files:**
- Create: `emitted_state/__init__.py`
- Create: `emitted_state/cable.py`
- Create: `emitted_state/world.py`
- Create: `emitted_state/readout.py`
- Create: `tests/test_core.py`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `Cable.transition(dt_ms)`, `Cable.encode(currents, dt_ms=1.0)`, `make_cable(diverse=True, tau_scale=1.0)`, `lorenz(initial, steps, dt=0.01)`, `delay_features(signal, size=19, stride=2)`, `exponential_features(signal, dt_ms=1.0, size=19)`, `QuadraticReadout(ridge_factor=0.001)`, `normalized_rmse(...)`.

- [ ] **Step 1: Write failing provenance/core tests** for a known exact RC transition, passive decay, causal delay features, finite constant-column readout, and deterministic Lorenz generation.
- [ ] **Step 2: Run** `python -m unittest tests.test_core -v` and verify failure because the package does not exist.
- [ ] **Step 3: Port the pinned V2 implementations** of `cable.py`, `world.py`, and `readout.py` without changing numerical constants or algorithms; set `requirements.txt` to NumPy and SciPy only.
- [ ] **Step 4: Run** `python -m unittest tests.test_core -v` and verify all core tests pass.
- [ ] **Step 5: Record SHA256 hashes** of the three copied source files for later receipt provenance.
- [ ] **Step 6: Commit** `feat: port pinned V2 prediction core`.

### Task 2: Gate A causal forecast dataset and six comparison arms

**Files:**
- Create: `emitted_state/gate_a.py`
- Create: `tests/test_gate_a.py`

**Interfaces:**
- Consumes: Task 1 core.
- Produces: `Protocol` dataclass containing the frozen constants; `initial_for_seed(seed) -> np.ndarray`; `world_for_seed(seed, protocol) -> np.ndarray`; `observed_x(state, seed, noise_level, x_mean, x_scale) -> np.ndarray`; `feature_bank(observed_x_norm, cable) -> dict[str, np.ndarray]`; `scored_indices(observe, discard, stride, horizon) -> np.ndarray`; `build_training_rows(...)`; `fit_forecasters(...)`; `evaluate_forecasters(...)`.
- Arm keys are exactly: `present_input`, `raw_input_delays`, `exponential_input_traces`, `internal_cable_state`, `instantaneous_soma`, `soma_history`.

- [ ] **Step 1: Write failing timing/shape tests** asserting all six arms have width 19, `soma_history[:,0]` equals current soma output, older columns are stride-2 causal samples, and scored indices exclude `t+h >= observe`.
- [ ] **Step 2: Write failing causality test**: modify observed input strictly after a cutoff and assert every feature row at or before the cutoff is unchanged.
- [ ] **Step 3: Write failing separation test** using sentinel hidden labels/held-out arrays and assert forecast fitting accepts only training feature matrices plus future observed-x targets; no hidden-label parameter exists in the fit path.
- [ ] **Step 4: Implement `Protocol`, world/noise generation, feature construction, and future-target row alignment** exactly from the spec. Use post-interval cable state from `Cable.encode`; soma is compartment 0.
- [ ] **Step 5: Implement training-only normalization and one `QuadraticReadout(0.001)` per arm/noise/horizon.** Clean future x is not passed into fitting.
- [ ] **Step 6: Run** `python -m unittest tests.test_gate_a -v` and verify the timing, causality, separation, constant-signal, and degenerate-feature tests pass.
- [ ] **Step 7: Commit** `feat: add causal Gate A forecast protocol`.

### Task 3: Frozen experiment, controls, receipt, and scientific verdict

**Files:**
- Create: `scripts/run_gate_a.py`
- Create: `results/gate_a_receipt.json`
- Create: `docs/findings.md`
- Modify: `README.md`
- Modify: `docs/progress.md`
- Test: `tests/test_gate_a.py`

**Interfaces:**
- Consumes: Task 2 protocol/evaluation functions.
- Produces: machine-readable receipt with protocol, package/runtime versions, source hashes, per-arm/per-noise/per-horizon/per-trajectory NRMSE and R², primary-condition pass/fail counts, and isolated negative-control metrics.

- [ ] **Step 1: Write failing quick-run test** that executes a reduced protocol and asserts every required arm/horizon/noise result is present and finite.
- [ ] **Step 2: Add evaluation-only independent-hidden-label probe** using independent Gaussian labels generated from declared seeds; its model and weights must never feed the forecasting reader.
- [ ] **Step 3: Implement `scripts/run_gate_a.py`** with `--quick` and full modes, deterministic JSON output, runtime/package versions, source SHA256 hashes, and explicit primary-evidence computation: soma history must beat instantaneous soma and present input in mean primary NRMSE and on at least 3/4 held-out trajectories.
- [ ] **Step 4: Run** `python -m unittest discover -s tests -v` and verify all tests pass.
- [ ] **Step 5: Run full frozen experiment** with `OPENBLAS_NUM_THREADS=1 python scripts/run_gate_a.py` exactly once for the published receipt; do not tune constants after seeing held-out results.
- [ ] **Step 6: Write `docs/findings.md` from the measured receipt**. State whether transmission/use passed, whether ordinary delays won or lost, and whether internal-state advantage survived the soma bottleneck. Preserve negative results.
- [ ] **Step 7: Update README and progress** so V3 results are clearly separated from V2 results and the exact next action is either analyze Gate A or design Gate B—not silently start it.
- [ ] **Step 8: Re-run** `python -m unittest discover -s tests -v` after documentation/receipt generation and verify green.
- [ ] **Step 9: Commit** `experiment: publish Gate A output prediction receipt`.

### Task 4: Remote reproducibility checkpoint

**Files:**
- Create: `.github/workflows/checks.yml`
- Modify: `docs/progress.md`

**Interfaces:**
- Consumes: complete Gate A branch.
- Produces: CI rerun of unit tests plus a fresh full experiment in a temporary directory, without overwriting the committed receipt.

- [ ] **Step 1: Add CI workflow** on push/PR using Python 3.12: install `requirements.txt`, run `python -m unittest discover -s tests -v`, then rerun the full experiment into a temporary output path and compare its scientific result payload with the committed receipt excluding environment-specific metadata.
- [ ] **Step 2: Push/check branch and inspect CI**; if a control fails, use systematic-debugging before changing scientific constants.
- [ ] **Step 3: Update `docs/progress.md`** with exact remote branch/commit, commands actually run, measured headline result, CI run state, unresolved caveats, and one precise next action.
- [ ] **Step 4: Read back README, findings, receipt, and progress from GitHub** and confirm the published checkpoint matches the verified local/CI state.
- [ ] **Step 5: Commit** `ci: verify Gate A reproducibility`.

## Completion Criteria

Gate A is complete only when: all tests pass; the full frozen protocol has run without held-out tuning; the committed receipt contains every arm, horizon, noise condition, and held-out trajectory; the negative control is isolated; findings state the predeclared pass/fail rule; CI independently reproduces the experiment; and the remote checkpoint can be resumed without this chat.
