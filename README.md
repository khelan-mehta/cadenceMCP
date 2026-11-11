# Cadence Analog CMOS — MCP Server + Dashboard

Drives a headless **Cadence Virtuoso / Spectre 15.1** install (running inside a
VMware VM) from **Claude Desktop** to perform all 10 experiments of the Nirma
University *4EC601ME25 Analog CMOS Integrated Circuits* lab — with every
parameter tweakable, automatic measurement extraction, a device/library browser,
circuit schematics, and a plotting dashboard.

Target PDK: **gpdk090** (90 nm). No license daemon needed — the uncounted
license is used directly via `CDS_LIC_FILE`.

## Architecture

```
Claude Desktop ──stdio──> cadence_mcp.server (MCP)
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                       │
   vmrun bridge         result store            dashboard (:8765)
   (vm.py) ──> VMware VM  (data/runs/*.json)    (Plotly SPA, plots
        │        │                                any signal, devices,
        │   spectre (raw, headless, psfascii)     schematics; can run sims)
        │        │
        │   PSF parser (psf.py) + op-point parser (opparse.py)
        │        │
        └──> measure.py (VT0, Kn, λ, gain, BW, PM, SR, THD, CMRR, ICMR…)
```

Every simulation is a self-contained Spectre deck (`experiments.py`) built from
your parameters, run on the VM, parsed, measured, and stored for plotting.

## Setup

1. Install deps (host):
   ```
   pip install -r requirements.txt
   ```
2. Add the server to Claude Desktop — merge `claude_desktop_config.example.json`
   into `%APPDATA%\Claude\claude_desktop_config.json`, then restart Claude Desktop.
3. In Claude, try: *"list experiments"*, *"run experiment 2 with device
   gpdk090_nmos1v"*, *"open the dashboard"*.

The dashboard also runs standalone: `run_dashboard.bat` → http://127.0.0.1:8765/

## Experiments (all tweakable)

| # | Title | Key extracted results |
|---|-------|-----------------------|
| 1 | CMOS inverter | VTC, switching threshold VM, propagation delay |
| 2 | MOS I–V characteristics | VT0, Kn, γ, λ, fT, op-point |
| 3 | Current mirrors (simple/cascode/PMOS) | IBIAS vs Rcs, <10% range |
| 4 | CS amplifier (R / NMOS / PMOS load) | gain, BW, swing, noise, power |
| 5 | Source-degenerated CS + parametric Rs | gain vs Rs |
| 6 | CD & CG amplifiers | gain, BW, noise, THD |
| 7 | Cascode + Monte-Carlo + P1dB/IIP3 | gain, corner spread, compression |
| 8 | Differential amplifier | Adm, Acm, CMRR, ICMR, GBP |
| 9 | Two-stage opamp | gain, GBP, PM, slew rate, ICMR, power |
| 10| Open project | any Spectre deck / analysis |

## Digital subsystem (8-bit CPU + cache — hybrid ASIC flow)

Spectre is analog-only, so digital design is added as a second engine:

- **Functional (Amaranth HDL):** an 8-bit accumulator CPU with 256 B RAM and a
  direct-mapped cache. Assemble + simulate programs in pure Python (VCD + full
  cycle trace), report cache hit-rate / effective cycles, and **export synthesizable
  Verilog** (`cpu8.v`). Demos: `sum_1_to_n`, `fibonacci`, `count_down`.
- **Transistor-level (Spectre / gpdk090):** the same logic as real standard cells
  (`INV NAND2 NOR2 DFF FA SRAM6T`), characterized in SPICE — inverter tpHL/tpLH,
  ring-oscillator frequency & stage delay, full-adder truth table, 6T SRAM
  write/read, DFF timing. This ties the CPU's gates back to the gpdk090 analog flow.

This is the standard ASIC split: verify the whole CPU functionally, characterize the
critical cells at transistor level. A *full* CPU+cache in SPICE is impractical on this
VM (too many transistors); the cell library + functional CPU together cover it.

## Physical design + closed-loop sizing (SKILL/Xvfb bridge)

Virtuoso's OpenAccess/layout/verification engine is driven **headless** via
`virtuoso -nograph` under Xvfb (`skill.py`). This makes the whole GUI-layer
prompt-drivable:

- **`run_skill`** — run arbitrary SKILL headless (the universal escape hatch:
  create/edit libraries, schematics, layouts, netlist, drive Diva).
- **`generate_layout` / `generate_inverter_layout`** — real gpdk090 pcell layout
  from W/L/fingers (returns bounding box).
- **`generate_schematic`** — schematic cellview with a device + pins.
- **`run_lvs`** — Diva layout-vs-schematic (positional `ivLVS`).
- Diva **DRC / parasitic-extraction** use compiled, form-driven functions whose
  batch prop-list is undocumented on this appliance → driven case-by-case through
  `run_skill` (the functions `ivDRC`/`ivExtract` are confirmed present).

**`auto_size`** — closed-loop design: give a spec and the knobs to tune, and it
iterates the circuit with live Spectre feedback until the spec is met, keeping
devices in saturation. Example (Exp 4, the manual's spec):
`spec={"dc_gain_db":{">=":20},"power_w":{"<=":1e-3}}, knobs=["w","rd"]`
→ converges to W≈17.8 µm, RD≈20 kΩ, 20.1 dB, 127 µW.

## General primitives (compose any design by prompting)

The core of the server is a small set of **general, composable** tools — you don't
need a bespoke tool per circuit:

- **`simulate(netlist, measures)`** — run ANY Spectre deck; return parsed waveforms
  + requested measurements; save a plottable run. Subsumes `run_experiment`,
  `characterize_cell`, `build_vtc_adc`, …
- **`measure(run_id, measures)`** — apply the whole measurement library to any stored
  run (gain/BW/PM/VT0/Kn/λ/slew/THD/delay/value_at/min/max/rms/power/device-op…).
- **`optimize(netlist_template, knobs, spec, measures)`** — closed-loop design on any
  `{param}` netlist; tune knobs until the spec is met via live Spectre feedback.
- **`skill(code)`** — run ANY SKILL headless (schematic/layout/verify/netlist).
- **`list_metrics`**, **`list_templates`**, **`get_template`** — discover metrics and
  load parameterized design templates (data) to feed `simulate`/`optimize`.

Templates (MOS I-V, CS amp, diff amp, inverter cell, VTC-ADC, …) are **data**, not
tools: load one with `get_template`, edit params, pass to `simulate`/`optimize`.
Adding a new circuit is prompting — no new Python.

## MCP tools

- **General:** `simulate`, `measure`, `optimize`, `skill`, `list_metrics`,
  `list_templates`, `get_template`
- **VM/env:** `vm_status`, `vm_start`, `vm_stop`, `vm_exec`, `check_environment`
- **Physical/design:** `run_skill`, `generate_layout`, `generate_inverter_layout`,
  `generate_schematic`, `run_lvs`, `auto_size`
- **Analog experiments:** `list_experiments`, `get_experiment_params`, `run_experiment`,
  `run_parametric`, `run_montecarlo`, `compute_cmrr`, `run_raw_netlist`
- **Digital:** `list_cpu_demos`, `run_cpu`, `assemble_program`, `export_cpu_verilog`,
  `list_cells`, `characterize_cell`, `run_ring_oscillator`, `get_cell_netlist`
- **Library:** `list_devices`, `get_device`
- **Results:** `list_runs`, `get_run`, `get_signal`, `delete_run`
- **View:** `get_schematic`, `open_dashboard`, `read_lab_manual`

## Notes

- Layout / DRC / LVS / RC-extraction (Exp 1 & 9 post-layout) are GUI Virtuoso+Diva
  steps; the decks here deliver the pre-layout electrical results. Post-layout
  re-sim reuses the same deck with an extracted netlist.
- `data/runs/` holds one JSON per run (params + waveforms + measurements).
