"""Cadence Analog CMOS MCP server (stdio) for Claude Desktop.

Exposes the full workflow as tools:
  VM control · experiment run/tweak · parametric/Monte-Carlo · raw Spectre ·
  device catalog · run store · schematics · dashboard · environment mediation.
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import (api, config, core, dashboard, devices, experiments, metrics,
               schematic, spectre, store, templates, vm)

mcp = FastMCP("cadence-analog-cmos")


# =========================================================================== #
#  GENERAL PRIMITIVES — compose any design by prompting (no bespoke tools)
# =========================================================================== #
@mcp.tool()
def simulate(netlist: str, measures: list | None = None, params: dict | None = None,
             run_name: str = "sim", title: str | None = None, save: bool = True) -> dict:
    """Run ANY Spectre deck headless on the VM; return parsed waveforms + the
    requested measurements; save a plottable run for the dashboard.

    `netlist` is a complete Spectre deck (may contain {param} placeholders filled
    from `params`). `measures` is a list of measure specs (see list_metrics), e.g.
    [{"name":"gain","metric":"gain_db","analysis":"acs","signal":"out"},
     {"name":"pwr","metric":"power"}].
    This subsumes run_experiment / characterize_cell / build_vtc_adc — feed it a
    template from get_template, or your own netlist."""
    core.ensure_vm()
    return api.simulate(netlist, measures, run_name=run_name, title=title,
                        save=save, params=params)


@mcp.tool()
def measure(run_id: str, measures: list) -> dict:
    """Apply the measurement library to an already-stored run (no re-simulation).
    Same measure specs as `simulate`. Great for extracting extra metrics or
    re-analyzing a saved waveform set."""
    return api.measure_run(run_id=run_id, measures=measures)


@mcp.tool()
def optimize(netlist_template: str, knobs: dict, spec: dict, measures: list,
             params: dict | None = None, iterations: int = 16) -> dict:
    """Closed-loop design on ANY {param} netlist: tune `knobs` until `spec` (keyed
    by measure names) is met, using live Spectre feedback.

    knobs:  {"w":{"init":"10u","min":"2u","max":"200u"}, "rd":{"init":"10k"}}
    spec:   {"gain_db":{">=":20}, "power":{"<=":1e-3}}
    params: the template's other fixed placeholders (e.g. from get_template).
    measures: the measure specs producing the spec's names.
    Subsumes auto_size; works on templates or custom netlists."""
    core.ensure_vm()
    return api.optimize(netlist_template, knobs, spec, measures, params=params,
                        iterations=iterations)


@mcp.tool()
def skill(code: str, timeout: int = 400) -> dict:
    """Run ANY SKILL headless in Virtuoso (Xvfb): schematics, layout, netlisting,
    Diva DRC/LVS/extract, library ops. Print 'MCP:key=value' lines for structured
    results. The universal OpenAccess/physical-design primitive."""
    from . import physical
    core.ensure_vm()
    return physical.run_skill_raw(code, timeout=timeout)


@mcp.tool()
def list_metrics() -> dict:
    """List the measurement metrics available to `simulate`/`measure`/`optimize`,
    with the arguments each expects."""
    return {
        "metrics": metrics.available_metrics(),
        "examples": [
            {"metric": "gain_db", "analysis": "acs", "signal": "out"},
            {"metric": "bandwidth_hz", "analysis": "acs", "signal": "out"},
            {"metric": "phase_margin_deg", "analysis": "acs", "signal": "out"},
            {"metric": "vt0", "analysis": "idvgs", "signal": "Vd:p", "transform": "abs"},
            {"metric": "slew_rate", "analysis": "trans", "signal": "out"},
            {"metric": "thd", "analysis": "trans", "signal": "out", "f0": 1000},
            {"metric": "delay", "analysis": "trans", "from": "in", "to": "out", "level": 0.5},
            {"metric": "value_at", "analysis": "dcsw", "signal": "out", "at": 0.9},
            {"metric": "power"},
            {"metric": "device", "instance": "M0", "param": "gm"},
        ],
    }


@mcp.tool()
def list_templates() -> list:
    """List design templates (data) that feed `simulate`/`optimize`: MOS I-V,
    CS amp, diff amp, inverter cell, VTC-ADC, etc. Load one with get_template."""
    return templates.list_templates()


@mcp.tool()
def get_template(name: str) -> dict:
    """Return a design template: its parameterized netlist, default params,
    suggested knobs, and default measures — ready to pass to simulate/optimize."""
    t = templates.get_template(name)
    return t or {"error": f"unknown template '{name}'"}


# --------------------------------------------------------------------------- #
#  VM / environment
# --------------------------------------------------------------------------- #
@mcp.tool()
def vm_status() -> dict:
    """Report whether the Cadence VM is running and ready for guest commands."""
    return vm.status()


@mcp.tool()
def vm_start() -> dict:
    """Power on the Cadence VM (headless) and wait until it accepts commands."""
    return {"status": vm.start(wait=True), **vm.status()}


@mcp.tool()
def vm_stop(hard: bool = False) -> dict:
    """Shut down the Cadence VM (soft by default)."""
    return {"status": vm.stop(hard=hard)}


@mcp.tool()
def vm_exec(bash: str, timeout: int = 120) -> dict:
    """Run an arbitrary bash command/script inside the Cadence guest (login shell
    with the Cadence environment already set). Use for environment mediation:
    inspecting the PDK, files, licenses, running tools directly. Returns the log."""
    res = vm.run_script(bash, timeout=timeout, tag="exec")
    return {"returncode": res.returncode, "log": res.log[-6000:]}


@mcp.tool()
def check_environment() -> dict:
    """Verify the toolchain: spectre version, license, PDK model file presence."""
    body = (
        'echo "=== spectre ==="; spectre -W 2>&1 | head -3\n'
        'echo "=== license (CDS_LIC_FILE) ==="; echo $CDS_LIC_FILE\n'
        f'echo "=== model file ==="; ls -la {config.PDK_MODEL_INCLUDE} 2>&1\n'
        'echo "=== corners ==="; grep -E "^section" ' + config.PDK_MODEL_INCLUDE + ' 2>/dev/null | head\n'
    )
    res = vm.run_script(body, timeout=90, tag="checkenv")
    return {"log": res.log}


# --------------------------------------------------------------------------- #
#  Experiments
# --------------------------------------------------------------------------- #
@mcp.tool()
def list_experiments() -> list:
    """List the 10 lab experiments (id, title, CO mapping, spec, #params)."""
    return experiments.list_experiments()


@mcp.tool()
def get_experiment_params(experiment: str) -> dict:
    """Return the full tweakable-parameter schema (name, default, unit, range,
    choices, group, description) plus analyses and default plots for an experiment."""
    exp = experiments.get(experiment)
    if not exp:
        return {"error": f"unknown experiment '{experiment}'"}
    return {"id": exp.id, "title": exp.title, "spec": exp.spec, "notes": exp.notes,
            "params": exp.params, "analyses": exp.analyses,
            "plots": [p["title"] for p in exp.plots]}


@mcp.tool()
def run_experiment(experiment: str, params: dict | None = None, timeout: int = 420) -> dict:
    """Build, simulate (headless Spectre on the VM), measure and store an experiment.

    `params` overrides any subset of the schema from get_experiment_params.
    Returns extracted measurements, the per-device operating point, available
    signals, and a dashboard link. Full waveforms are saved for plotting."""
    return core.run_experiment(experiment, params, timeout=timeout)


@mcp.tool()
def run_parametric(experiment: str, sweep_param: str, values: list,
                   params: dict | None = None) -> dict:
    """Sweep one parameter across `values`, re-running the experiment each time,
    and return the key metric vs parameter (e.g. gain vs Rs for Exp 5)."""
    return core.run_parametric(experiment, sweep_param, values, params)


@mcp.tool()
def run_montecarlo(experiment: str, runs: int = 10, params: dict | None = None) -> dict:
    """Statistical spread across PDK process corners (NN/SS/SF/FF/FS) as a
    Monte-Carlo proxy; returns per-run metrics and gain mean/std/min/max (Exp 7)."""
    return core.run_montecarlo(experiment, runs, params)


@mcp.tool()
def compute_cmrr(diff_run_id: str, cm_run_id: str) -> dict:
    """CMRR (dB) = differential gain − common-mode gain, from two Exp 8 runs
    (one with input_mode=diff, one with input_mode=cm)."""
    return core.compute_cmrr(diff_run_id, cm_run_id)


@mcp.tool()
def run_raw_netlist(netlist: str, run_name: str = "raw", timeout: int = 420) -> dict:
    """Run an arbitrary complete Spectre deck on the VM and return parsed results
    (any analysis: dc/ac/tran/noise/pss/pnoise/stb/pz/sp/montecarlo…). Escape hatch."""
    core.ensure_vm()
    res = spectre.run_netlist(netlist, run_name=run_name, timeout=timeout)
    return {"ok": res.ok, "errors": res.errors, "warnings": res.warnings,
            "analyses": {n: {"kind": res.kinds.get(n), "signals": a.get("names", [])}
                         for n, a in res.analyses.items() if "data" in a},
            "opinfo_devices": len(res.opinfo.get("instances", {})),
            "log_tail": spectre.trimmed_log(res.log)}


# --------------------------------------------------------------------------- #
#  Devices / library
# --------------------------------------------------------------------------- #
@mcp.tool()
def list_devices() -> list:
    """List gpdk090 library components available for schematics/netlists."""
    return devices.list_devices()


@mcp.tool()
def get_device(name: str) -> dict:
    """Full parameter card for a gpdk090 component (instance params + op outputs)."""
    d = devices.get_device(name)
    return d or {"error": f"unknown device '{name}'"}


# --------------------------------------------------------------------------- #
#  Runs / results
# --------------------------------------------------------------------------- #
@mcp.tool()
def list_runs(experiment: str | None = None, limit: int = 50) -> list:
    """List stored simulation runs (newest first) with headline measurements."""
    return store.list_runs(experiment, limit)


@mcp.tool()
def get_run(run_id: str, include_waveforms: bool = False) -> dict:
    """Fetch a stored run. Measurements + op-point always; set include_waveforms
    to also return the raw signal arrays (large)."""
    d = store.load_run(run_id)
    if not d:
        return {"error": "run not found"}
    if not include_waveforms:
        d = {**d, "analyses": {n: {"kind": a["kind"], "sweep": a["sweep"],
                                   "signals": a["names"]} for n, a in d["analyses"].items()}}
    return d


@mcp.tool()
def get_signal(run_id: str, analysis: str, signal: str) -> dict:
    """Return the numeric array for one signal of one analysis in a run (for
    custom plotting / numeric inspection)."""
    d = store.load_run(run_id)
    if not d:
        return {"error": "run not found"}
    a = d["analyses"].get(analysis)
    if not a:
        return {"error": f"no analysis '{analysis}'"}
    return {"sweep": a["sweep"], "x": a["data"].get(a["sweep"]),
            "signal": signal, "y": a["data"].get(signal)}


@mcp.tool()
def delete_run(run_id: str) -> dict:
    """Delete a stored run."""
    return {"deleted": store.delete_run(run_id)}


# --------------------------------------------------------------------------- #
#  Schematic / dashboard / manual
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_schematic(experiment: str, params: dict | None = None) -> dict:
    """Return an annotated SVG schematic of the experiment's circuit with current
    parameter values, plus the dashboard URL that renders it live."""
    svg = schematic.render(experiment, params or {})
    return {"svg": svg,
            "dashboard": f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/#sch"}


@mcp.tool()
def open_dashboard() -> dict:
    """Start the local plotting dashboard (if not running) and return its URL.
    The dashboard plots any signal from any run, shows device cards and schematics,
    and can itself trigger simulations."""
    url = dashboard.start(background=True)
    return {"url": url}


# --------------------------------------------------------------------------- #
#  Digital subsystem (8-bit CPU + cache; transistor-level cells)
# --------------------------------------------------------------------------- #
@mcp.tool()
def list_cpu_demos() -> dict:
    """List built-in CPU demo programs and the CPU's instruction set."""
    from .digital import sim
    from .digital.cpu import OPCODES
    return {"demos": list(sim.DEMOS.keys()), "isa": list(OPCODES.keys()),
            "note": "2-byte instructions; 256B RAM; direct-mapped cache. "
                    "Pass a demo name or your own assembly to run_cpu."}


@mcp.tool()
def run_cpu(program: str, max_cycles: int = 3000, cache_lines: int = 8,
           line_bytes: int = 4, miss_penalty: int = 8) -> dict:
    """Assemble + simulate an 8-bit CPU program (functional Amaranth sim).
    `program` is a demo name (see list_cpu_demos) or assembly source. Returns
    final registers, cache hit-rate/effective cycles, and a dashboard link with
    the full cycle trace (PC/ACC/OUT/cache) plotted."""
    return core.run_cpu(program, max_cycles, cache_lines, line_bytes, miss_penalty)


@mcp.tool()
def assemble_program(program: str) -> dict:
    """Assemble CPU assembly to a memory image + label map (no simulation)."""
    from .digital.assembler import assemble
    try:
        image, meta = assemble(program)
    except Exception as e:
        return {"error": str(e)}
    return {"labels": meta["labels"], "image": image[:64], "note": "first 64 bytes shown"}


@mcp.tool()
def export_cpu_verilog(save: bool = True) -> dict:
    """Export synthesizable Verilog for the 8-bit CPU (Amaranth->yosys backend)."""
    from .digital import sim
    v = sim.export_verilog()
    path = None
    if save:
        path = str(config.DATA_DIR / "digital" / "cpu8.v")
        (config.DATA_DIR / "digital").mkdir(parents=True, exist_ok=True)
        Path(path).write_text(v, encoding="utf-8")
    return {"verilog_chars": len(v), "saved_to": path,
            "head": v[:1200]}


@mcp.tool()
def list_cells() -> dict:
    """List the gpdk090 transistor-level standard cells (INV/NAND2/NOR2/DFF/FA/SRAM6T)."""
    from .digital.cells import CELLS
    return {name: c["desc"] for name, c in CELLS.items()}


@mcp.tool()
def characterize_cell(cell: str) -> dict:
    """Simulate a standard cell at transistor level in Spectre (gpdk090) and return
    real metrics: INV -> tpHL/tpLH/power; FA -> truth table; SRAM6T/DFF -> waveforms.
    Saved to the dashboard for plotting."""
    from .digital import cells
    core.ensure_vm()
    cell = cell.upper()
    if cell == "INV":
        return cells.characterize_inverter()
    if cell == "FA":
        return cells.characterize_full_adder()
    if cell == "SRAM6T":
        return cells.characterize_sram()
    if cell == "DFF":
        return cells.characterize_dff()
    return {"error": f"no characterization for '{cell}' (try INV/FA/SRAM6T/DFF or run_ring_oscillator)"}


@mcp.tool()
def run_ring_oscillator(stages: int = 5) -> dict:
    """Transistor-level inverter ring oscillator in Spectre: returns oscillation
    frequency and per-stage delay (a real speed measure of the gpdk090 inverter)."""
    from .digital import cells
    core.ensure_vm()
    return cells.ring_oscillator(stages=stages)


@mcp.tool()
def get_cell_netlist(cell: str) -> dict:
    """Return the Spectre subckt definition for a standard cell."""
    from .digital.cells import CELL_SUBCKTS, CELLS
    cell = cell.upper()
    if cell not in CELLS:
        return {"error": f"unknown cell '{cell}'"}
    # extract the subckt block
    import re
    m = re.search(rf"subckt {cell} .*?ends {cell}", CELL_SUBCKTS, re.S)
    return {"cell": cell, "ports": CELLS[cell]["ports"], "desc": CELLS[cell]["desc"],
            "subckt": m.group(0) if m else None}


# --------------------------------------------------------------------------- #
#  Physical design (SKILL/Xvfb) + closed-loop auto-sizing
# --------------------------------------------------------------------------- #
@mcp.tool()
def run_skill(skill_code: str, timeout: int = 400) -> dict:
    """Run arbitrary SKILL headless in Virtuoso (via Xvfb) — create/edit libraries,
    schematics, layouts, drive Diva DRC/LVS/extract, netlist, etc. The universal
    escape hatch that makes the whole OpenAccess/Virtuoso side prompt-drivable.
    Print 'MCP:key=value' lines in your SKILL to get structured results back."""
    from . import physical
    core.ensure_vm()
    return physical.run_skill_raw(skill_code, timeout=timeout)


@mcp.tool()
def build_inverter_cell(wn: str = "1u", wp: str = "2u", l: str = "100n",
                        lib: str = "mcp_work", sch_cell: str = "inv_sch",
                        lay_cell: str = "inv_lay", do_drc: bool = True,
                        do_lvs: bool = True) -> dict:
    """END-TO-END CMOS inverter in ONE Virtuoso boot: authors a wired schematic AND
    a correctly-SIZED, routed layout (real gpdk090 pcells), then runs Diva DRC + LVS.

    This is the fast path — it bakes in every fact the manual physical-design flow
    had to discover (fw-not-w sizing, techfile self-bind, connectGates/tap for
    DRC-clean devices, the ivDRC/ivLVS signatures) so a full flow is one launch,
    not ~25. Returns effective device sizes, both net lists, techbind winner, and
    DRC/LVS report tails. Set do_drc/do_lvs=False to only author the cells."""
    from . import physical
    core.ensure_vm()
    return physical.build_inverter_cell(wn, wp, l, lib, sch_cell, lay_cell,
                                        do_drc=do_drc, do_lvs=do_lvs)


@mcp.tool()
def generate_layout(device: str = "nmos1v", w: str = "1u", l: str = "100n",
                    fingers: int = 1, cell: str = "dut", tap: str = "Integrated") -> dict:
    """Generate a correctly-sized gpdk090 transistor layout (pcell). Width uses the
    real `fw` knob (metres), tap='Integrated' adds DRC-clean well/substrate ties.
    Returns the effective device params read back from the DB (proof the size took)."""
    from . import physical
    core.ensure_vm()
    return physical.generate_device_layout(device, w, l, fingers, cell, tap=tap)


@mcp.tool()
def generate_inverter_layout(wn: str = "1u", wp: str = "2u", l: str = "100n",
                             cell: str = "inv_lay") -> dict:
    """Generate a ROUTED CMOS inverter layout (sized NMOS+PMOS pcells + Metal1
    IN/OUT/VDD/GND routing) in gpdk090. Pair with run_drc/run_lvs, or use
    build_inverter_cell for the full flow in one launch."""
    from . import physical
    core.ensure_vm()
    return physical.generate_inverter_layout(wn, wp, l, cell)


@mcp.tool()
def generate_schematic(device: str = "nmos1v", w: str = "1u", l: str = "100n",
                       cell: str = "dut_sch") -> dict:
    """Create a Virtuoso schematic cellview with a gpdk090 device + D/G/S/B pins."""
    from . import physical
    core.ensure_vm()
    return physical.generate_schematic(device, w, l, cell)


@mcp.tool()
def run_drc(cell: str, lib: str = "mcp_work") -> dict:
    """Run Diva DRC on a layout via the verified ivDRC keyword form. Returns the
    invocation status and report tails (violation count + markers)."""
    from . import physical
    core.ensure_vm()
    return physical.run_drc(cell, lib)


@mcp.tool()
def run_extract(cell: str, lib: str = "mcp_work") -> dict:
    """Run Diva layout extraction (produces the `extracted` view feeding LVS)."""
    from . import physical
    core.ensure_vm()
    return physical.run_extract(cell, lib=lib)


@mcp.tool()
def run_lvs(layout_cell: str, schematic_cell: str, lib: str = "mcp_work") -> dict:
    """Run Diva LVS (layout-vs-schematic) via ivLVS. Returns the invocation status
    and report files (netlist match verdict)."""
    from . import physical
    core.ensure_vm()
    return physical.run_lvs(layout_cell, schematic_cell, lib)


@mcp.tool()
def auto_size(experiment: str, spec: dict, knobs: list, iterations: int = 16,
              params: dict | None = None, enforce_saturation: bool = True) -> dict:
    """Closed-loop design: automatically tune `knobs` (experiment parameter names)
    until the circuit meets `spec`, using live Spectre measurements as feedback.

    spec example: {"dc_gain_db": {">=": 20}, "power_w": {"<=": 1e-3}}
    knobs example: ["w", "rd"]
    Returns whether the spec was met, the tuned parameter values, achieved metrics,
    and the search history. Keeps devices in saturation by default."""
    from . import sizing
    core.ensure_vm()
    return sizing.auto_size(experiment, spec, knobs, iterations, params,
                            enforce_saturation=enforce_saturation)


@mcp.tool()
def build_vtc_adc(vin_list: list | None = None, n_stages: int = 10,
                  make_schematics: bool = True) -> dict:
    """Build a low-power VTC-based ADC (Voltage-to-Time + Time-to-Digital converter):
    simulate the end-to-end Vin->code transfer on gpdk090, generate schematic diagrams
    (SVG), author real Virtuoso schematic cellviews (saved to a persistent OA library
    on the VM), and return the working-directory paths (host + guest)."""
    from .designs import vtc_adc
    core.ensure_vm()
    return vtc_adc.build(vin_list, n_stages, make_schematics)


@mcp.tool()
def read_lab_manual() -> dict:
    """Return the extracted text of the course lab manual (all 10 experiments)."""
    p = config.PROJECT_ROOT / "lab_manual.txt"
    if p.exists():
        return {"text": p.read_text(encoding="utf-8", errors="replace")}
    return {"error": "lab_manual.txt not found"}


def main():
    # Bring the dashboard up alongside the MCP server so the link always works.
    try:
        dashboard.start(background=True)
    except Exception:
        pass
    mcp.run()


if __name__ == "__main__":
    main()
