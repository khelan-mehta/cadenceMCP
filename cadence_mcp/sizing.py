"""Closed-loop auto-sizing: iterate an experiment's parameters until it meets a
spec, using live Spectre measurements as feedback. Coordinate-descent hill-climb
in log space — gradient-free, robust, and bounded in the number of simulations.

Spec format:  {"dc_gain_db": {">=": 20}, "power_w": {"<=": 1e-3}}
Knobs:        ["w", "rd"]  (experiment parameter names to tune)
"""
from __future__ import annotations

import math

from . import core, experiments

# map friendly target names -> measurement keys produced by experiments
_ALIASES = {
    "gain_db": ["dc_gain_db", "gain_db"],
    "dc_gain_db": ["dc_gain_db", "gain_db"],
    "bandwidth_hz": ["bandwidth_hz"],
    "gbw_hz": ["gbw_hz", "unity_gain_hz"],
    "phase_margin_deg": ["phase_margin_deg"],
    "slew_rate_v_per_us": ["slew_rate_v_per_us"],
    "power_w": ["power_w"],
}


def _get_metric(meas: dict, name: str):
    for k in _ALIASES.get(name, [name]):
        v = meas.get(k)
        if isinstance(v, (int, float)):
            return v
    return None


def _op_penalty(meas: dict) -> tuple[float, int]:
    """Penalize transistors that are not in saturation (a broken bias point makes
    gain meaningless). Returns (penalty, n_out_of_sat)."""
    devs = meas.get("devices") or []
    bad = 0
    for d in devs:
        region = str(d.get("region", "")).lower()
        if region and region not in ("sat", "saturation"):
            bad += 1
    return (0.5 * bad, bad)


def _cost(meas: dict, spec: dict, enforce_sat: bool = True) -> tuple[float, dict]:
    """Sum of normalized spec violations (0 = all met)."""
    total = 0.0
    detail = {}
    if enforce_sat:
        pen, bad = _op_penalty(meas)
        total += pen
        if bad:
            detail["_operating_point"] = {"devices_out_of_saturation": bad, "met": False}
    for metric, cond in spec.items():
        val = _get_metric(meas, metric)
        if val is None:
            total += 1.0
            detail[metric] = {"value": None, "met": False}
            continue
        met = True
        pen = 0.0
        for op, target in cond.items():
            if target == 0:
                target = 1e-12
            if op == ">=":
                if val < target:
                    pen += (target - val) / abs(target); met = False
            elif op == "<=":
                if val > target:
                    pen += (val - target) / abs(target); met = False
            elif op == "==":
                pen += abs(val - target) / abs(target)
                met = abs(val - target) / abs(target) < 0.05
        total += pen
        detail[metric] = {"value": val, "met": met}
    return total, detail


def _num(v):
    return experiments._num(v)


def _fmt(v: float) -> str:
    """Format a float back to engineering notation for a netlist param."""
    a = abs(v)
    for suf, mul in (("G", 1e9), ("M", 1e6), ("k", 1e3), ("", 1), ("m", 1e-3),
                     ("u", 1e-6), ("n", 1e-9), ("p", 1e-12), ("f", 1e-15)):
        if a >= mul or suf == "f":
            return f"{v/mul:.4g}{suf}"
    return f"{v:.4g}"


def auto_size(experiment: str, spec: dict, knobs: list[str],
              iterations: int = 16, params: dict | None = None,
              span: float = 4.0, enforce_saturation: bool = True) -> dict:
    """Tune `knobs` of `experiment` to satisfy `spec`. Returns the best params,
    achieved metrics, whether the spec is met, and the search history."""
    exp = experiments.get(experiment)
    if exp is None:
        return {"error": f"unknown experiment '{experiment}'"}
    defaults = exp.default_params()
    cur = dict(defaults)
    if params:
        cur.update({k: str(v) for k, v in params.items()})

    # numeric working values + bounds for each knob
    work = {}
    bounds = {}
    for k in knobs:
        base = _num(cur.get(k, defaults.get(k, "1")))
        if not base or math.isnan(base):
            base = 1.0
        work[k] = base
        bounds[k] = (base / span, base * span)

    def evaluate(wvals):
        p = dict(cur)
        for k, v in wvals.items():
            p[k] = _fmt(v)
        r = core.run_experiment(experiment, p)
        if not r.get("ok"):
            return None, 1e9, {}, p
        meas = r["measurements"]
        c, detail = _cost(meas, spec, enforce_sat=enforce_saturation)
        return meas, c, detail, p

    meas, best_cost, detail, best_p = evaluate(work)
    history = [{"iter": 0, "cost": best_cost, "knobs": dict(work), "detail": detail}]
    step = 2.0  # multiplicative step, shrinks over time

    it = 0
    while it < iterations and best_cost > 1e-6:
        improved = False
        for k in knobs:
            for factor in (step, 1 / step):
                trial = dict(work)
                nv = trial[k] * factor
                lo, hi = bounds[k]
                nv = max(lo, min(hi, nv))
                if nv == work[k]:
                    continue
                trial[k] = nv
                m2, c2, d2, p2 = evaluate(trial)
                it += 1
                history.append({"iter": it, "cost": c2, "knobs": dict(trial),
                                "changed": k, "factor": round(factor, 3)})
                if c2 < best_cost - 1e-9:
                    best_cost, work, meas, detail, best_p = c2, trial, m2, d2, p2
                    improved = True
                    break
                if it >= iterations:
                    break
            if it >= iterations or best_cost <= 1e-6:
                break
        if not improved:
            step = 1 + (step - 1) * 0.5   # refine
            if step < 1.05:
                break

    met = best_cost <= 1e-6
    final_params = {k: _fmt(v) for k, v in work.items()}
    return {
        "ok": True, "experiment": experiment, "spec": spec,
        "met": met, "cost": best_cost,
        "tuned_params": final_params,
        "all_params": {k: (best_p.get(k)) for k in best_p if not k.startswith("_")},
        "achieved": {m: detail[m]["value"] for m in detail if "value" in detail[m]},
        "spec_detail": detail,
        "iterations_run": it,
        "history": history[-30:],
    }
