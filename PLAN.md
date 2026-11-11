# PLAN.md — Analog Block Library & Surrogate Data Factory (Schematic-Level)

**Owner:** cadence MCP project
**Created:** 2026-08-01
**Status:** APPROVED FOR EXECUTION — do NOT start coding phases out of order.
**Scope lock:** **Schematic-level only. Layout and PEX are entirely out of scope.** The
deliverable is a working prototype that ends at a *simulated, verified schematic*.

**Prime directives:**
1. **SPICE is ground truth.** Every ML output is verified against SPICE before it is trusted.
2. **A schematic has no output params by itself** — it must be netlisted and re-simulated,
   and that re-sim must reproduce the verified deck (schematic-equivalence check).
3. **Nothing composes into a larger circuit without a final full-SPICE check.**
4. **Standardize the simulator, then measure.** Uncontrolled solver/extraction settings are
   self-inflicted label noise; freeze them so the surrogate isn't fighting our own scatter.

---

## 0. Purpose & Scope

Build, on the existing `gpdk090` headless-Spectre engine, a reusable **analog block
library** where every block has: a parameterized netlist, a clean provenance-tagged
dataset, a per-topology surrogate model, and a characterized interface (I/O impedance +
loading). Then a **composition engine** that fetches pre-characterized blocks, wires them
into larger circuits, predicts system behavior interface-aware, and verifies with one
full-SPICE run. Finally an **interaction-memory database** that remembers how any two
blocks behaved when connected, so predictions improve and known-good pairings aren't
re-derived.

**Decisions locked (do not re-litigate):**
- Lead use case = **surrogate-data generation** (fast, quantified ROI).
- **Generic PDK only** (`gpdk090`). Engine stays PDK-abstracted so a swap is possible.
- **Per-topology surrogates** (one model per block). Cross-topology GNN = north-star, out of scope.
- **Schematic-level only.** No layout generation, no parasitic extraction, no post-layout
  data in this plan. The end state is a schematic that re-simulates to the verified numbers.
- Analog blocks do **not** compose perfectly on prediction alone (interface loading) — handled
  explicitly in Phase 4 & 5.

**Explicitly OUT of scope:** layout, PEX/QRC/Calibre parasitics, proprietary PDK, true
statistical Monte-Carlo sign-off, functional-verification ML, tape-out. (Layout-aware
fidelity and statistical yield data are a *later* program, not this prototype.)

---

## 1. Guiding Principles (apply to every phase)

1. **SPICE is ground truth.** Surrogates propose; SPICE disposes.
2. **Interface is a characterized dimension** — blocks are characterized *with* source/load
   swept as inputs, never in a vacuum.
3. **Freeze the simulator per dataset.** One fixed set of tolerances / `errpreset` / timestep /
   analysis grids / temperature, recorded in provenance. Changing them = a new dataset version.
4. **Hidden variables become features, not noise.** Corner, temperature, (and MC seed if used)
   are explicit dataset columns — never silent variance the model has to average over.
5. **Deterministic vs stochastic are different products.** Well-behaved circuits at fixed
   settings are deterministic → the surrogate is a *fast interpolator*. Mismatch/metastability/
   startup circuits produce *distributions* → those get distributional labels (mean+σ), not a scalar.
6. **Reproducibility is mandatory.** Every row carries: seed, PDK name + model-file SHA, corner,
   temp, sim-settings id, tool version, converged-flag, operating-region flag, run_id.
7. **Fail closed.** Non-converged / NaN / out-of-range sims never enter a dataset; logged + dropped.
8. **Composable mechanics already exist** (`digital/cells.py::CELL_SUBCKTS`, `designs/vtc_adc.py`).
   Reuse subckt-stitching; do not reinvent netlist assembly.
9. **No phase starts until the previous Gate passes** — all boxes checked, evidence committed.

---

## 2. Directory & Artifact Layout

```
cadence MCP/
├── PLAN.md
├── library/
│   ├── elements.json               # Phase 1: full gpdk090 primitive catalog
│   ├── sim_settings.json           # Phase 2: the FROZEN simulator profile(s)
│   ├── blocks/<block_id>/
│   │   ├── block.json              # spec: netlist, knobs, interface knobs, measures, ports, io_model
│   │   ├── dataset.parquet         # (X,y) table
│   │   ├── dataset.meta.json       # provenance + sampling + sim-settings id + drop-reasons
│   │   └── surrogate.pkl           # trained model + metrics
│   └── interactions/interactions.parquet   # Phase 5: pairwise "how they behaved together"
├── cadence_mcp/
│   ├── elements.py                 # NEW — loads/serves elements.json
│   ├── sampling.py                 # NEW — DOE (LHS/Sobol/grid/random/adaptive)
│   ├── batch.py                    # NEW — parallel run orchestration + QA + determinism check
│   ├── dataset.py                  # NEW — collate runs -> parquet + provenance
│   ├── surrogate.py                # NEW — train/eval/predict (scalar or distributional)
│   ├── compose.py                  # NEW — assemble + interface-aware predict + verify + equiv-check
│   ├── interactions.py             # NEW — read/write interaction memory
│   ├── templates.py                # EXTEND
│   ├── api.py spectre.py store.py metrics.py measure.py sizing.py physical.py  # REUSE
│   └── config.py                   # EXTEND — LIBRARY_DIR, model-file hashing, sim-settings profiles
└── data/                           # existing run store (unchanged)
```

**Config additions:** `LIBRARY_DIR`; SHA-256 of `PDK_MODEL_INCLUDE`; named simulator-setting
profiles (tolerances, errpreset, timestep, AC pts/decade, DC step, temp).

---

## 3. Canonical Schemas (freeze after Phase 1)

### 3.1 Dataset row (`dataset.parquet`)
| group | columns |
|---|---|
| design knobs | one per block knob (`w`, `l`, `rd`, `L`, `C`, …) — SI floats, not "10u" strings |
| interface knobs | `src_R`, `load_R`, `load_C` (as the block exposes) |
| conditions (explicit features) | `corner`, `temp_c`, `seed`, `sim_settings_id` |
| labels | one per measure (`gain_db`, `bw_hz`, `f0_hz`, `il_db`, `s21_db`, `pm_deg`, `power_w`, …) |
| stochastic labels (when applicable) | `<measure>_mean`, `<measure>_std` over MC seeds |
| flags | `op_region` (sat/triode/subthreshold summary), `converged` |
| provenance | `run_id`, `pdk_name`, `model_sha`, `created` |

### 3.2 Block spec (`block.json`)
```json
{
  "block_id": "lc_lowpass",
  "class": "filter",
  "description": "2nd-order LC low-pass",
  "netlist": "<parameterized Spectre deck with {knobs} and {interface} placeholders>",
  "knobs":           {"L": {"min":1e-9,"max":100e-9,"scale":"log"}, "C": {"min":1e-13,"max":1e-11,"scale":"log"}},
  "interface_knobs": {"src_R": {"min":25,"max":100}, "load_R": {"min":25,"max":1e6,"scale":"log"}, "load_C": {"min":0,"max":1e-12}},
  "measures":  [ {"name":"f0_hz","metric":"...","analysis":"acs","signal":"out"} ],
  "ports":     [ {"name":"in","kind":"signal"}, {"name":"out","kind":"signal"} ],
  "stochastic": false,                          // true -> distributional labels + MC path
  "io_model":  {"Zin":null,"Zout":null,"transfer":null},
  "dataset":"dataset.parquet", "surrogate":"surrogate.pkl",
  "surrogate_metrics": {"r2":null,"mae":null,"n_train":null}
}
```

### 3.3 Interaction-memory row (`interactions.parquet`) — Phase 5
| group | columns |
|---|---|
| identity | `pair_id`, `blockA_id`, `blockB_id`, `interface_net` |
| A / B | `A_params`, `A_predicted_iso`, `B_params`, `B_predicted_iso` (json) |
| interface | `interface_conditions` (actual Z each side sees) |
| truth | `measured_system` (full-SPICE of the connected pair) |
| learning | `delta` (measured − predicted), `correction` (fitted loading correction) |
| provenance | `run_id`, `model_sha`, `created` |

**Intention:** the memory of "how two devices behaved when kept together" — lets us (a) skip
re-simulating a known-good pairing at a known config, and (b) train a small **loading
correction** that turns two isolated predictions into an accurate connected one.

---

## PHASE 1 — Complete the gpdk090 Element Catalog ("add all elements")

**Intention.** Can't build datasets for arbitrary circuits while only MOS variants are exposed.
Enumerate **every** `gpdk090` primitive (params, ranges, terminals) + the ideal passives
analog/RF circuits need (L, C, mutual inductor, ideal port/tline). Make each instantiable and
proven to simulate.

**Steps.**
1. Introspect the PDK on the VM (`vm_exec`/`check_environment`): every device/subckt name and
   model section in `PDK_MODEL_INCLUDE`.
2. Per element: terminals, instance params, default, **verified** min/max (from model file, not
   guessed), units, model section, `source:"pdk"`.
3. Add ideal behavioral passives (`resistor/capacitor/inductor/mutual_inductor/port`),
   `source:"ideal"`.
4. `library/elements.json` + `cadence_mcp/elements.py` + tools `list_elements`/`get_element`.
5. Smoke-test every element: trivial DC-op + small-AC deck via `api.simulate`; confirm converge + parse.

**GATE 1:**
- [ ] Every element passes its smoke-test (converges + parses).
- [ ] Every param range verified against the PDK model file.
- [ ] Ideal passives present + tagged.
- [ ] Catalog enumerable via tool and loadable by `templates.py`/`api.py`.
- [ ] `model_sha` recorded.

---

## PHASE 2 — Dataset-Generation Infrastructure (circuit-agnostic, deterministic)

**Intention.** Reusable machinery that turns *any* block spec into a clean, provenance-tagged,
**reproducible** dataset — with self-inflicted noise engineered out.

**Steps.**
1. **Freeze simulator profile(s)** → `library/sim_settings.json` (tolerances, `errpreset`,
   transient `maxstep`, AC pts/decade, DC step, temp). Referenced by `sim_settings_id`.
2. `sampling.py` — DOE over `knobs` + `interface_knobs`: LHS / Sobol / grid / random / adaptive.
   Respect `scale: log|linear` + bounds. Deterministic under `seed`.
3. `batch.py` — fan `api.simulate` across N parallel guest-exec workers (license uncounted → no
   seat cap). Includes retry/timeout, and:
   - **QA filter:** drop non-converged / NaN / out-of-physical-range; log why.
   - **Determinism gate:** re-run a random sample of points twice; flag any label that differs
     beyond ε (root-cause = adaptive timestep or multistable DC before proceeding).
   - **Operating-region tag:** derive `op_region` per point from `op.info`.
4. `dataset.py` — collate to `dataset.parquet` + `dataset.meta.json` (sampling cfg, seed,
   PDK+model_sha, sim_settings_id, tool version, counts, drop-reasons, determinism-check result).
5. Tool `generate_dataset(block_id, n, method, seed)`.

**GATE 2:**
- [ ] Output Parquet matches frozen §3.1 schema, with `sim_settings_id` + `op_region` populated.
- [ ] Same `seed` ⇒ identical sample points (determinism of sampling).
- [ ] **Label-determinism check passes**: re-run scatter within ε for well-behaved points;
      any exceedance is root-caused, not ignored.
- [ ] QA provably drops an injected divergent point (logged), drop-rate reported.
- [ ] ≥1000-point parallel run completes and is measurably faster than serial.
- [ ] Full provenance on every row.

---

## PHASE 3 — Block Library + Datasets + Surrogates

**Intention.** Define reusable analog blocks, characterize each **with interface/loading as
inputs**, and train a per-block surrogate — scalar for deterministic blocks, **distributional**
for stochastic ones.

**Starter blocks (build in order, each a `block.json`):**
1. `current_mirror` 2. `cs_amp` 3. `diff_pair_load` 4. `source_follower`
5. `two_stage_opamp` 6. `rc_lowpass` 7. `lc_lowpass` (RF) 8. `lc_bandpass` (RF)
9. `comparator` (stochastic: offset) 10. `lna` (if elements support)

**Steps (per block).**
1. `block.json`: netlist with `{knobs}` **and** `{interface}` placeholders, measures, ports,
   `stochastic` flag.
2. `generate_dataset` → ≥1000 valid rows.
3. Characterize **I/O model** (`Zin`, `Zout`, transfer) → `block.json::io_model`.
4. `surrogate.py`: train (GBT/GP baseline; MLP if needed). Input = knobs+interface+conditions
   (+`op_region`). Output = measures. **Stochastic blocks:** run MC seeds, train on mean+σ.
   Save `surrogate.pkl` + held-out metrics.
5. **Headline metric:** on ≥2 blocks show (a) surrogate accuracy vs SPICE, (b) **SPICE-calls
   saved** when the surrogate guides `optimize` vs raw `optimize`.

**GATE 3 (per block + library):**
- [ ] ≥1000 valid rows, interface knobs included.
- [ ] Deterministic block: held-out **R² ≥ 0.9** per label (or documented reason + more data).
      Stochastic block: predicted σ validated against MC spread.
- [ ] Surrogate verified vs **fresh SPICE** at ≥5 random points, mean error within stated tol.
- [ ] `io_model` populated.
- [ ] Headline "SPICE-calls saved" produced on ≥2 blocks and written up.

---

## PHASE 4 — Composition Engine (schematic-level system assembly)

**Intention.** Fetch pre-characterized blocks, wire into a larger circuit, predict the *system*
interface-aware, verify with one full-SPICE run, re-tune the bad interface if needed.

**Steps.**
1. `compose.py::assemble(blocks, wiring)` — concatenate block subckts + net connections into one
   valid Spectre deck (reuse the existing stitching mechanic).
2. **Interface-aware prediction:** for each internal connection compute the real load each side
   presents (from neighbors' `io_model`), query each surrogate **at that load**; solve
   iteratively where sides mutually load.
3. **Verify:** run the assembled deck once in real Spectre; measure system specs.
4. **Reconcile & re-tune:** predicted vs measured; if an interface is off, local-`optimize` that
   boundary and re-verify.
5. Record outcome to interaction memory (Phase 5).

**GATE 4:**
- [ ] `assemble` produces a deck that simulates for ≥3 distinct 2-block pairings.
- [ ] Interface-aware prediction **beats naive** isolated-surrogate composition (report both errors).
- [ ] Every composed result ends with an enforced **full-SPICE verification** (in code, not optional).
- [ ] Re-tune loop demonstrably fixes ≥1 deliberately-mismatched interface.

---

## PHASE 5 — Interaction-Memory Database ("remember how two blocks behaved together")

**Intention.** Persist every composition outcome so the system reuses known-good pairings and
**learns a loading correction** that makes future predictions accurate first-try.

**Steps.**
1. `interactions.py` — append a §3.3 row on every Phase-4 composition.
2. **Lookup:** before composing, query for a close prior (same pair + similar configs +
   interface); if within tolerance, predict from stored correction and use a lighter verification.
3. **Learning:** as rows accumulate for a pair, fit a small correction (delta vs interface
   conditions); feed back into Phase-4 prediction.
4. Tools `remember_interaction`, `lookup_interaction`.

**GATE 5:**
- [ ] Every Phase-4 composition writes exactly one interaction row (append-only).
- [ ] A repeated pairing at a seen config is served from memory, matching earlier full-SPICE within tol.
- [ ] With ≥N rows for a pair, fitted correction **reduces** first-try interface error vs Phase-4 baseline.

---

## PHASE 6 — Agentic Layer + Schematic Output + Demo

**Intention.** A natural-language prompt drives the whole factory and ends at a **real Virtuoso
schematic that re-simulates to the verified numbers.**

**Steps.**
1. Prompt → agent decomposes into blocks → fetch (or trigger a new dataset build) → `compose` →
   full-SPICE verify.
2. **Author schematic** via `skill()` with the verified values.
3. **Schematic-equivalence check (mandatory):** netlist the drawn schematic, re-simulate with the
   same frozen settings/testbench, and confirm its measures match the verified deck within tol.
   The usual diff is device S/D geometry (AS/AD/PS/PD) or `m`/fingers — reconcile if it appears.
4. **Active-learning demo:** surrogate proposes next best batch → `batch` simulates → dataset grows
   → surrogate retrains; show accuracy improving.
5. Package the headline numbers (Phase 3 accuracy/calls-saved, Phase 4 composition accuracy,
   Phase 5 memory learning curve) behind one entry point.

**GATE 6:**
- [ ] One prompt → verified multi-block circuit → authored schematic, end-to-end.
- [ ] **Schematic re-simulates to the verified deck within tolerance** (equivalence proven, not assumed).
- [ ] Active-learning loop shows measurable accuracy gain per added batch.
- [ ] Demo runs from one entry point and reproduces the headline numbers.

---

## 4. Global "Definition of Done"
- [ ] Full gpdk090 element catalog, all smoke-tested.
- [ ] Reproducible dataset factory (frozen sim settings + sampling + parallel + QA + determinism check).
- [ ] ≥10 blocks, each with ≥1000-row dataset, I/O model, validated surrogate (scalar or distributional).
- [ ] Composition engine that beats naive prediction and always full-SPICE-verifies.
- [ ] Interaction-memory DB that provably improves interface prediction over time.
- [ ] Prompt-driven demo ending in a schematic that re-simulates to the verified numbers.

## 5. Standing Rules (never violate)
1. No ML number is final without a SPICE verification behind it.
2. No schematic is "done" until it re-simulates to the verified deck (equivalence check).
3. No phase begins before the prior Gate is fully checked and evidence committed.
4. Every dataset/interaction row carries full provenance (§3.1 / §3.3).
5. Simulator settings are frozen per dataset; hidden variables are features, never silent noise.
6. Bad sims are dropped and logged, never silently included.
7. Engine stays PDK-abstracted — no hard-coding that blocks a future PDK swap.
8. Schemas in §3 are frozen after Phase 1; changes require a version bump + migration.
9. **Layout / PEX stay out of scope** — this prototype ends at the schematic.
```
