"""RC low-pass surrogate + schematic-equivalence design/verify loop.

Two ground truths, one loop:

  * SPICE ground truth (raw headless Spectre) generates a dataset and trains an
    invertible surrogate that maps design knobs (R, C) -> outputs (f0, gain_dc).
  * SCHEMATIC ground truth: each design iteration authors a *real* Virtuoso OA
    schematic (analogLib res + cap + gnd + IN/OUT pins) with the surrogate's
    proposed values, reads the connectivity back out of the OpenAccess database,
    reconstructs a Spectre deck *from the drawn schematic*, re-simulates it, and
    checks the measured outputs against the required spec. If the schematic does
    not reproduce the target, the measured point is folded back into the dataset,
    the surrogate is retrained, and it re-proposes -- until the *schematic itself*
    meets the required outputs (PLAN.md's schematic-equivalence gate).

Only `createNetlist` exists headless on this appliance (no schGenerateNetlist /
si_* / hnl*), and a full ADE netlister session is heavy, so we netlist the
schematic by walking its OA connectivity -- i.e. we simulate exactly what
Virtuoso wired, which is the faithful equivalence check.
"""
from __future__ import annotations

import math
import re

import numpy as np

from . import api, core, physical


# =========================================================================== #
#  SPICE ground truth (raw Spectre, ideal passives -- no PDK models needed)
# =========================================================================== #
AC_LINE = "acs ac start=0.1 stop=1e10 dec=20"

MEASURES = [
    {"name": "f0",      "metric": "bandwidth_hz", "analysis": "acs", "signal": "out"},
    {"name": "gain_dc", "metric": "gain_db",      "analysis": "acs", "signal": "out"},
]


def rc_deck(R: float, C: float) -> str:
    """Ideal series-R / shunt-C low-pass, unity-mag AC drive on `in`, sense `out`."""
    return ("simulator lang=spectre\nglobal 0\n"
            "Vin (in 0) vsource dc=0 mag=1 type=dc\n"
            f"R0 (in out) resistor r={R:.6g}\n"
            f"C0 (out 0) capacitor c={C:.6g}\n"
            f"{AC_LINE}\n")


def spice_eval(R: float, C: float, run_name: str = "rc") -> dict:
    """One raw-Spectre evaluation -> {ok, f0, gain_dc}. This is ground truth."""
    r = api.simulate(rc_deck(R, C), MEASURES, run_name=run_name, save=False)
    if not r.get("ok"):
        return {"ok": False, "R": R, "C": C, "err": r.get("errors")}
    m = r["measurements"]
    f0, g = m.get("f0"), m.get("gain_dc")
    if isinstance(f0, dict):
        f0 = None
    if isinstance(g, dict):
        g = None
    return {"ok": f0 is not None and g is not None, "R": R, "C": C,
            "f0": f0, "gain_dc": g}


# =========================================================================== #
#  DOE sampling (Latin-hypercube in log space, deterministic under seed)
# =========================================================================== #
def sample_lhs(n: int, seed: int, r_lo: float, r_hi: float,
               c_lo: float, c_hi: float) -> list[tuple[float, float]]:
    rng = np.random.default_rng(seed)
    def lhs(lo, hi):
        edges = (np.arange(n) + rng.random(n)) / n          # stratified
        return 10 ** (np.log10(lo) + edges * (np.log10(hi) - np.log10(lo)))
    R = rng.permutation(lhs(r_lo, r_hi))
    C = rng.permutation(lhs(c_lo, c_hi))
    return list(zip(R.tolist(), C.tolist()))


# =========================================================================== #
#  Dataset factory (with QA -- non-converged / out-of-range dropped + logged)
# =========================================================================== #
def generate_dataset(n: int = 48, seed: int = 0,
                     r_lo: float = 300.0, r_hi: float = 3e5,
                     c_lo: float = 1e-12, c_hi: float = 1e-7) -> dict:
    pts = sample_lhs(n, seed, r_lo, r_hi, c_lo, c_hi)
    rows, drops = [], []
    for i, (R, C) in enumerate(pts):
        ev = spice_eval(R, C, run_name=f"rc_ds{i}")
        # QA: keep only converged points whose -3dB point is inside the AC sweep
        # and whose passband is a proper 0 dB (ideal LP) -- fail closed.
        if not ev["ok"] or not (1.0 < ev["f0"] < 5e9) or abs(ev["gain_dc"]) > 0.5:
            drops.append({"R": R, "C": C, "reason":
                          "no_conv" if not ev["ok"] else "out_of_range"})
            continue
        rows.append(ev)
    return {"rows": rows, "n_valid": len(rows), "n_dropped": len(drops),
            "drops": drops, "seed": seed,
            "bounds": {"r": [r_lo, r_hi], "c": [c_lo, c_hi]}}


# =========================================================================== #
#  Surrogate: OLS on log features.  log10 f0 = a*log10 R + b*log10 C + c
#  (physically a=b=-1, c=-log10(2*pi)); invertible for design.
# =========================================================================== #
class RCSurrogate:
    def __init__(self):
        self.coef_f0 = None      # [a, b, c] for log10 f0
        self.gain_mean = 0.0
        self.metrics = {}

    @staticmethod
    def _X(rows):
        return np.array([[math.log10(r["R"]), math.log10(r["C"]), 1.0] for r in rows])

    def fit(self, rows: list[dict], holdout: float = 0.25, seed: int = 1) -> dict:
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(rows))
        k = max(1, int(len(rows) * holdout))
        te, tr = idx[:k], idx[k:]
        rows_tr = [rows[i] for i in tr]
        rows_te = [rows[i] for i in te]

        Xtr = self._X(rows_tr)
        ytr = np.array([math.log10(r["f0"]) for r in rows_tr])
        self.coef_f0, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
        self.gain_mean = float(np.mean([r["gain_dc"] for r in rows_tr]))

        # held-out metrics on f0 (in Hz) and gain
        Xte = self._X(rows_te)
        yte = np.array([r["f0"] for r in rows_te])
        pred = 10 ** (Xte @ self.coef_f0)
        ss_res = float(np.sum((np.log10(yte) - np.log10(pred)) ** 2))
        ss_tot = float(np.sum((np.log10(yte) - np.log10(yte).mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
        mape = float(np.mean(np.abs(pred - yte) / yte)) * 100
        self.metrics = {"r2_log_f0": round(r2, 6), "mape_f0_pct": round(mape, 4),
                        "n_train": len(rows_tr), "n_test": len(rows_te),
                        "coef_f0": [round(c, 5) for c in self.coef_f0.tolist()],
                        "gain_dc_mean_db": round(self.gain_mean, 5)}
        return self.metrics

    def predict(self, R: float, C: float) -> dict:
        lf0 = self.coef_f0 @ np.array([math.log10(R), math.log10(C), 1.0])
        return {"f0": 10 ** float(lf0), "gain_dc": self.gain_mean}

    def invert_C(self, target_f0: float, R: float) -> float:
        """Solve C from the surrogate for a required f0 at fixed R."""
        a, b, c = self.coef_f0
        logC = (math.log10(target_f0) - c - a * math.log10(R)) / b
        return 10 ** logC


# =========================================================================== #
#  Schematic authoring in Virtuoso + reconstruct deck from OA connectivity
# =========================================================================== #
def _author_skill(R_str: str, C_str: str, lib: str, cell: str) -> str:
    # Deterministic straight-wire authoring on the exact, known analogLib hotspots
    # (probed): res R90 -> PLUS(0,0) MINUS(0.375,0); cap R0 -> PLUS(1.0,-1.0)
    # MINUS(1.0,-1.375). All wires are single orthogonal segments landing exactly
    # on hotspots, so connectivity is reproducible across fresh cells.
    return f'''
printf("SKILL_START\\n")
libName="{lib}"
unless(ddGetObj(libName) ddCreateLib(libName strcat("/home/work/" libName)))
lib=ddGetObj(libName)
errset(techBindTechFile(lib "gpdk090"))
cv=dbOpenCellViewByType(libName "{cell}" "schematic" "schematic" "w")

ipinM=dbOpenCellViewByType("basic" "ipin" "symbol")
opinM=dbOpenCellViewByType("basic" "opin" "symbol")

rI=dbCreateParamInstByMasterName(cv "analogLib" "res" "symbol" "R0" 0:0 "R90" 1
      list(list("r" "string" "{R_str}")))
cI=dbCreateParamInstByMasterName(cv "analogLib" "cap" "symbol" "C0" 1.0:-1.0 "R0" 1
      list(list("c" "string" "{C_str}")))
gI=dbCreateInstByMasterName(cv "analogLib" "gnd" "symbol" "GND0" 1.0:-2.0 "R0")
printf("MCP:insts=%L %L %L\\n" rI!=nil cI!=nil gI!=nil)
foreach( it gI~>instTerms
  printf("MCP:gndterm=%s box=%L\\n" it~>name
    dbTransformBBox(car(it~>term~>pins~>fig)~>bBox gI~>transform)))

pinIn =schCreatePin(cv ipinM "IN"  "input"  nil -1.5:0.0 "R0")
pinOut=schCreatePin(cv opinM "OUT" "output" nil  2.0:0.0 "R0")

wok=errset( progn(
  ; IN: pin -> R.PLUS  (horizontal)
  schCreateWire(cv "draw" "full" list(-1.5:0.0 0.0:0.0) 0.0625 0.0625 0.0)
  ; OUT: R.MINUS -> OUT pin (horizontal), with a vertical drop to C.PLUS
  schCreateWire(cv "draw" "full" list(0.375:0.0 2.0:0.0) 0.0625 0.0625 0.0)
  schCreateWire(cv "draw" "full" list(1.0:0.0 1.0:-1.0) 0.0625 0.0625 0.0)
  ; GND: C.MINUS -> gnd (vertical, extends through the gnd hotspot)
  schCreateWire(cv "draw" "full" list(1.0:-1.375 1.0:-2.1) 0.0625 0.0625 0.0)
  t) nil)
printf("MCP:wired=%L\\n" wok)

sc=errset(schCheck(cv) nil)
printf("MCP:schCheck=%L\\n" sc)
dbSave(cv)

; ---- connectivity as one parseable string: name:member,member,|... ----
cstr=""
foreach(net cv~>nets
  cstr=strcat(cstr net~>name ":")
  foreach(itm net~>instTerms cstr=strcat(cstr itm~>inst~>name "." itm~>name ","))
  foreach(trm net~>terminals cstr=strcat(cstr "PIN#" trm~>name ","))
  cstr=strcat(cstr "|"))
printf("MCP:CONN=%s\\n" cstr)
printf("MCP:Rval=%s\\n" dbGetq(rI "r"))
printf("MCP:Cval=%s\\n" dbGetq(cI "c"))
dbClose(cv)
printf("MCP:OK=1\\n")
exit(0)
'''


def _parse_conn(cstr: str) -> dict:
    """OA connectivity string -> {net_name: {'terms':[(inst,term)], 'pins':[..]}}."""
    nets = {}
    for seg in cstr.split("|"):
        if ":" not in seg:
            continue
        name, members = seg.split(":", 1)
        terms, pins = [], []
        for mem in members.split(","):
            mem = mem.strip()
            if not mem:
                continue
            if mem.startswith("PIN#"):
                pins.append(mem[4:])
            elif "." in mem:
                inst, term = mem.split(".", 1)
                terms.append((inst, term))
        nets[name] = {"terms": terms, "pins": pins}
    return nets


def reconstruct_deck(conn: dict, Rval: str, Cval: str):
    """Build a Spectre deck from the drawn schematic's connectivity.

    Maps the net carrying the IN pin -> `in`, OUT pin -> `out`, gnd -> `0`, and
    emits R0/C0 across whatever nets they were actually wired to. Returns
    (deck_or_None, node_of_term, issues)."""
    node_of = {}          # (inst,term) -> spectre node
    issues = []
    for name, d in conn.items():
        pins = [p.upper() for p in d["pins"]]
        uname = name.upper()
        is_gnd = any(t == "gnd!" for (_i, t) in d["terms"]) or uname in ("GND!", "GND")
        if is_gnd:
            node = "0"
        elif "IN" in pins or uname == "IN":
            node = "in"
        elif "OUT" in pins or uname == "OUT":
            node = "out"
        else:
            node = name.replace("!", "_").replace("<", "_").replace(">", "_")
        for (inst, term) in d["terms"]:
            node_of[(inst, term)] = node

    def nodes(inst):
        p = node_of.get((inst, "PLUS"))
        m = node_of.get((inst, "MINUS"))
        return p, m

    rp, rm = nodes("R0")
    cp, cm = nodes("C0")
    for label, (a, b) in (("R0", (rp, rm)), ("C0", (cp, cm))):
        if a is None or b is None:
            issues.append(f"{label} terminal not connected ({a},{b})")
    # topology sanity: R between in and out, C between out and 0
    if not issues:
        if "in" not in (rp, rm) or "out" not in (rp, rm):
            issues.append(f"R0 not wired in<->out (got {rp},{rm})")
        if "out" not in (cp, cm) or "0" not in (cp, cm):
            issues.append(f"C0 not wired out<->gnd (got {cp},{cm})")
    if issues:
        return None, node_of, issues

    deck = ("simulator lang=spectre\nglobal 0\n"
            "Vin (in 0) vsource dc=0 mag=1 type=dc\n"
            f"R0 ({rp} {rm}) resistor r={Rval}\n"
            f"C0 ({cp} {cm}) capacitor c={Cval}\n"
            f"{AC_LINE}\n")
    return deck, node_of, issues


def verify_schematic(R: float, C: float, lib: str = "RC_surrogate",
                     cell: str = "rc_lp", timeout: int = 520) -> dict:
    """Author the real Virtuoso schematic for (R,C), read its OA connectivity,
    reconstruct a Spectre deck FROM the schematic, re-simulate, and measure.
    This is the schematic-equivalence check for one candidate design."""
    R_str, C_str = f"{R:.6g}", f"{C:.6g}"
    r = physical.run_skill_raw(_author_skill(R_str, C_str, lib, cell), timeout=timeout)
    v = r["values"]
    conn_raw = v.get("CONN", "")
    conn = _parse_conn(conn_raw)
    out = {"authored": r["ok"], "wired": v.get("wired") == "(t)",
           "schCheck": v.get("schCheck"), "Rval": v.get("Rval"),
           "Cval": v.get("Cval"), "conn": conn_raw}
    if not conn:
        out.update({"equivalent": False, "reason": "no connectivity read back"})
        return out
    deck, _nodes, issues = reconstruct_deck(conn, v.get("Rval", R_str), v.get("Cval", C_str))
    if deck is None:
        out.update({"equivalent": False, "reason": "; ".join(issues)})
        return out
    sim = api.simulate(deck, MEASURES, run_name=f"rc_sch_{cell}", save=True,
                       title=f"RC schematic re-sim R={R_str} C={C_str}")
    if not sim.get("ok"):
        out.update({"equivalent": False, "reason": "schematic deck did not simulate",
                    "sim_errors": sim.get("errors")})
        return out
    m = sim["measurements"]
    f0, g = m.get("f0"), m.get("gain_dc")
    out.update({"equivalent": True, "reconstructed_deck": deck,
                "measured_f0": None if isinstance(f0, dict) else f0,
                "measured_gain_dc": None if isinstance(g, dict) else g,
                "run_id": sim.get("run_id"), "dashboard": sim.get("dashboard")})
    return out


# =========================================================================== #
#  The loop: propose -> author schematic -> re-sim -> verify -> (retrain) repeat
# =========================================================================== #
def design_and_verify(target_f0: float = 1e6, target_gain_db: float = 0.0,
                      R_fixed: float = 1591.5, tol_f0: float = 0.05,
                      tol_gain: float = 0.5, max_iter: int = 5,
                      surrogate: RCSurrogate | None = None,
                      dataset_rows: list | None = None) -> dict:
    """Drive the RC low-pass to the required outputs, verifying every proposal
    against a freshly-authored Virtuoso schematic. Folds each schematic
    measurement back into the dataset and retrains until the *schematic* meets
    spec (or max_iter)."""
    core.ensure_vm()
    assert surrogate is not None and surrogate.coef_f0 is not None, "fit a surrogate first"
    rows = list(dataset_rows or [])
    iters = []
    for i in range(1, max_iter + 1):
        C = surrogate.invert_C(target_f0, R_fixed)
        pred = surrogate.predict(R_fixed, C)
        vr = verify_schematic(R_fixed, C, cell=f"rc_lp_it{i}")
        mf0, mg = vr.get("measured_f0"), vr.get("measured_gain_dc")
        f0_err = abs(mf0 - target_f0) / target_f0 if mf0 else None
        gain_ok = (mg is not None and abs(mg - target_gain_db) <= tol_gain)
        met = bool(vr.get("equivalent") and f0_err is not None
                   and f0_err <= tol_f0 and gain_ok)
        iters.append({
            "iter": i, "R": R_fixed, "C_proposed": C,
            "predicted_f0": pred["f0"], "predicted_gain_dc": pred["gain_dc"],
            "schematic_equivalent": vr.get("equivalent"),
            "schCheck": vr.get("schCheck"),
            "measured_f0": mf0, "measured_gain_dc": mg,
            "f0_error_pct": None if f0_err is None else round(f0_err * 100, 4),
            "spec_met": met, "reason": vr.get("reason"),
            "run_id": vr.get("run_id"),
        })
        if met:
            return {"converged": True, "iterations": iters, "final": iters[-1],
                    "R": R_fixed, "C": C, "dataset_size": len(rows)}
        # fold the *schematic-measured* truth back in and retrain (active learning)
        if mf0 and mg is not None:
            rows.append({"ok": True, "R": R_fixed, "C": C, "f0": mf0, "gain_dc": mg})
            surrogate.fit(rows)
    return {"converged": False, "iterations": iters, "final": iters[-1],
            "R": R_fixed, "C": iters[-1]["C_proposed"], "dataset_size": len(rows)}
