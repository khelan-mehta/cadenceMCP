"""General measurement DSL — apply the measure.py library to *any* simulation run.

A measure is a small dict:
    {"name": "gain", "metric": "gain_db", "analysis": "ac", "signal": "out"}
    {"name": "vt0",  "metric": "vt0", "analysis": "dc", "signal": "Vd:p", "transform": "abs"}
    {"name": "pm",   "metric": "phase_margin_deg", "analysis": "ac", "signal": "out"}
    {"name": "td",   "metric": "delay", "analysis": "tran", "from": "in", "to": "out", "level": 0.5}
    {"name": "pwr",  "metric": "power"}                       # from op-point
    {"name": "vo",   "metric": "value_at", "analysis": "dc", "signal": "out", "x": 0.9}
    {"name": "gm_M0","metric": "device", "instance": "M0", "param": "gm"}

`apply_measures` returns {name: scalar_or_dict}. Every metric is wrapped so one
bad spec never breaks the batch. Works on a fresh SpectreResult or a stored run.
"""
from __future__ import annotations

import math

from . import measure


# --------------------------------------------------------------------------- #
#  input normalization
# --------------------------------------------------------------------------- #
def _norm(source):
    """Return (analyses, opinfo). Accepts a SpectreResult or a stored-run dict."""
    if hasattr(source, "analyses"):          # SpectreResult
        return source.analyses, getattr(source, "opinfo", {}) or {}
    if isinstance(source, dict):             # stored run doc
        return source.get("analyses", {}), source.get("opinfo", {}) or {}
    raise TypeError("measure source must be a SpectreResult or run dict")


def _pick_analysis(analyses: dict, m: dict):
    name = m.get("analysis")
    if name and name in analyses:
        return name, analyses[name]
    if name:  # requested but missing
        return None, None
    if len(analyses) == 1:
        n = next(iter(analyses))
        return n, analyses[n]
    # fall back to a kind hint
    kind = m.get("kind")
    for n, a in analyses.items():
        if kind and (a.get("kind") == kind):
            return n, a
    return (next(iter(analyses)), next(iter(analyses.values()))) if analyses else (None, None)


def _xy(a: dict, m: dict, sig_key="signal"):
    """Return (x, y) arrays with optional transform applied to y."""
    data = a.get("data", {})
    sweep = a.get("sweep")
    xname = m.get("x", "@sweep")
    x = data.get(sweep) if xname == "@sweep" else data.get(xname)
    yname = m.get(sig_key)
    y = data.get(yname) if yname else None
    tr = m.get("transform")
    if y is not None and tr:
        if tr == "abs":
            y = [abs(v) for v in y]
        elif tr == "sqrtabs":
            y = [math.sqrt(abs(v)) for v in y]
        elif tr == "db":
            y = measure.db20([abs(v) for v in y])
    return x, y


def _phase(a: dict, sig: str):
    cd = (a.get("cdata") or {}).get(sig)
    if not cd:
        return None
    return [math.degrees(math.atan2(im, re)) for (re, im) in cd]


# --------------------------------------------------------------------------- #
#  metric implementations  (each: (analyses, opinfo, m) -> value)
# --------------------------------------------------------------------------- #
def _m_gain_db(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    return measure.ac_gain_bw(f, mag).get("dc_gain_db")


def _m_gain_vv(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    return measure.ac_gain_bw(f, mag).get("dc_gain_vv")


def _m_bandwidth(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    return measure.ac_gain_bw(f, mag).get("bandwidth_hz")


def _m_gbw(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    g = measure.ac_gain_bw(f, mag)
    return g.get("gbw_hz") or g.get("unity_gain_hz")


def _m_ugf(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    return measure.ac_gain_bw(f, mag).get("unity_gain_hz")


def _m_phase_margin(A, op, m):
    _, a = _pick_analysis(A, m); f, mag = _xy(a, m)
    ph = _phase(a, m.get("signal"))
    if ph is None:
        return None
    return measure.phase_margin(f, mag, ph).get("phase_margin_deg")


def _m_vt0(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    y = [abs(v) for v in y]
    return measure.extract_vt0(x, y).get("vt0")


def _m_kn(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    y = [abs(v) for v in y]
    vt = measure.extract_vt0(x, y).get("vt0")
    return measure.extract_kn(x, y, vt).get("kn") if vt is not None else None


def _m_lambda(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    y = [abs(v) for v in y]
    return measure.extract_lambda(x, y).get("lambda")


def _m_slew(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    return measure.slew_rate(x, y).get("slew_rate_v_per_us")


def _m_thd(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    return measure.thd(x, y, float(m.get("f0", 1e3))).get("thd_percent")


def _m_delay(A, op, m):
    _, a = _pick_analysis(A, m)
    data = a.get("data", {}); t = data.get(a.get("sweep"))
    lvl = float(m.get("level", 0.5)) * _amp(data.get(m.get("to")), m)
    t_from = measure.cross(t, data.get(m.get("from")), lvl, m.get("edge_from", "either"))
    t_to = measure.cross(t, data.get(m.get("to")), lvl, m.get("edge_to", "either"))
    return (t_to - t_from) if (t_from is not None and t_to is not None) else None


def _amp(sig, m):
    if "abs_level" in m:
        return 1.0
    return (max(sig) if sig else 1.0)


def _m_value_at(A, op, m):
    _, a = _pick_analysis(A, m)
    m2 = dict(m); m2["x"] = "@sweep"          # axis = sweep; eval point is "at"
    x, y = _xy(a, m2)
    if not x or not y:
        return None
    return measure.interp(x, y, float(m.get("at", m.get("x_value"))))


def _m_cross(A, op, m):
    _, a = _pick_analysis(A, m); x, y = _xy(a, m)
    return measure.cross(x, y, float(m.get("level", 0.0)), m.get("edge", "either"))


def _reduce(fn):
    def inner(A, op, m):
        _, a = _pick_analysis(A, m); x, y = _xy(a, m)
        return fn(y) if y else None
    return inner


def _rms(y):
    return math.sqrt(sum(v * v for v in y) / len(y)) if y else None


def _m_power(A, op, m):
    return (op or {}).get("total_power_w")


def _m_device(A, op, m):
    inst = (op or {}).get("instances", {}).get(m.get("instance"))
    if not inst:
        return None
    p = inst.get("params", {}).get(m.get("param"))
    if not p:
        return None
    si = p.get("si")
    return si if si is not None else p.get("raw")


METRICS = {
    "gain_db": _m_gain_db, "gain_vv": _m_gain_vv, "bandwidth_hz": _m_bandwidth,
    "gbw_hz": _m_gbw, "unity_gain_hz": _m_ugf, "phase_margin_deg": _m_phase_margin,
    "vt0": _m_vt0, "kn": _m_kn, "lambda": _m_lambda,
    "slew_rate": _m_slew, "thd": _m_thd, "delay": _m_delay,
    "value_at": _m_value_at, "cross": _m_cross,
    "min": _reduce(min), "max": _reduce(max),
    "pp": _reduce(lambda y: max(y) - min(y)), "rms": _reduce(_rms),
    "mean": _reduce(lambda y: sum(y) / len(y)),
    "power": _m_power, "device": _m_device,
}


def apply_measures(source, measures: list) -> dict:
    A, op = _norm(source)
    out = {}
    for i, m in enumerate(measures or []):
        name = m.get("name") or m.get("metric") or f"m{i}"
        metric = m.get("metric")
        fn = METRICS.get(metric)
        if fn is None:
            out[name] = {"error": f"unknown metric '{metric}'"}
            continue
        try:
            out[name] = fn(A, op, m)
        except Exception as e:
            out[name] = {"error": str(e)}
    return out


def available_metrics() -> list:
    return sorted(METRICS.keys())
