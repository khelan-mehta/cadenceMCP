"""Persist simulation runs so the dashboard and later tools can read them."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from . import config


def _run_path(run_id: str) -> Path:
    return config.RUNS_DIR / f"{run_id}.json"


def save_run(experiment_id: str, title: str, params: dict, spectre_res,
             measurements: dict, netlist: str, plots: list) -> str:
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    # serialize analyses into compact numeric arrays
    analyses = {}
    for name, a in spectre_res.analyses.items():
        if "data" not in a:
            continue
        analyses[name] = {
            "kind": spectre_res.kinds.get(name, ""),
            "sweep": a.get("sweep"),
            "names": a.get("names"),
            "units": a.get("units"),
            "data": a.get("data"),
            "cdata": a.get("cdata"),          # complex (ac) data, for phase measures
            "has_complex": a.get("cdata") is not None,
        }
    doc = {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "title": title,
        "created": time.time(),
        "created_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": params,
        "ok": spectre_res.ok,
        "errors": spectre_res.errors,
        "warnings": spectre_res.warnings,
        "measurements": _jsonable(measurements),
        "opinfo": spectre_res.opinfo,
        "analyses": analyses,
        "plots": plots,
        "netlist": netlist,
    }
    _run_path(run_id).write_text(json.dumps(doc), encoding="utf-8")
    return run_id


def save_generic(experiment_id: str, title: str, params: dict, measurements: dict,
                 analyses: dict, plots: list, extra: dict | None = None) -> str:
    """Persist a non-Spectre run (e.g. the CPU trace) in the same schema so the
    dashboard can plot it. `analyses` maps name -> {kind, sweep, names, data}."""
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    doc = {
        "run_id": run_id, "experiment_id": experiment_id, "title": title,
        "created": time.time(), "created_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": params, "ok": True, "errors": 0, "warnings": 0,
        "measurements": _jsonable(measurements), "opinfo": {},
        "analyses": analyses, "plots": plots, "netlist": "",
    }
    if extra:
        doc.update(extra)
    _run_path(run_id).write_text(json.dumps(doc), encoding="utf-8")
    return run_id


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
        return obj
    return obj


def load_run(run_id: str) -> dict | None:
    p = _run_path(run_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_runs(experiment_id: str | None = None, limit: int = 200) -> list[dict]:
    runs = []
    for f in sorted(config.RUNS_DIR.glob("*.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if experiment_id and str(d.get("experiment_id")) != str(experiment_id):
            continue
        runs.append({
            "run_id": d["run_id"], "experiment_id": d.get("experiment_id"),
            "title": d.get("title"), "created_str": d.get("created_str"),
            "ok": d.get("ok"), "errors": d.get("errors"),
            "measurements": _summary_meas(d.get("measurements", {})),
        })
        if len(runs) >= limit:
            break
    return runs


def _summary_meas(m: dict) -> dict:
    """A few scalar highlights for list views."""
    keys = ("vt0", "kn", "lambda", "dc_gain_db", "gain_db", "bandwidth_hz",
            "gbw_hz", "phase_margin_deg", "slew_rate_v_per_us", "power_w",
            "cmrr_db", "switching_threshold_vm_v")
    return {k: m[k] for k in keys if k in m and not isinstance(m[k], (list, dict))}


def delete_run(run_id: str) -> bool:
    p = _run_path(run_id)
    if p.exists():
        p.unlink()
        return True
    return False
