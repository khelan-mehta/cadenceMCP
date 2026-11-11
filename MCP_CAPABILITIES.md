# cadence-analog-cmos MCP Server — Capabilities Reference (edited 2026-11-09)

Python MCP server (`cadence_mcp/`, stdio) that drives a Cadence Virtuoso 6.1.7 /
Spectre 15.1 VM (VMware, RHEL 6.5) headlessly from Windows. PDK: **gpdk090**
(gpdk045 also installed; gpdk180 NOT installed). Every simulation run is
**auto-recorded** to `data/runs/` (JSON: netlist, waveforms, measures, op-info)
and is plottable in the dashboard. 40 tools, grouped:

## VM control
| Tool | What it does |
|---|---|
| `vm_status()` | VMX path, running?, guest-exec ready? |
| `vm_start()` / `vm_stop(hard)` | Power the VM on (waits for guest) / off |
| `vm_exec(bash, timeout)` | Run any bash in the guest (Cadence env preloaded) |
| `check_environment()` | Verifies spectre/virtuoso/license/PDK end-to-end |

## General simulation primitives (preferred interface)
| Tool | What it does |
|---|---|
| `simulate(netlist, measures, params, run_name)` | Run ANY Spectre deck (`{param}` placeholders filled from `params`); parses every PSF result + `op.info`; applies the measure DSL; **saves the run** |
| `measure(run_id, measures)` | Re-apply measures to a stored run |
| `optimize(netlist_template, knobs, spec, measures, params)` | Closed-loop hill-climb of knob values against a spec, live Spectre feedback |
| `run_raw_netlist(netlist, run_name)` | Bare deck run, no measure pass |
| `list_metrics()` | The measure-DSL vocabulary: `gain_db, gain_vv, dc_gain_db, bandwidth_hz, gbw_hz, unity_gain_hz, phase_margin_deg, vt0, kn, lambda, slew_rate, thd, delay, value_at, min, max, pp, rms, mean, cross, power, device` (+ transforms `abs, db, sqrtabs`) |
| `list_templates()` / `get_template(name)` | Parameterized starter decks: `mos_iv`, `cs_amp`, `diff_amp`, `inverter_cell`, `vtc_adc` — each with params/knobs/measures |

## Course experiments (Nirma ACIC lab manual, 10 experiments)
| Tool | What it does |
|---|---|
| `list_experiments()` / `get_experiment_params(id)` | Catalog + authoritative param list per experiment |
| `run_experiment(id, params)` | Build deck from params, simulate, measure, **record** |
| `run_parametric(id, sweep_param, values, params)` | One run per value, overlaid curves (e.g. gain vs Rs) |
| `run_montecarlo(id, runs, params)` | MC statistical runs |
| `compute_cmrr(diff_run_id, cm_run_id)` | CMRR from a differential + common-mode run pair |
| `auto_size(experiment, spec, knobs, iterations)` | Coordinate-descent sizing with saturation penalty |
| `get_schematic(experiment, params)` | SVG schematic of the experiment netlist |
| `read_lab_manual()` | The extracted lab-manual text |

Experiments: 1 inverter pre/post-layout · 2 MOS I-V + VT0/Kn/γ/λ extraction ·
3 current mirrors · 4 CS amp (resistive / current-source load) ·
**5 source-degenerated CS + parametric Rs** · 6 CD & CG + noise/harmonic ·
7 cascode + MC + P1dB/IIP3 · 8 diff amp (CMRR/ICMR/GBP) · 9 two-stage op-amp ·
10 open project.

## Run recording & inspection (everything is kept)
| Tool | What it does |
|---|---|
| `list_runs(experiment, limit)` | Stored run index (id, time, measures) |
| `get_run(run_id, include_waveforms)` | Full record: netlist, measures, op-info, analyses |
| `get_signal(run_id, analysis, signal)` | One waveform as x/y arrays |
| `delete_run(run_id)` | Remove a stored run |
| `open_dashboard()` | Plotly SPA at http://127.0.0.1:8765 — plot any signal of any stored run, device op-param cards, SVG schematics, can trigger sims |

## Devices / PDK
`list_devices()` / `get_device(name)` — gpdk090 device info (nmos1v/2v, pmos,
resistors, caps; models, typical params).

## Physical design (headless Virtuoso SKILL via Xvfb)
| Tool | What it does |
|---|---|
| `skill(code)` / `run_skill(code)` | Arbitrary SKILL in a headless Virtuoso boot |
| `generate_schematic(device, w, l, cell, lib)` | Schematic cellview with a sized device |
| `generate_layout(...)` / `generate_inverter_layout(...)` | Sized pcell layout / routed inverter layout |
| `build_inverter_cell(wn, wp, l)` | Schematic + routed layout + DRC + LVS in ONE boot |
| `run_drc(cell)` / `run_extract(cell)` / `run_lvs(lay, sch)` | Diva verification (gpdk090 decks) |

## Digital subsystem
`list_cpu_demos` / `run_cpu` / `assemble_program` / `export_cpu_verilog`
(8-bit Amaranth CPU + cache, VCD traces recorded) ·
`list_cells` / `characterize_cell` / `get_cell_netlist` / `run_ring_oscillator`
(transistor-level gpdk090 standard cells) · `build_vtc_adc(...)`.

## Known limits
- gpdk180 not installed (use gpdk090 `nmos2v` at 1.8 V for "0.18µm-class" work).
- No QRC/PEX license → parasitics are techfile-coefficient estimates.
- OCEAN/GUI need Xvfb; raw `spectre` is the simulation path.
- VM disk was factory-reset ~Nov 2026; back up guest work via tar + `vm_exec`.
