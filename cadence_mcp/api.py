"""General, composable primitives that subsume the bespoke tools.

  simulate(netlist, measures)      -> run any deck, parse waveforms + measures, save plottable run
  measure_run(run_id, measures)    -> apply the measure library to any stored run
  optimize(template, knobs, spec)  -> tune any {param} netlist to a spec via live feedback

Templates (the 10 experiments, cells, VTC-ADC) are just data fed to these.
"""
from __future__ import annotations

import math
import re

from . import config, metrics, spectre, store, vm


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def _fmt(v) -> str:
    """Engineering-notation formatting for a netlist parameter value."""
    if isinstance(v, str):
        return v
    a = abs(v)
    for suf, mul in (("G", 1e9), ("M", 1e6), ("k", 1e3), ("", 1), ("m", 1e-3),
                     ("u", 1e-6), ("n", 1e-9), ("p", 1e-12), ("f", 1e-15)):
        if a >= mul or suf == "f":
            return f"{v/mul:.5g}{suf}"
    return f"{v:.5g}"


def _num(v):
    from .experiments import _num as n
    return n(v)


def substitute(template: str, values: dict) -> str:
    """Replace {name} placeholders in a netlist template with formatted values."""
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", _fmt(v))
    return out


def _auto_plots(res) -> list:
    """One default plot per analysis: signals vs sweep (log-x + dB for ac)."""
    plots = []
    for name, a in res.analyses.items():
        if "data" not in a:
            continue
        sweep = a.get("sweep")
        sigs = [s for s in a.get("names", []) if s != sweep][:6]
        if not sigs:
            continue
        is_ac = a.get("cdata") is not None or res.kinds.get(name) == "ac"
        plots.append({
            "title": f"{name} ({res.kinds.get(name,'')})",
            "analysis": name, "x": "@sweep" if not is_ac else sweep,
            "y": sigs, "xlabel": sweep, "ylabel": "value",
            "xscale": "log" if is_ac else "linear",
            "ytransform": "db" if is_ac else "none",
        })
    return plots


# --------------------------------------------------------------------------- #
#  simulate
# --------------------------------------------------------------------------- #
def simulate(netlist: str, measures: list | None = None, run_name: str = "sim",
             title: str | None = None, save: bool = True, params: dict | None = None,
             timeout: int = 420) -> dict:
    """Run any Spectre deck; return parsed signals + requested measures; save a
    plottable run. `params` optionally substitutes {name} placeholders first."""
    if params:
        netlist = substitute(netlist, params)
    res = spectre.run_netlist(netlist, run_name=run_name, timeout=timeout)
    if not res.ok:
        return {"ok": False, "errors": res.errors, "warnings": res.warnings,
                "log_tail": spectre.trimmed_log(res.log), "netlist": netlist}

    meas = metrics.apply_measures(res, measures or [])
    plots = _auto_plots(res)
    run_id = None
    if save:
        run_id = store.save_run(run_name, title or run_name, params or {}, res,
                                {**meas, "devices": _device_table(res)}, netlist, plots)
    return {
        "ok": True, "run_id": run_id,
        "measurements": meas,
        "analyses": {n: {"kind": res.kinds.get(n), "signals": a.get("names", []),
                         "points": len(a.get("data", {}).get(a.get("sweep"), []))}
                     for n, a in res.analyses.items() if "data" in a},
        "devices": _device_table(res),
        "warnings": res.warnings,
        "dashboard": (f"http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/?run={run_id}"
                      if run_id else None),
    }


def _device_table(res):
    from .opparse import device_table
    try:
        return device_table(res.opinfo)
    except Exception:
        return []


# --------------------------------------------------------------------------- #
#  measure (on a stored run or provided analyses)
# --------------------------------------------------------------------------- #
def measure_run(run_id: str | None = None, measures: list | None = None,
                source: dict | None = None) -> dict:
    if source is None:
        if run_id is None:
            return {"error": "provide run_id or source"}
        source = store.load_run(run_id)
        if source is None:
            return {"error": f"run '{run_id}' not found"}
    return {"ok": True, "run_id": run_id,
            "measurements": metrics.apply_measures(source, measures or [])}


# --------------------------------------------------------------------------- #
#  optimize (general auto-size on any {param} netlist)
# --------------------------------------------------------------------------- #
def _cost(meas: dict, spec: dict) -> tuple[float, dict]:
    total, detail = 0.0, {}
    for name, cond in spec.items():
        val = meas.get(name)
        if isinstance(val, dict):        # a measure error
            val = None
        if val is None:
            total += 1.0
            detail[name] = {"value": None, "met": False}
            continue
        met, pen = True, 0.0
        for op, tgt in cond.items():
            tgt = tgt if tgt != 0 else 1e-12
            if op == ">=" and val < tgt:
                pen += (tgt - val) / abs(tgt); met = False
            elif op == "<=" and val > tgt:
                pen += (val - tgt) / abs(tgt); met = False
            elif op == "==":
                pen += abs(val - tgt) / abs(tgt); met = abs(val - tgt) / abs(tgt) < 0.05
        total += pen
        detail[name] = {"value": val, "met": met}
    return total, detail


def optimize(netlist_template: str, knobs: dict, spec: dict, measures: list,
             params: dict | None = None, iterations: int = 16, span: float = 4.0,
             timeout: int = 420) -> dict:
    """Tune the {param} knobs of `netlist_template` until `spec` (keyed by measure
    names) is met. `knobs`: {name: {"init":v, "min":a, "max":b}} or {name: init}.
    `params`: the template's other (fixed) placeholders — filled every iteration.

    spec example: {"gain_db": {">=": 20}, "power": {"<=": 1e-3}}
    """
    base_params = dict(params or {})
    work, bounds = {}, {}
    for k, cfg in knobs.items():
        if isinstance(cfg, dict):
            base = _num(cfg.get("init", 1))
            lo = _num(cfg["min"]) if "min" in cfg else base / span
            hi = _num(cfg["max"]) if "max" in cfg else base * span
        else:
            base = _num(cfg); lo, hi = base / span, base * span
        if not base or (isinstance(base, float) and math.isnan(base)):
            base = 1.0
        work[k] = base; bounds[k] = (lo, hi)

    def evaluate(wv):
        vals = {**base_params, **{k: _fmt(v) for k, v in wv.items()}}
        r = simulate(netlist_template, measures, run_name="opt", save=False,
                     params=vals, timeout=timeout)
        if not r.get("ok"):
            return None, 1e9, {}
        c, d = _cost(r["measurements"], spec)
        return r["measurements"], c, d

    meas, best, detail = evaluate(work)
    history = [{"iter": 0, "cost": best, "knobs": dict(work)}]
    step, it = 2.0, 0
    while it < iterations and best > 1e-6:
        improved = False
        for k in list(work):
            for factor in (step, 1 / step):
                trial = dict(work)
                nv = max(bounds[k][0], min(bounds[k][1], trial[k] * factor))
                if nv == work[k]:
                    continue
                trial[k] = nv
                m2, c2, d2 = evaluate(trial); it += 1
                history.append({"iter": it, "cost": round(c2, 4), "changed": k})
                if c2 < best - 1e-9:
                    best, work, meas, detail = c2, trial, m2, d2
                    improved = True
                    break
                if it >= iterations:
                    break
            if it >= iterations or best <= 1e-6:
                break
        if not improved:
            step = 1 + (step - 1) * 0.5
            if step < 1.05:
                break

    return {"ok": True, "met": best <= 1e-6, "cost": best,
            "tuned_params": {k: _fmt(v) for k, v in work.items()},
            "achieved": {n: detail[n]["value"] for n in detail},
            "spec_detail": detail, "iterations_run": it, "history": history[-25:]}
