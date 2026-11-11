"""Parser for Spectre `info what=oppoint` operating-point files (op.info).

Block format (validated live)::

    Instance: M0 of gpdk090_nmos1v
    Model: M0.gpdk090_nmos1v_x
    Primitive: bsim3v3
              d : V(o) = 1.24828 V
           type = n
         region = sat
             gm = 2.06476 mS
            gds = 342.949 uS
            ...
    Total Power Dissipation = 1.51387 mW.

We return { instance_name: { "model":.., "params": {name: {"raw":str, "si":float}} } }.
"""
from __future__ import annotations

import re

_PREFIX = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
           "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")

_INST = re.compile(r"^Instance:\s+(\S+)(?:\s+of\s+(\S+))?\s*$")
_PARAM = re.compile(r"^\s*([A-Za-z][\w/]*)\s*=\s*(.+?)\s*$")
_TOTAL = re.compile(r"^Total Power Dissipation\s*=\s*(.+)$")


def _to_si(value_tok: str, unit_tok: str):
    if not _NUM.match(value_tok):
        return None
    v = float(value_tok)
    if not unit_tok:
        return v
    u = unit_tok
    # unit may carry an SI prefix: mV, uA, kOhm, GHz, fF, aCoul, mA/V^2 ...
    if len(u) > 1 and u[0] in _PREFIX:
        base = u[1:]
        # guard: don't treat 'A','V','S','F','W','C'... bare as prefixed
        return v * _PREFIX[u[0]]
    return v


def parse_opinfo(text: str) -> dict:
    result: dict[str, dict] = {}
    total_power = None
    cur = None
    for line in text.splitlines():
        m = _INST.match(line.strip()) if line.startswith("Instance:") else None
        if m:
            name = m.group(1)
            cur = {"model": m.group(2), "params": {}}
            result[name] = cur
            continue
        mt = _TOTAL.match(line.strip())
        if mt:
            parts = mt.group(1).replace(".", " ").split()
            # e.g. "1.51387 mW."
            toks = mt.group(1).rstrip(".").split()
            if toks:
                total_power = _to_si(toks[0], toks[1] if len(toks) > 1 else "")
            continue
        if cur is None:
            continue
        if line.startswith("Model:"):
            cur["model_card"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Primitive:"):
            cur["primitive"] = line.split(":", 1)[1].strip()
            continue
        # skip terminal lines like "   d : V(o) = 1.24828 V"
        if re.match(r"^\s*\w+\s*:\s", line):
            continue
        pm = _PARAM.match(line)
        if pm:
            key = pm.group(1)
            rest = pm.group(2)
            toks = rest.split()
            raw = rest
            si = None
            if toks:
                si = _to_si(toks[0], toks[1] if len(toks) > 1 else "")
            cur["params"][key] = {"raw": raw, "si": si}
    return {"instances": result, "total_power_w": total_power}


def device_table(opinfo: dict, want=("region", "id", "ids", "gm", "gds", "ron",
                                      "vth", "vdsat", "vgs", "vds", "cgs", "cgd",
                                      "pwr", "gmoverid", "fug", "vearly", "self_gain")) -> list[dict]:
    """Flatten MOS instances into a compact table for display."""
    rows = []
    for name, d in opinfo.get("instances", {}).items():
        p = d.get("params", {})
        if "gm" not in p and "region" not in p:
            continue  # not a transistor
        row = {"instance": name, "model": d.get("model")}
        # ro = 1/gds
        gds = p.get("gds", {}).get("si")
        if gds:
            row["ro"] = 1.0 / gds
        for k in want:
            if k in p:
                si = p[k].get("si")
                row[k] = si if si is not None else p[k].get("raw")
        rows.append(row)
    return rows
