"""High-level orchestration: build a deck, simulate on the VM, measure, store.

These functions are shared by the MCP server tools and the dashboard.
"""
from __future__ import annotations

import math

from . import config, experiments, spectre, store, vm


def _clean(m: dict) -> dict:
    """Strip large arrays for the compact tool reply (keep scalars + device table)."""
    out = {}
    for k, v in m.items():
        if isinstance(v, list) and len(v) > 12:
            out[k] = f"<{len(v)} pts>"
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = None
        else:
            out[k] = v
    return out


def ensure_vm() -> dict:
    st = vm.status()
    if not st["guest_ready"]:
        vm.start(wait=True)
        st = vm.status()
    return st


def run_experiment(exp_id: str, params: dict | None = None, timeout: int = 420) -> dict:
    exp = experiments.get(exp_id)
    if exp is None:
        return {"error": f"unknown experiment '{exp_id}'"}
    p = dict(exp.default_params())
    if params:
        p.update({k: str(v) for k, v in params.items()})
    p["_title"] = f"Exp {exp.id} {exp.title}"

    ensure_vm()
    netlist = exp.build(p)
    res = spectre.run_netlist(netlist, run_name=f"exp{exp.id}", timeout=timeout)

    if not res.ok:
        return {
            "ok": False, "experiment_id": exp.id,
            "errors": res.errors, "warnings": res.warnings,
            "log_tail": spectre.trimmed_log(res.log),
            "netlist": netlist,
        }

    meas = exp.measure(res)
    plots = exp.plots
    run_id = store.save_run(exp.id, exp.title, p, res, meas, netlist, plots)

    return {
        "ok": True, "run_id": run_id, "experiment_id": exp.id, "title": exp.title,
        "spec": exp.spec, "warnings": res.warnings,
        "measurements": _clean(meas),
        "device_table": meas.get("devices", []),
        "analyses": {n: {"kind": res.kinds.get(n), "signals": a.get("names", [])}
                     for n, a in res.analyses.items() if "data" in a},
        "plots_available": [pl["title"] for pl in plots],
        "dashboard": f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/?run={run_id}",
    }


def run_parametric(exp_id: str, sweep_param: str, values: list, params: dict | None = None,
                   timeout: int = 600) -> dict:
    """Run an experiment repeatedly, overriding one parameter, and collect key metrics."""
    exp = experiments.get(exp_id)
    if exp is None:
        return {"error": f"unknown experiment '{exp_id}'"}
    ensure_vm()
    rows = []
    run_ids = []
    for val in values:
        p = dict(params or {})
        p[sweep_param] = val
        r = run_experiment(exp_id, p, timeout=timeout)
        if r.get("ok"):
            run_ids.append(r["run_id"])
            m = r["measurements"]
            rows.append({sweep_param: val,
                         "gain_db": m.get("dc_gain_db") or m.get("gain_db"),
                         "bandwidth_hz": m.get("bandwidth_hz"),
                         "gbw_hz": m.get("gbw_hz"),
                         "power_w": m.get("power_w"),
                         "run_id": r["run_id"]})
        else:
            rows.append({sweep_param: val, "error": True})
    return {"ok": True, "experiment_id": exp_id, "sweep_param": sweep_param,
            "rows": rows, "run_ids": run_ids}


def run_montecarlo(exp_id: str, runs: int = 10, params: dict | None = None) -> dict:
    """Corner-based statistical spread (NN/SS/SF/FF/FS) as a Monte-Carlo proxy."""
    from . import config
    corners = config.PDK_CORNERS
    rows = []
    for i in range(runs):
        corner = corners[i % len(corners)]
        p = dict(params or {}); p["corner"] = corner
        r = run_experiment(exp_id, p)
        if r.get("ok"):
            m = r["measurements"]
            rows.append({"iter": i, "corner": corner,
                         "gain_db": m.get("dc_gain_db") or m.get("gain_db"),
                         "gbw_hz": m.get("gbw_hz"), "power_w": m.get("power_w")})
    gains = [x["gain_db"] for x in rows if x.get("gain_db") is not None]
    stats = {}
    if gains:
        mean = sum(gains) / len(gains)
        var = sum((g - mean) ** 2 for g in gains) / len(gains)
        stats = {"gain_mean_db": mean, "gain_std_db": var ** 0.5,
                 "gain_min_db": min(gains), "gain_max_db": max(gains)}
    return {"ok": True, "experiment_id": exp_id, "rows": rows, "stats": stats}


def run_cpu(program: str, max_cycles: int = 3000, cache_lines: int = 8,
            line_bytes: int = 4, miss_penalty: int = 8) -> dict:
    """Assemble + simulate an 8-bit CPU program (functional). Persists the cycle
    trace so the dashboard can plot PC/ACC/OUT/cache vs cycle."""
    from .digital import sim
    from . import store
    if program in sim.DEMOS:
        program = sim.DEMOS[program]
    r = sim.run_program(program, max_cycles=max_cycles, cache_lines=cache_lines,
                        line_bytes=line_bytes, miss_penalty=miss_penalty,
                        vcd_name="cpu")
    tr = r["trace"]
    analyses = {"trace": {"kind": "digital", "sweep": "cycle",
                          "names": list(tr.keys()), "data": tr}}
    plots = [
        {"title": "CPU registers vs cycle", "analysis": "trace", "x": "cycle",
         "y": ["pc", "acc", "out"], "xlabel": "cycle", "ylabel": "value"},
        {"title": "Cache hits / misses", "analysis": "trace", "x": "cycle",
         "y": ["cache_hits", "cache_misses"], "xlabel": "cycle", "ylabel": "count"},
    ]
    meas = {k: v for k, v in r["final"].items() if k != "memory"}
    meas["labels"] = r["labels"]
    run_id = store.save_generic("cpu", "8-bit CPU program", {"cache": r["cache_cfg"]},
                                meas, analyses, plots)
    return {"ok": True, "run_id": run_id, "halted": r["halted"],
            "cycles_run": r["cycles_run"], "final": {k: v for k, v in r["final"].items()
                                                     if k != "memory"},
            "cache_cfg": r["cache_cfg"], "vcd": r["vcd"],
            "dashboard": f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/?run={run_id}"}


def compute_cmrr(diff_run_id: str, cm_run_id: str) -> dict:
    dd = store.load_run(diff_run_id); cc = store.load_run(cm_run_id)
    if not dd or not cc:
        return {"error": "run id not found"}
    adm = dd["measurements"].get("gain_db")
    acm = cc["measurements"].get("gain_db")
    if adm is None or acm is None:
        return {"error": "gain_db missing in one of the runs"}
    return {"adm_db": adm, "acm_db": acm, "cmrr_db": adm - acm}
