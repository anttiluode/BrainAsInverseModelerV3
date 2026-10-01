# Gate C0 State-Bearing Spike Emission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether a small state-dependent spike-waveform payload improves held-out future-observation prediction beyond the timing of the exact same emitted spikes.

**Architecture:** Keep the V3 passive cable, Lorenz world, noise schedule, and quadratic reader unchanged. Add a one-way Hodgkin-Huxley emitter that converts training-normalized soma voltage into spike events, extract four frozen waveform features, then build event-centric timing/waveform controls and a separate frozen experiment runner. Gate A remains untouched.

**Tech Stack:** Python 3.12+, NumPy, SciPy only through the existing requirements, `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-01-gate-c0-waveform-state-design.md`

## Global Constraints

- Do not modify Gate A numerical constants, receipt, or evidence criteria.
- Reuse `emitted_state.cable`, `emitted_state.world`, `emitted_state.gate_a.observed_x`, and `emitted_state.readout.QuadraticReadout` rather than copying them.
- Hodgkin-Huxley constants: `C_m=1`, `g_Na=120`, `E_Na=50`, `g_K=36`, `E_K=-77`, `g_L=0.3`, `E_L=-54.387`; RK4 `dt=0.025 ms`; initialize `V=-65 mV` with steady-state gates.
- Soma-to-emitter drive is frozen as `I_emit = 10 + 4*tanh(z_s/2)` uA/cm² with soma mean/std fit on training trajectories separately for each noise condition.
- Spike onset is an upward `0 mV` crossing; waveform window is `[-1,+4] ms`; feature availability is onset `+4 ms`; targets are indexed from the first 1 ms world interval beginning at or after availability.
- Waveform payload is exactly peak amplitude, half-height width, peak sharpness at ±0.1 ms, and repolarization OLS slope over `[t_peak+0.5,t_peak+2.0] ms`.
- Timing context is exactly eight previous log-ISIs; all four primary arms use the same event IDs, onset times, and availability times.
- Primary arms are width 12: timing only, timing + real waveform, timing + shuffled waveform, timing + residual waveform. Internal cable state remains the privileged width-19 secondary arm.
- Shuffle seed is `500000 + trajectory_seed`; implement a deterministic derangement so every waveform vector moves to another event while each vector is preserved exactly once.
- Residualization uses degree-two ridge factor `0.001`; training residuals are leave-one-training-trajectory-out, held-out residuals use a model fit on all six training trajectories.
- Training seeds `(10,11,12,13,14,15)`, held-out seeds `(100,101,102,103)`, noise levels `(0,0.02)`, horizons `(1,5,20)`, primary condition noise `0`, horizon `20`.
- A primary trajectory is viable only with at least 50 scored events after waveform validity, eight-ISI history, and horizon-20 target-boundary exclusions. Any required trajectory below 50 makes the frozen channel `not_viable`; do not retune.
- Operationalize the independent Gaussian-label control before the full run: positive C0 claims are invalid if its mean NRMSE is `<0.90` or its mean R² is `>0.05`. Label seed is frozen as `700000 + trajectory_seed`.
- Do not tune emitter mapping, waveform features, event selection, decoder, or claim thresholds after inspecting held-out full-protocol results.

## Review Focus

1. **HH singular rates:** `alpha_m(-40)` and `alpha_n(-55)` must use analytic limits and remain finite; pinned in Task 1 tests.
2. **Event overlap/boundaries:** spikes with incomplete `[-1,+4] ms` windows or another onset in `(0,+4] ms` must be excluded with explicit reason counts; pinned in Task 1 tests.
3. **Same-event controls:** shuffling/residualization may change feature values but never row identity, onset time, or decision time; pinned in Task 2 tests.
4. **Training-only transforms:** soma normalization, timing normalization, residualizers, and forecasters must not use held-out data or future labels; pinned in Tasks 2–3 tests.
5. **Nonviable channel:** fewer than 50 primary scored events in any required trajectory must produce a reproducible `not_viable` receipt rather than an exception or parameter search; pinned in Task 3 tests.

---

### Task 1: Active emitter and deterministic waveform extraction

**Files:**
- Create: `emitted_state/emitter.py`
- Create: `tests/test_emitter.py`

**Interfaces:**
- Consumes: one current value per 1 ms world interval.
- Produces:
  - `HHParams` frozen dataclass with the exact constants above.
  - `WaveformEvent(spike_index: int, onset_ms: float, availability_ms: float, features: np.ndarray)`.
  - `EmissionResult(onset_times_ms: np.ndarray, events: tuple[WaveformEvent, ...], exclusions: dict[str, int])`.
  - `hh_rates(v_mv: float) -> tuple[float, float, float, float, float, float]` ordered `(alpha_m,beta_m,alpha_h,beta_h,alpha_n,beta_n)`.
  - `steady_state_gates(v_mv: float) -> tuple[float,float,float]` ordered `(m,h,n)`.
  - `simulate_hh_piecewise(current_by_interval: np.ndarray, interval_ms: float = 1.0, dt_ms: float = 0.025, params: HHParams = HHParams()) -> tuple[np.ndarray,np.ndarray]` returning integration sample times and voltage.
  - `extract_waveform_events(time_ms: np.ndarray, voltage_mv: np.ndarray, pre_ms: float = 1.0, post_ms: float = 4.0) -> EmissionResult`.

- [ ] **Step 1: Write failing HH rate/initialization tests**

Add tests asserting `alpha_m(-40.0) == 1.0`, `alpha_n(-55.0) == 0.1`, all six rates are finite at `-65`, and each steady-state gate equals `alpha/(alpha+beta)` and lies in `[0,1]`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m unittest tests.test_emitter.EmitterPhysicsTests -v`

Expected: FAIL because `emitted_state.emitter` does not exist.

- [ ] **Step 3: Implement HH rates, initialization, and RK4 simulation**

Implement the exact spec equations with analytic singular limits. `simulate_hh_piecewise` must hold each current element constant for exactly 1 ms / 40 RK4 substeps at the default settings, start at `V=-65`, and reject nonfinite currents or interval/dt ratios that are not positive integers within `1e-12`.

- [ ] **Step 4: Add deterministic simulation tests**

Assert two 100 ms runs at constant `10 uA/cm²` are bitwise-equal, finite, have identical shapes, and cross `0 mV` at least once. Assert a zero-current 20 ms run stays finite.

- [ ] **Step 5: Write failing exact waveform-feature test**

Use a synthetic piecewise-linear spike with baseline `-65 mV`, onset at `0 ms`, peak `35 mV` at `1 ms`, and linear repolarization to `-65 mV` at `3 ms`. Assert extracted features are approximately `[100.0, 2.1153846153846154, 4.25, -50.0]` using interpolation under the spec rules.

- [ ] **Step 6: Write failing exclusion tests**

Construct traces proving: an onset before 1 ms is counted as `boundary`; an onset with another onset within the next 4 ms is counted as `overlap`; an otherwise complete spike produces one `WaveformEvent` whose `spike_index` indexes the full detected-onset array.

- [ ] **Step 7: Implement onset interpolation, waveform extraction, and exclusion accounting**

Detect all upward 0 mV crossings first. Use every detected onset for `onset_times_ms`, even when its waveform is later excluded. A valid event stores only the four-feature vector and stable index into that full onset array.

- [ ] **Step 8: Run Task 1 tests GREEN**

Run: `python -m unittest tests.test_emitter -v`

Expected: all Task 1 tests pass.

- [ ] **Step 9: Run the existing suite for regression safety**

Run: `python -m unittest discover -s tests -v`

Expected: existing Gate A tests plus Task 1 tests all pass.

- [ ] **Step 10: Commit**

```bash
git add emitted_state/emitter.py tests/test_emitter.py
git commit -m "feat: add state-dependent HH spike emitter"
```

### Task 2: Event-centric Gate C0 dataset and controls

**Files:**
- Create: `emitted_state/gate_c0.py`
- Create: `tests/test_gate_c0.py`

**Interfaces:**
- Consumes: existing Gate A world/noise/cable utilities plus Task 1 `EmissionResult`.
- Produces:
  - `PRIMARY_ARMS = ("timing_only","timing_real_waveform","timing_shuffled_waveform","timing_residual_waveform")`.
  - `SECONDARY_ARMS = ("waveform_only","current_observed_input","raw_input_delays","internal_cable_state")`.
  - `GateC0Protocol` frozen dataclass containing all frozen schedule/current/threshold seeds and constants from Global Constraints.
  - `EventTable(seed, event_ids, onset_ms, availability_ms, availability_index, timing_raw, waveform, current_observed, raw_input_delays, internal_cable_state, exclusions)` with NumPy arrays sharing one row axis.
  - `passive_state_for_observed(observed: np.ndarray, observed_mean: float, observed_scale: float, protocol: GateC0Protocol) -> np.ndarray`.
  - `emitter_current(soma: np.ndarray, soma_mean: float, soma_scale: float) -> np.ndarray` implementing exactly `10 + 4*tanh(z/2)`.
  - `build_event_table(...) -> EventTable`; use all detected onsets, including waveform-invalid predecessors, to construct the eight ISIs ending at each valid current spike.
  - `eligible_rows(table: EventTable, horizon: int, observe: int) -> np.ndarray`.
  - `fit_timing_stats(train_tables) -> tuple[np.ndarray,np.ndarray]`; fit on all valid training events with eight-ISI history before forecast-boundary trimming, and clamp scales `<1e-12` to `1.0`.
  - `deranged_waveforms(waveform: np.ndarray, seed: int) -> np.ndarray`.
  - `residualize_waveforms(train_tables, test_tables, timing_mean, timing_scale, ridge_factor) -> tuple[dict[int,np.ndarray],dict[int,np.ndarray],dict]`; provenance dict records fit-seed sets per predicted trajectory.
  - `arm_features(table, timing_mean, timing_scale, residual_waveform, protocol) -> dict[str,np.ndarray]`.
  - `fit_forecasters(features_by_arm, targets, ridge_factor) -> dict[str,QuadraticReadout]`; no hidden-coordinate or clean-truth parameter.

- [ ] **Step 1: Write failing frozen-drive and availability-index tests**

Assert `emitter_current(np.array([-1,0,1]),0,1)` equals `10 + 4*tanh([-0.5,0,0.5])`. For synthetic event availability times `4.0`, `4.001`, `4.999`, `5.0` ms, assert world indices are `4,5,5,5` respectively.

- [ ] **Step 2: Write failing timing-context test**

Create ten detected onsets with one invalid-waveform predecessor and one valid tenth spike. Assert the valid spike's timing vector still uses the previous eight intervals from the complete onset sequence, proving invalid waveform predecessors are not erased from timing history.

- [ ] **Step 3: Write failing same-event/width tests**

Build a synthetic `EventTable` with at least 12 rows. Assert every primary arm has shape `(n,12)`, all primary arms preserve identical `event_ids`, and `internal_cable_state` has width 19 while the other secondary arms have width 12.

- [ ] **Step 4: Write failing shuffle-integrity test**

For `n=50`, assert `deranged_waveforms` preserves the multiset of complete four-feature row tuples exactly, has no row in its original position, and is deterministic for seed `500123`.

- [ ] **Step 5: Write failing residualization-provenance test**

With six toy training trajectory tables and two held-out tables, assert each training seed's residualizer provenance contains exactly the other five training seeds; each test seed provenance contains all six training seeds; no test seed appears in any fit set. Assert output residual arrays match waveform shape and are finite even for constant waveform columns.

- [ ] **Step 6: Implement passive coupling, event tables, timing normalization, shuffle, residualization, and arm construction**

Use Gate A `observed_x` normalization semantics for cable drive. Raw-input delays are 12 causal samples ending at `availability_index`; use the existing `delay_features(..., width=12, stride=1)` zero-padding behavior so secondary baselines do not alter event identity.

- [ ] **Step 7: Add causality and data-separation tests**

Assert changing observed input strictly after a completed event's availability time does not change that event's stored onset/features. Assert `fit_forecasters` signature contains only `features_by_arm`, `targets`, and `ridge_factor`; inspect that `residualize_waveforms` has no forecast-target or hidden-state argument.

- [ ] **Step 8: Add degenerate-case tests**

Assert no-spike and single-spike emission produce empty event tables without NaNs; constant timing and constant waveform columns remain finite through timing normalization, residualization, and `QuadraticReadout` fitting.

- [ ] **Step 9: Run Task 2 GREEN and full regression**

Run:
```bash
python -m unittest tests.test_gate_c0 -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add emitted_state/gate_c0.py tests/test_gate_c0.py
git commit -m "feat: build Gate C0 event controls"
```

### Task 3: Frozen experiment runner, viability, evidence, and negative control

**Files:**
- Create: `scripts/run_gate_c0.py`
- Create: `tests/test_gate_c0_receipt.py`

**Interfaces:**
- Consumes: Task 2 protocol/tables/arms and existing `normalized_rmse`, Gate A `r2_score`.
- Produces:
  - `run_experiment(protocol: GateC0Protocol | None = None) -> dict`.
  - `scientific_payload(receipt: dict) -> dict` excluding runtime-only metadata.
  - CLI: `python scripts/run_gate_c0.py [--quick] [--output PATH]`.

- [ ] **Step 1: Write failing reduced-receipt test**

Use a smoke protocol with two train seeds, two test seeds, shorter burn/observe values, and `min_primary_events=5`. Assert receipt contains `protocol`, `emitter`, `event_counts`, `conditions`, `primary_evidence`, `negative_control`, `claim_boundary`, `source_sha256`, and runtime versions. Every condition/horizon present in a viable smoke run must report every arm and per-trajectory NRMSE/R².

- [ ] **Step 2: Write failing viability test**

Use a deliberately impossible smoke threshold larger than available events. Assert `run_experiment` returns `primary_evidence.status == "not_viable"`, names every sub-threshold trajectory and count, and does not silently alter drive parameters or throw away the receipt.

- [ ] **Step 3: Write failing evidence-rule tests on synthetic metrics**

Pin C0-A so the same three test seeds must beat both timing-only and shuffled controls; separate wins against different controls must fail. Pin C0-B to mean improvement plus at least three per-trajectory wins versus timing-only.

- [ ] **Step 4: Write failing negative-control threshold test**

Freeze label seed `700000 + trajectory_seed`. Assert a synthetic control with NRMSE `0.95`, R² `0.0` passes; NRMSE `0.89` fails; R² `0.051` fails. Positive C0 claims must be forced false when the negative control fails even if forecast metrics otherwise meet C0-A/B.

- [ ] **Step 5: Implement the runner in two passes per noise condition**

Pass 1: generate worlds/observations/passive states for all trajectories, fit observed-x and soma statistics on training trajectories only. Pass 2: drive the emitter for train/test using those training soma statistics, build event tables, timing stats, residuals, and arms. Residualization/timing normalization use all valid eight-ISI training events independent of forecast horizon; forecasting fits use only horizon-eligible rows.

- [ ] **Step 6: Implement receipt detail**

Record per trajectory: detected spike count, valid waveform count, each exclusion reason, eight-ISI eligible count, scored count for each horizon, waveform-feature mean/std/min/max, and soma normalization used. Record source SHA256 for `emitter.py`, `gate_c0.py`, `cable.py`, `world.py`, `readout.py`, and `run_gate_c0.py`.

- [ ] **Step 7: Implement independent event-label control**

Use the `timing_real_waveform` feature matrix because it is the richest primary receiver. Generate one Gaussian label per scored event from `700000 + seed`, fit only training event labels, evaluate held-out labels, and report mean/per-trajectory NRMSE/R² plus `passed_chance_check` under the frozen `NRMSE>=0.90 and R²<=0.05` rule. Keep its model/features/weights isolated from all forecast fits.

- [ ] **Step 8: Run smoke RED→GREEN and regression**

Run:
```bash
python -m unittest tests.test_gate_c0_receipt -v
python scripts/run_gate_c0.py --quick --output /tmp/gate_c0_quick.json
python -m unittest discover -s tests -v
```

Expected: tests pass, quick receipt is written outside the repository, and no full-protocol scientific result has been inspected yet.

- [ ] **Step 9: Commit before the full run**

```bash
git add scripts/run_gate_c0.py tests/test_gate_c0_receipt.py
git commit -m "feat: add frozen Gate C0 experiment runner"
```

### Task 4: Run the frozen full protocol once and publish the result unchanged

**Files:**
- Create: `results/gate_c0_receipt.json`
- Create: `docs/gate_c0_findings.md`
- Modify: `README.md`
- Modify: `docs/progress.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: the committed Task 3 runner without scientific-constant edits after result inspection.
- Produces: permanent full receipt plus bounded interpretation.

- [ ] **Step 1: Run the full frozen protocol once**

Run:
```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_c0.py --output results/gate_c0_receipt.json
```

Expected: either a viable complete receipt or a `not_viable` receipt. Both are valid outcomes. Do not change emitter mapping, feature definitions, thresholds, event selection, or reader settings after reading it.

- [ ] **Step 2: Run the full unit suite after the receipt exists**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 3: Write findings from the receipt only**

`docs/gate_c0_findings.md` must report event viability first, then C0-A, C0-B, timing/shuffle/residual comparisons, secondary arms, negative control, waveform distributions, and failure localization. If nonviable, do not discuss unrun forecast claims as results.

- [ ] **Step 4: Update README and handoff without rewriting Gate A history**

README gets a Gate C0 status/result section and links to the new findings/receipt. `docs/progress.md` records branch, exact result commit, commands actually run, headline metrics or nonviability counts, unresolved caveats, and one precise next action. `AGENTS.md` must say Gate C0 result is frozen and no synapse/full Gate C work starts without a new user request.

- [ ] **Step 5: Commit the frozen evidence**

```bash
git add results/gate_c0_receipt.json docs/gate_c0_findings.md README.md docs/progress.md AGENTS.md
git commit -m "results: freeze Gate C0 waveform-state experiment"
```

### Task 5: Independent receipt comparison and CI reproduction

**Files:**
- Create: `scripts/compare_gate_c0_receipts.py`
- Create: `tests/test_gate_c0_compare.py`
- Modify: `.github/workflows/checks.yml`
- Modify: `docs/progress.md`

**Interfaces:**
- Consumes: committed Gate C0 receipt and `scripts.run_gate_c0.scientific_payload` schema.
- Produces: environment-independent scientific comparison with `rtol=1e-9`, `atol=1e-10` and a CI rerun on Python 3.12.

- [ ] **Step 1: Write failing comparator tests**

Assert identical scientific payloads compare equal despite different runtime metadata. Mutating one forecast NRMSE by `1e-3`, one event count, one exclusion count, or one C0 pass/fail boolean must make comparison fail.

- [ ] **Step 2: Implement `compare_gate_c0_receipts.py`**

Reuse comparison semantics from `scripts/compare_receipts.py` but keep Gate A's comparator untouched. Ignore only runtime/environment metadata; event counts, waveform summaries, protocol, evidence, negative control, and claim boundary are scientific and must compare.

- [ ] **Step 3: Run comparator tests and fresh local reproduction**

Run:
```bash
python -m unittest tests.test_gate_c0_compare -v
OPENBLAS_NUM_THREADS=1 python scripts/run_gate_c0.py --output /tmp/gate_c0_verify.json
python scripts/compare_gate_c0_receipts.py results/gate_c0_receipt.json /tmp/gate_c0_verify.json
```

Expected: tests pass and comparator prints a scientific-payload match.

- [ ] **Step 4: Extend GitHub Actions only after the receipt exists**

Keep the existing Gate A rerun/comparison. Add a Gate C0 rerun into `/tmp/gate_c0_ci.json` with `OPENBLAS_NUM_THREADS=1`, then compare it against `results/gate_c0_receipt.json`. CI must run the complete unit suite first under Python 3.12.

- [ ] **Step 5: Commit CI/comparator**

```bash
git add scripts/compare_gate_c0_receipts.py tests/test_gate_c0_compare.py .github/workflows/checks.yml
git commit -m "ci: reproduce Gate C0 scientific receipt"
```

- [ ] **Step 6: Verify the pushed final head**

Push the feature branch, inspect the GitHub Actions job on the exact head SHA, and require success for unit tests, the frozen Gate A rerun/comparison, the full Gate C0 rerun, and Gate C0 scientific-payload comparison.

- [ ] **Step 7: Record the verified workflow run**

Update `docs/progress.md` with exact final branch SHA, workflow run ID, job conclusion, and explicit statement that implementation stops at Gate C0. Commit that documentation-only checkpoint and verify its triggered CI again before offering integration options.

## Completion Criteria

Gate C0 implementation is complete only when:

- the active emitter and waveform extractor pass deterministic unit tests,
- every primary control uses identical event identity/timing,
- training-only normalization/residualization is provenance-tested,
- the fixed full protocol has been run once and preserved even if negative or nonviable,
- the independent-label control satisfies the frozen chance check or any positive claim is suppressed,
- the committed receipt reproduces independently in GitHub Actions,
- findings and progress clearly distinguish retention, timing information, waveform information, and biological claims,
- no synapse, postsynaptic neuron, Gate B, or full Gate C implementation has begun.
