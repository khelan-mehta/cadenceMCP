"""The 10 lab experiments as parameterized, headless Spectre decks.

Each experiment exposes:
  * a parameter schema (every knob tweakable from Claude Desktop / the dashboard),
  * a netlist builder,
  * the list of analyses it runs,
  * default plots for the dashboard,
  * a measurement function that extracts the manual's required quantities.

All decks are self-contained Spectre (`simulator lang=spectre`) targeting gpdk090.
Device polarity/rails follow the manual (2 V thick-oxide devices for 1.8 V rails).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from . import config, measure
from .opparse import device_table

MODEL = config.PDK_MODEL_INCLUDE


# --------------------------------------------------------------------------- #
#  parameter-schema helpers
# --------------------------------------------------------------------------- #
def P(name, default, unit="", desc="", ptype="text", choices=None, group="Design"):
    return {"name": name, "default": default, "unit": unit, "desc": desc,
            "type": ptype, "choices": choices or [], "group": group}


def _num(v):
    """Accept '1u', '100n', '1.8', '5k' -> float."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        pass
    mult = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3,
            "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "meg": 1e6}
    for suf, mv in sorted(mult.items(), key=lambda kv: -len(kv[0])):
        if s.endswith(suf):
            try:
                return float(s[:-len(suf)]) * mv
            except ValueError:
                return float("nan")
    return float("nan")


def _header(p):
    corner = p.get("corner", config.PDK_DEFAULT_CORNER)
    return (f"// {p.get('_title','')}\n"
            f"simulator lang=spectre\n"
            f"global 0\n"
            f'include "{MODEL}" section={corner}\n')


def _opts(p):
    return f"simOpt options temp={p.get('temp','27')} save=allpub gmin=1e-13\n"


def _opinfo():
    return ('oppoint dc\n'
            'opinfo info what=oppoint where=file file="op.info"\n')


def _phase_deg(cdata_list):
    return [math.degrees(math.atan2(im, re)) for (re, im) in cdata_list]


COMMON = [
    P("corner", config.PDK_DEFAULT_CORNER, desc="PDK process corner (NN=typical)",
      ptype="enum", choices=config.PDK_CORNERS, group="Sim"),
    P("temp", "27", "C", "simulation temperature", "text", group="Sim"),
]


# --------------------------------------------------------------------------- #
@dataclass
class Experiment:
    id: str
    title: str
    co: str
    spec: str
    params: list
    build: Callable[[dict], str]
    analyses: list
    plots: list
    measure: Callable[["object"], dict]
    notes: str = ""

    def default_params(self):
        return {p["name"]: p["default"] for p in self.params}


REG: dict[str, Experiment] = {}


def _reg(exp: Experiment):
    REG[exp.id] = exp
    return exp


# =========================================================================== #
#  EXP 1 — CMOS inverter (VTC, VT, propagation delay)
# =========================================================================== #
def _build_exp1(p):
    d = p["device_n"]; dp = p["device_p"]
    s = _header(p)
    s += (f"parameters vdd={p['vdd']} vin=0\n"
          f"Vdd (vdd 0) vsource dc=vdd\n"
          f"Vin (in 0) vsource dc=vin type=pulse val0=0 val1={p['vdd']} "
          f"period={p['period']} rise={p['trf']} fall={p['trf']} width={p['pw']} mag=1\n"
          f"MN (out in 0 0) {d} w={p['wn']} l={p['l']}\n"
          f"MP (out in vdd vdd) {dp} w={p['wp']} l={p['l']}\n"
          f"CL (out 0) capacitor c={p['cl']}\n")
    s += _opts(p)
    s += "vtc dc dev=Vin param=dc start=0 stop=" + str(p["vdd"]) + f" step={p['vstep']}\n"
    s += f"trans tran stop={p['tstop']} errpreset=conservative\n"
    s += _opinfo()
    return s


def _meas_exp1(res):
    out = {}
    a = res.analyses
    if "vtc" in a:
        d = a["vtc"]["data"]; x = d.get("vin") or d.get(a["vtc"]["sweep"])
        vout = d.get("out")
        if x and vout:
            # switching threshold: where Vout == Vin
            diff = [vo - vi for vo, vi in zip(vout, x)]
            vm = measure.cross(x, diff, 0.0)
            out["switching_threshold_vm_v"] = vm
            g = measure.deriv(x, vout)
            out["max_gain_vtc"] = min(g)  # most negative slope
    if "trans" in a:
        d = a["trans"]["data"]; t = d.get(a["trans"]["sweep"]); vo = d.get("out"); vi = d.get("in")
        if t and vo and vi:
            vdd = max(vi)
            thp = measure.cross(t, vi, vdd / 2, "rising")
            tho = measure.cross(t, vo, vdd / 2, "falling")
            if thp and tho:
                out["tp_hl_s"] = abs(tho - thp)
    out["power_w"] = res.opinfo.get("total_power_w")
    out["devices"] = device_table(res.opinfo)
    return out


_reg(Experiment(
    id="1", title="Exploring Virtuoso — CMOS Inverter", co="CO1-CO4",
    spec="Find VT (switching threshold) & propagation delay; pre/post-layout.",
    params=[
        P("vdd", "1.0", "V", "supply", group="Design"),
        P("wn", "1u", "m", "NMOS width"), P("wp", "2u", "m", "PMOS width"),
        P("l", "100n", "m", "channel length"),
        P("device_n", "gpdk090_nmos1v", desc="NMOS model", ptype="enum",
          choices=["gpdk090_nmos1v", "gpdk090_nmos2v"]),
        P("device_p", "gpdk090_pmos1v", desc="PMOS model", ptype="enum",
          choices=["gpdk090_pmos1v", "gpdk090_pmos2v"]),
        P("cl", "50f", "F", "load cap"),
        P("vstep", "0.01", "V", "VTC sweep step", group="Sim"),
        P("period", "2n", "s", "input pulse period", group="Stimulus"),
        P("pw", "1n", "s", "pulse width", group="Stimulus"),
        P("trf", "50p", "s", "rise/fall time", group="Stimulus"),
        P("tstop", "4n", "s", "tran stop", group="Sim"),
        *COMMON,
    ],
    build=_build_exp1,
    analyses=[{"name": "vtc", "kind": "dc", "desc": "Voltage transfer curve"},
              {"name": "trans", "kind": "tran", "desc": "Pulse response / delay"}],
    plots=[
        {"title": "Inverter VTC", "analysis": "vtc", "x": "vin", "y": ["out"],
         "xlabel": "Vin (V)", "ylabel": "Vout (V)"},
        {"title": "Transient response", "analysis": "trans", "x": "time",
         "y": ["in", "out"], "xlabel": "t (s)", "ylabel": "V"},
    ],
    measure=_meas_exp1,
    notes="Layout/DRC/LVS/RC-extraction are GUI (Virtuoso+Diva) steps; "
          "this deck delivers the pre-layout VTC + delay. Post-layout re-sim reuses "
          "the same deck with an extracted netlist.",
))


# =========================================================================== #
#  EXP 2 — MOS I-V characteristics & parameter extraction (VT0, Kn, gamma, lambda)
# =========================================================================== #
def _build_exp2(p):
    dev = p["device"]
    pmos = "pmos" in dev
    s = _header(p)
    if not pmos:
        s += (f"parameters vgs={p['vgs_fixed']} vds={p['vdd']} vbs={p['vbs']}\n"
              f"Vg (g 0) vsource dc=vgs\n"
              f"Vd (d 0) vsource dc=vds\n"
              f"Vb (b 0) vsource dc=vbs\n"
              f"M0 (d g 0 b) {dev} w={p['w']} l={p['l']}\n")
    else:
        s += (f"parameters vsg={p['vgs_fixed']} vsd={p['vdd']} vbs={p['vbs']}\n"
              f"Vs (s 0) vsource dc={p['vdd']}\n"
              f"Vg (g 0) vsource dc={p['vdd']}-vsg\n"
              f"Vd (d 0) vsource dc={p['vdd']}-vsd\n"
              f"M0 (d g s s) {dev} w={p['w']} l={p['l']}\n")
    s += _opts(p)
    if not pmos:
        s += f"idvgs dc param=vgs start=0 stop={p['vdd']} step={p['vgs_step']}\n"
        s += f"idvds dc param=vds start=0 stop={p['vdd']} step={p['vds_step']}\n"
    else:
        s += f"idvgs dc param=vsg start=0 stop={p['vdd']} step={p['vgs_step']}\n"
        s += f"idvds dc param=vsd start=0 stop={p['vdd']} step={p['vds_step']}\n"
    s += _opinfo()
    return s


def _meas_exp2(res):
    out = {}
    a = res.analyses
    if "idvgs" in a:
        d = a["idvgs"]["data"]; sw = a["idvgs"]["sweep"]
        vgs = d.get(sw)
        idd = [abs(v) for v in d.get("Vd:p", [])]
        if vgs and idd:
            vt = measure.extract_vt0(vgs, idd)
            out.update(vt)
            if not math.isnan(vt.get("vt0", float("nan"))):
                out.update(measure.extract_kn(vgs, idd, vt["vt0"]))
    if "idvds" in a:
        d = a["idvds"]["data"]; sw = a["idvds"]["sweep"]
        vds = d.get(sw); idd = [abs(v) for v in d.get("Vd:p", [])]
        if vds and idd:
            out.update(measure.extract_lambda(vds, idd))
    out["devices"] = device_table(res.opinfo)
    # fT (max operating freq) from op.info
    for name, inst in res.opinfo.get("instances", {}).items():
        if "fug" in inst.get("params", {}):
            out["ft_hz"] = inst["params"]["fug"]["si"]
            break
    return out


_reg(Experiment(
    id="2", title="MOS I–V Characteristics & Parameter Extraction", co="CO2",
    spec="Extract VT0 (Id–Vgs), Kn & γ (√Id–Vgs, body bias), λ (Id–Vds).",
    params=[
        P("device", "gpdk090_nmos1v", desc="device under test", ptype="enum",
          choices=["gpdk090_nmos1v", "gpdk090_pmos1v", "gpdk090_nmos2v",
                   "gpdk090_pmos2v", "gpdk090_nmos1v_hvt"]),
        P("w", "1u", "m", "width"), P("l", "100n", "m", "length"),
        P("vdd", "1.8", "V", "max sweep / drain voltage"),
        P("vgs_fixed", "0.9", "V", "gate bias held during Id–Vds"),
        P("vbs", "0", "V", "body–source bias (sweep this for γ)", group="Design"),
        P("vgs_step", "0.02", "V", "Id–Vgs step", group="Sim"),
        P("vds_step", "0.02", "V", "Id–Vds step", group="Sim"),
        *COMMON,
    ],
    build=_build_exp2,
    analyses=[{"name": "idvgs", "kind": "dc", "desc": "Id vs Vgs (transfer)"},
              {"name": "idvds", "kind": "dc", "desc": "Id vs Vds (output)"}],
    plots=[
        {"title": "Id–Vgs (transfer)", "analysis": "idvgs", "x": "@sweep",
         "y": ["Vd:p"], "ytransform": "abs", "xlabel": "Vgs (V)", "ylabel": "Id (A)"},
        {"title": "√Id–Vgs (Kn / γ)", "analysis": "idvgs", "x": "@sweep",
         "y": ["Vd:p"], "ytransform": "sqrtabs", "xlabel": "Vgs (V)", "ylabel": "√Id"},
        {"title": "Id–Vds (output, λ)", "analysis": "idvds", "x": "@sweep",
         "y": ["Vd:p"], "ytransform": "abs", "xlabel": "Vds (V)", "ylabel": "Id (A)"},
    ],
    measure=_meas_exp2,
    notes="Re-run with different vbs to get the second √Id–Vgs curve for γ. "
          "Set device=…pmos… for the PMOS assignment.",
))


# =========================================================================== #
#  EXP 3 — Current mirrors (simple / cascode / PMOS), VDD=1.8, sink 10 uA
# =========================================================================== #
def _build_exp3(p):
    mtype = p["mirror_type"]
    dev = p["device"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} rcs={p['rcs']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    if mtype == "simple":
        # reference branch: Rset from vdd to diode-connected M1; mirror M2 with Rcs load
        s += (f"Rset (vdd nref) resistor r={p['rset']}\n"
              f"M1 (nref nref 0 0) {dev} w={p['w']} l={p['l']}\n"
              f"M2 (nbias nref 0 0) {dev} w={p['w']} l={p['l']}\n"
              f"Rload (vdd nbias) resistor r=rcs\n")
        iout_node = "Rload"
    elif mtype == "cascode":
        s += (f"Rset (vdd nref) resistor r={p['rset']}\n"
              f"M1 (n1 n1 0 0) {dev} w={p['w']} l={p['l']}\n"
              f"M1c (nref nref n1 0) {dev} w={p['w']} l={p['l']}\n"
              f"M2 (n2 n1 0 0) {dev} w={p['w']} l={p['l']}\n"
              f"M2c (nbias nref n2 0) {dev} w={p['w']} l={p['l']}\n"
              f"Rload (vdd nbias) resistor r=rcs\n")
        iout_node = "Rload"
    else:  # pmos mirror sourcing current
        pdev = p["device_p"]
        s += (f"Rset (nref 0) resistor r={p['rset']}\n"
              f"M1 (nref nref vdd vdd) {pdev} w={p['w']} l={p['l']}\n"
              f"M2 (nbias nref vdd vdd) {pdev} w={p['w']} l={p['l']}\n"
              f"Rload (nbias 0) resistor r=rcs\n")
        iout_node = "Rload"
    s += _opts(p)
    s += f"sweeprcs dc param=rcs start={p['rcs_start']} stop={p['rcs_stop']} step={p['rcs_step']}\n"
    s += _opinfo()
    return s


def _meas_exp3(res):
    out = {}
    a = res.analyses
    if "sweeprcs" in a:
        d = a["sweeprcs"]["data"]; sw = a["sweeprcs"]["sweep"]
        rcs = d.get(sw)
        iload = d.get("Rload:p") or d.get("Vdd:p")
        if rcs and iload:
            iload = [abs(v) for v in iload]
            out["rcs"] = rcs
            out["ibias"] = iload
            # reference current ~ value at nominal rcs (first point roughly)
            iref = iload[len(iload) // 2]
            out["iref_mid_a"] = iref
            # range of Rcs where |Ibias-Iref|<10%
            lo = hi = None
            for r, i in zip(rcs, iload):
                if iref and abs(i - iref) / iref < 0.10:
                    lo = r if lo is None else lo
                    hi = r
            out["rcs_range_within_10pct"] = [lo, hi]
    out["devices"] = device_table(res.opinfo)
    out["power_w"] = res.opinfo.get("total_power_w")
    return out


_reg(Experiment(
    id="3", title="Current Mirrors (simple / cascode / PMOS)", co="CO2",
    spec="VDD = 1.8 V, sink IREF = 10 µA; find Rcs range keeping ΔIBIAS < 10%.",
    params=[
        P("mirror_type", "simple", desc="topology", ptype="enum",
          choices=["simple", "cascode", "pmos"]),
        P("device", "gpdk090_nmos2v", desc="mirror NMOS (2 V for 1.8 V rail)",
          ptype="enum", choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("device_p", "gpdk090_pmos2v", desc="mirror PMOS (pmos type)",
          ptype="enum", choices=["gpdk090_pmos2v", "gpdk090_pmos1v"]),
        P("vdd", "1.8", "V", "supply"),
        P("w", "5u", "m", "mirror device width"), P("l", "1u", "m", "length"),
        P("rset", "165k", "ohm", "reference set resistor (~ (VDD-Vgs)/10µA)"),
        P("rcs", "165k", "ohm", "nominal output-branch resistor"),
        P("rcs_start", "1k", "ohm", "Rcs sweep start", group="Sim"),
        P("rcs_stop", "500k", "ohm", "Rcs sweep stop", group="Sim"),
        P("rcs_step", "5k", "ohm", "Rcs sweep step", group="Sim"),
        *COMMON,
    ],
    build=_build_exp3,
    analyses=[{"name": "sweeprcs", "kind": "dc", "desc": "IBIAS vs output resistor Rcs"}],
    plots=[{"title": "IBIAS vs Rcs", "analysis": "sweeprcs", "x": "@sweep",
            "y": ["Rload:p"], "ytransform": "abs", "xlabel": "Rcs (Ω)",
            "ylabel": "IBIAS (A)"}],
    measure=_meas_exp3,
))


# =========================================================================== #
#  common single-transistor amplifier deck (Exp 4/5/6/7)
# =========================================================================== #
def _amp_source(p):
    """Input source doubling as AC (mag) and transient sine stimulus."""
    return (f"Vin (in 0) vsource dc={p['vin_dc']} mag=1 "
            f"type=sine sinedc={p['vin_dc']} ampl={p['vac']} freq={p['fin']}\n")


def _amp_analyses(p, out="out", inn="in"):
    s = _opts(p)
    s += f"dcsw dc dev=Vin param=dc start=0 stop={p['vdd']} step=0.01\n"
    s += f"acs ac start={p['fstart']} stop={p['fstop']} dec={p['fdec']}\n"
    nper = 5
    stop = nper / _num(p["fin"])
    s += f"trans tran stop={stop:.6g} errpreset=conservative\n"
    if p.get("do_noise", "0") in ("1", 1, True, "true"):
        s += f"noises noise start={p['fstart']} stop={p['fstop']} dec={p['fdec']} oprobe=Vin out={out}\n"
    s += _opinfo()
    return s


def _meas_amp(res, out="out"):
    m = {}
    a = res.analyses
    if "acs" in a:
        d = a["acs"]["data"]; f = d.get(a["acs"]["sweep"]); mag = d.get(out)
        if f and mag:
            m.update(measure.ac_gain_bw(f, mag))
            cd = (a["acs"].get("cdata") or {}).get(out)
            if cd:
                ph = _phase_deg(cd)
                m.update(measure.phase_margin(f, mag, ph))
    if "trans" in a:
        d = a["trans"]["data"]; t = d.get(a["trans"]["sweep"]); vo = d.get(out)
        if t and vo:
            m["vout_pp"] = max(vo) - min(vo)
    if "noises" in a:
        d = a["noises"]["data"]; f = d.get(a["noises"]["sweep"]); on = d.get("out")
        if f and on:
            # integrated output noise (rough)
            m["output_noise_at_fmin"] = on[0] if on else None
    m["power_w"] = res.opinfo.get("total_power_w")
    m["devices"] = device_table(res.opinfo)
    return m


def _amp_plots(out="out"):
    return [
        {"title": "AC gain", "analysis": "acs", "x": "@sweep", "y": [out],
         "ytransform": "db", "xscale": "log", "xlabel": "f (Hz)", "ylabel": "Gain (dB)"},
        {"title": "AC phase", "analysis": "acs", "x": "@sweep", "y": [out],
         "ytransform": "phase", "xscale": "log", "xlabel": "f (Hz)", "ylabel": "Phase (°)"},
        {"title": "DC transfer", "analysis": "dcsw", "x": "@sweep", "y": [out],
         "xlabel": "Vin (V)", "ylabel": "Vout (V)"},
        {"title": "Transient", "analysis": "trans", "x": "time", "y": ["in", out],
         "xlabel": "t (s)", "ylabel": "V"},
    ]


_AMP_COMMON = [
    P("vdd", "1.8", "V", "supply"),
    P("w", "10u", "m", "driver width"), P("l", "1u", "m", "driver length"),
    P("vin_dc", "0.7", "V", "input DC bias (operating point)"),
    P("vac", "5m", "V", "transient sine amplitude", group="Stimulus"),
    P("fin", "1k", "Hz", "transient sine frequency", group="Stimulus"),
    P("fstart", "1", "Hz", "AC start", group="Sim"),
    P("fstop", "1G", "Hz", "AC stop", group="Sim"),
    P("fdec", "20", "", "AC points/decade", group="Sim"),
    P("cl", "100f", "F", "load capacitance"),
    P("do_noise", "0", "", "run noise analysis (1/0)", group="Sim"),
]


# =========================================================================== #
#  EXP 4 — CS amplifier (resistive / NMOS / PMOS load); Gain 20 dB, P < 1 mW
# =========================================================================== #
def _build_exp4(p):
    load = p["load_type"]; dev = p["device"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} vin_dc={p['vin_dc']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    s += _amp_source(p)
    s += f"M0 (out in 0 0) {dev} w={p['w']} l={p['l']}\n"
    if load == "resistive":
        s += f"RD (vdd out) resistor r={p['rd']}\n"
    elif load == "pmos":
        s += (f"Vbp (vbp 0) vsource dc={p['vbias_load']}\n"
              f"M1 (out vbp vdd vdd) {p['device_p']} w={p['wl']} l={p['l']}\n")
    else:  # nmos current-source load
        s += (f"Vbn (vbn 0) vsource dc={p['vbias_load']}\n"
              f"M1 (vdd vbn out out) {dev} w={p['wl']} l={p['l']}\n")
    s += f"CL (out 0) capacitor c={p['cl']}\n"
    s += _amp_analyses(p)
    return s


_reg(Experiment(
    id="4", title="Common-Source Amplifier (resistive / current-source load)", co="CO2,CO4",
    spec="Gain = 20 dB, Power < 1 mW. AC/DC/transient; report gain, BW, swing, noise.",
    params=[
        P("load_type", "resistive", desc="load", ptype="enum",
          choices=["resistive", "pmos", "nmos"]),
        P("device", "gpdk090_nmos2v", desc="driver NMOS", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("device_p", "gpdk090_pmos2v", desc="PMOS load model", ptype="enum",
          choices=["gpdk090_pmos2v", "gpdk090_pmos1v"]),
        P("rd", "10k", "ohm", "resistive load"),
        P("wl", "10u", "m", "load device width (pmos/nmos load)"),
        P("vbias_load", "0.9", "V", "load gate bias (current-source load)"),
        *_AMP_COMMON, *COMMON,
    ],
    build=_build_exp4,
    analyses=[{"name": "dcsw", "kind": "dc", "desc": "DC transfer"},
              {"name": "acs", "kind": "ac", "desc": "AC gain/phase"},
              {"name": "trans", "kind": "tran", "desc": "Transient"},
              {"name": "noises", "kind": "noise", "desc": "Output noise (optional)"}],
    plots=_amp_plots(), measure=_meas_amp,
))


# =========================================================================== #
#  EXP 5 — Source-degenerated CS + parametric sweep on Rs
# =========================================================================== #
def _build_exp5(p):
    dev = p["device"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} vin_dc={p['vin_dc']} rs={p['rs']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    s += _amp_source(p)
    s += f"M0 (out in src 0) {dev} w={p['w']} l={p['l']}\n"
    s += "Rs (src 0) resistor r=rs\n"
    s += f"RD (vdd out) resistor r={p['rd']}\n"
    s += f"CL (out 0) capacitor c={p['cl']}\n"
    s += _amp_analyses(p)
    # extra: parametric sweep of gain vs Rs via nested dc? use `sweep` analysis over ac is hard;
    # instead an explicit paramset list handled by the server for a proper parametric run.
    return s


def _meas_exp5(res):
    return _meas_amp(res)


_reg(Experiment(
    id="5", title="Source-Degenerated CS Amplifier + Parametric Rs", co="CO2,CO4",
    spec="Add source resistor Rs to linearize; find optimum Rs (parametric) for target gain.",
    params=[
        P("device", "gpdk090_nmos2v", desc="driver", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("rd", "10k", "ohm", "load resistor"),
        P("rs", "1k", "ohm", "source degeneration resistor"),
        P("rs_sweep", "0,200,500,1k,2k,5k", desc="parametric Rs list (comma-sep)",
          group="Parametric"),
        *_AMP_COMMON, *COMMON,
    ],
    build=_build_exp5,
    analyses=[{"name": "dcsw", "kind": "dc", "desc": "DC transfer"},
              {"name": "acs", "kind": "ac", "desc": "AC gain/phase"},
              {"name": "trans", "kind": "tran", "desc": "Transient"}],
    plots=_amp_plots(), measure=_meas_exp5,
    notes="Use tool run_parametric with param 'rs' and the rs_sweep list to get "
          "gain-vs-Rs; the server sweeps Rs and overlays AC gain curves.",
))


# =========================================================================== #
#  EXP 6 — CD (source follower) & CG amplifiers + noise/harmonic
# =========================================================================== #
def _build_exp6(p):
    dev = p["device"]; stage = p["stage"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} vin_dc={p['vin_dc']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    if stage == "CD":  # common-drain / source follower
        s += _amp_source(p)
        s += f"M0 (vdd in out 0) {dev} w={p['w']} l={p['l']}\n"
        s += f"RS (out 0) resistor r={p['rload']}\n"
        outn = "out"
    else:  # CG common-gate: input at source, gate AC-grounded (fixed bias)
        s += (f"Vg (g 0) vsource dc={p['vbias_load']}\n"
              f"Vin (in 0) vsource dc={p['vin_dc']} mag=1 type=sine "
              f"sinedc={p['vin_dc']} ampl={p['vac']} freq={p['fin']}\n"
              f"Rin (in src) resistor r={p['rsin']}\n"
              f"M0 (out g src 0) {dev} w={p['w']} l={p['l']}\n"
              f"RD (vdd out) resistor r={p['rload']}\n")
        outn = "out"
    s += f"CL ({outn} 0) capacitor c={p['cl']}\n"
    s += _amp_analyses(p, out=outn)
    return s


_reg(Experiment(
    id="6", title="Common-Drain & Common-Gate Amplifiers", co="CO2,CO4",
    spec="CD & CG stages; AC/DC/tran + noise + harmonic (THD). Compare with CS.",
    params=[
        P("stage", "CD", desc="stage", ptype="enum", choices=["CD", "CG"]),
        P("device", "gpdk090_nmos2v", desc="device", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("rload", "10k", "ohm", "load/source resistor"),
        P("rsin", "1k", "ohm", "CG input series resistor"),
        P("vbias_load", "1.0", "V", "CG gate bias"),
        *_AMP_COMMON, *COMMON,
    ],
    build=_build_exp6,
    analyses=[{"name": "dcsw", "kind": "dc", "desc": "DC transfer"},
              {"name": "acs", "kind": "ac", "desc": "AC gain/phase"},
              {"name": "trans", "kind": "tran", "desc": "Transient (THD)"},
              {"name": "noises", "kind": "noise", "desc": "Output noise"}],
    plots=_amp_plots(), measure=_meas_amp,
))


# =========================================================================== #
#  EXP 7 — Cascode amplifier + Monte Carlo + P1dB / IIP3
# =========================================================================== #
def _build_exp7(p):
    dev = p["device"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} vin_dc={p['vin_dc']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    s += _amp_source(p)
    s += (f"Vcasc (vc 0) vsource dc={p['vcasc']}\n"
          f"M0 (n1 in 0 0) {dev} w={p['w']} l={p['l']}\n"        # CS device
          f"M1 (out vc n1 0) {dev} w={p['w']} l={p['l']}\n"      # cascode device
          f"RD (vdd out) resistor r={p['rd']}\n"
          f"CL (out 0) capacitor c={p['cl']}\n")
    s += _amp_analyses(p)
    return s


def _meas_exp7(res):
    m = _meas_amp(res)
    # gain compression / THD from transient (proxy for P1dB when amplitude swept)
    a = res.analyses
    if "trans" in a:
        d = a["trans"]["data"]; t = d.get(a["trans"]["sweep"]); vo = d.get("out")
        # fundamental amplitude
        if t and vo:
            m["vout_pp"] = max(vo) - min(vo)
    return m


_reg(Experiment(
    id="7", title="Cascode Amplifier + Monte Carlo + P1dB/IIP3", co="CO2,CO4",
    spec="High-gain cascode; Monte-Carlo spread, 1-dB compression point, IIP3.",
    params=[
        P("device", "gpdk090_nmos2v", desc="device", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("rd", "20k", "ohm", "load resistor"),
        P("vcasc", "1.2", "V", "cascode gate bias"),
        P("mc_runs", "20", "", "Monte-Carlo iterations (run_montecarlo tool)",
          group="Statistics"),
        *_AMP_COMMON, *COMMON,
    ],
    build=_build_exp7,
    analyses=[{"name": "dcsw", "kind": "dc", "desc": "DC transfer"},
              {"name": "acs", "kind": "ac", "desc": "AC gain/phase"},
              {"name": "trans", "kind": "tran", "desc": "Transient"}],
    plots=_amp_plots(), measure=_meas_exp7,
    notes="P1dB / IIP3: use run_power_sweep (amplitude sweep + FFT). "
          "Monte-Carlo: use run_montecarlo (corner spread) tool.",
))


# =========================================================================== #
#  EXP 8 — Differential amplifier; VDD=1.8, Gain 30 dB, Power 5 mW; CMRR/ICMR/GBP
# =========================================================================== #
def _build_exp8(p):
    n = p["device_n"]; pl = p["device_p"]
    s = _header(p)
    mode = p["input_mode"]  # 'diff' or 'cm'
    s += f"parameters vdd={p['vdd']} vcm={p['vcm']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    # differential input sources
    if mode == "diff":
        s += (f"Vip (inp 0) vsource dc=vcm mag=0.5\n"
              f"Vin (inm 0) vsource dc=vcm mag=-0.5\n")
    else:  # common-mode
        s += (f"Vip (inp 0) vsource dc=vcm mag=1\n"
              f"Vin (inm 0) vsource dc=vcm mag=1\n")
    # tail current source
    s += f"Itail (tail 0) isource dc={p['itail']}\n"
    # input pair
    s += (f"M1 (op inp tail 0) {n} w={p['w']} l={p['l']}\n"
          f"M2 (om inm tail 0) {n} w={p['w']} l={p['l']}\n")
    # load
    if p["load"] == "pmos_pair":  # differential output
        s += (f"M3 (op op vdd vdd) {pl} w={p['wl']} l={p['l']}\n"
              f"M4 (om om vdd vdd) {pl} w={p['wl']} l={p['l']}\n")
    else:  # current-mirror load -> single-ended output at om
        s += (f"M3 (op op vdd vdd) {pl} w={p['wl']} l={p['l']}\n"
              f"M4 (om op vdd vdd) {pl} w={p['wl']} l={p['l']}\n")
    s += f"CL (om 0) capacitor c={p['cl']}\n"
    s += _opts(p)
    s += f"acs ac start={p['fstart']} stop={p['fstop']} dec={p['fdec']}\n"
    s += f"icmr dc dev=Vip param=dc start=0 stop={p['vdd']} step=0.02\n"
    s += _opinfo()
    return s


def _meas_exp8(res):
    m = {}
    a = res.analyses
    if "acs" in a:
        d = a["acs"]["data"]; f = d.get(a["acs"]["sweep"])
        cd = a["acs"].get("cdata") or {}
        # true differential output = om - op (complex) when both nodes exist,
        # else single-ended om (mirror load).
        if "om" in cd and "op" in cd:
            diff = [((rm - rp) ** 2 + (im - ip) ** 2) ** 0.5
                    for (rm, im), (rp, ip) in zip(cd["om"], cd["op"])]
            mag = diff
        else:
            mag = d.get("om")
        if f and mag:
            g = measure.ac_gain_bw(f, mag)
            m["gain_db"] = g.get("dc_gain_db")
            m["gain_vv"] = g.get("dc_gain_vv")
            m["bandwidth_hz"] = g.get("bandwidth_hz")
            m["gbw_hz"] = g.get("gbw_hz")
    m["power_w"] = res.opinfo.get("total_power_w")
    m["devices"] = device_table(res.opinfo)
    return m


_reg(Experiment(
    id="8", title="Differential Amplifier (PMOS load / mirror load)", co="CO2,CO4",
    spec="VDD=1.8 V, Gain=30 dB, Power=5 mW. Adm, Acm, CMRR, ICMR±, GBP.",
    params=[
        P("input_mode", "diff", desc="AC drive", ptype="enum", choices=["diff", "cm"]),
        P("load", "pmos_pair", desc="load type", ptype="enum",
          choices=["pmos_pair", "mirror"]),
        P("device_n", "gpdk090_nmos2v", desc="input pair", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("device_p", "gpdk090_pmos2v", desc="load", ptype="enum",
          choices=["gpdk090_pmos2v", "gpdk090_pmos1v"]),
        P("vdd", "1.8", "V", "supply"),
        P("vcm", "0.9", "V", "input common-mode"),
        P("itail", "2.7m", "A", "tail current (sets 5 mW budget)"),
        P("w", "20u", "m", "input device width"),
        P("wl", "20u", "m", "load device width"),
        P("l", "1u", "m", "length"),
        P("cl", "1p", "F", "load cap"),
        P("fstart", "1", "Hz", "AC start", group="Sim"),
        P("fstop", "1G", "Hz", "AC stop", group="Sim"),
        P("fdec", "20", "", "pts/decade", group="Sim"),
        *COMMON,
    ],
    build=_build_exp8,
    analyses=[{"name": "acs", "kind": "ac", "desc": "AC (diff or CM depending on input_mode)"},
              {"name": "icmr", "kind": "dc", "desc": "Input common-mode range sweep"}],
    plots=[
        {"title": "Differential gain", "analysis": "acs", "x": "@sweep", "y": ["om"],
         "ytransform": "db", "xscale": "log", "xlabel": "f (Hz)", "ylabel": "Gain (dB)"},
        {"title": "ICMR sweep", "analysis": "icmr", "x": "@sweep", "y": ["om", "op"],
         "xlabel": "Vcm (V)", "ylabel": "Vout (V)"},
    ],
    measure=_meas_exp8,
    notes="CMRR = Adm − Acm(dB): run once with input_mode=diff and once with "
          "input_mode=cm, then compute_cmrr from the two run ids.",
))


# =========================================================================== #
#  EXP 9 — Two-stage CMOS opamp; slew 10 V/µs, gain 200, GBP 10 MHz, ICMR, P<0.3 mW
# =========================================================================== #
def _build_exp9(p):
    n = p["device_n"]; pl = p["device_p"]; L = p["l"]
    s = _header(p)
    s += f"parameters vdd={p['vdd']} vcm={p['vcm']}\n"
    s += "Vdd (vdd 0) vsource dc=vdd\n"
    # --- bias string: Ibias -> diode M8, mirrors to tail (M5) and 2nd-stage sink (M7)
    s += (f"Ibias (vdd nb) isource dc={p['ibias']}\n"
          f"M8 (nb nb 0 0) {n} w={p['w_mirror']} l={L}\n"
          f"M5 (tail nb 0 0) {n} w={p['w_tail']} l={L}\n")
    # --- inputs: inp = pulse (slew) + ac; inm = ac complement (open loop)
    vcm = _num(p["vcm"]); vst = _num(p["vstep"])
    s += (f"Vinp (inp 0) vsource dc=vcm mag=0.5 type=pulse "
          f"val0={vcm - vst:.4g} val1={vcm + vst:.4g} period={p['tperiod']} "
          f"rise={p['tedge']} fall={p['tedge']} width={p['tpw']}\n"
          f"Vinm (inm 0) vsource dc=vcm mag=-0.5\n")
    # --- 1st stage: NMOS input pair, PMOS mirror load (output o2)
    s += (f"M1 (o1 inp tail 0) {n} w={p['w_in']} l={L}\n"
          f"M2 (o2 inm tail 0) {n} w={p['w_in']} l={L}\n"
          f"M3 (o1 o1 vdd vdd) {pl} w={p['w_load']} l={L}\n"
          f"M4 (o2 o1 vdd vdd) {pl} w={p['w_load']} l={L}\n")
    # --- 2nd stage: PMOS CS (M6) with NMOS current-sink load (M7), output out
    s += (f"M6 (out o2 vdd vdd) {pl} w={p['w_s2p']} l={L}\n"
          f"M7 (out nb 0 0) {n} w={p['w_s2n']} l={L}\n")
    # --- Miller compensation + load
    s += (f"Cc (o2 out) capacitor c={p['cc']}\n"
          f"CL (out 0) capacitor c={p['cl']}\n")
    s += _opts(p)
    s += f"acs ac start={p['fstart']} stop={p['fstop']} dec={p['fdec']}\n"
    s += f"icmr dc dev=Vinp param=dc start=0 stop={p['vdd']} step=0.02\n"
    stop = _num(p["tperiod"]) * 2
    s += f"slew tran stop={stop:.6g} errpreset=conservative\n"
    s += _opinfo()
    return s


def _meas_exp9(res):
    m = {}
    a = res.analyses
    if "acs" in a:
        d = a["acs"]["data"]; f = d.get(a["acs"]["sweep"]); mag = d.get("out")
        if f and mag:
            g = measure.ac_gain_bw(f, mag)
            m["dc_gain_vv"] = g.get("dc_gain_vv")
            m["dc_gain_db"] = g.get("dc_gain_db")
            m["gbw_hz"] = g.get("unity_gain_hz")
            cd = (a["acs"].get("cdata") or {}).get("out")
            if cd:
                ph = _phase_deg(cd)
                m.update(measure.phase_margin(f, mag, ph))
    if "slew" in a:
        d = a["slew"]["data"]; t = d.get(a["slew"]["sweep"]); vo = d.get("out")
        if t and vo:
            m.update(measure.slew_rate(t, vo))
    m["power_w"] = res.opinfo.get("total_power_w")
    m["devices"] = device_table(res.opinfo)
    return m


_reg(Experiment(
    id="9", title="Two-Stage CMOS Operational Amplifier", co="CO3",
    spec="VDD=1.8 V, Gain=200 (46 dB), GBP=10 MHz, SR=10 V/µs, CL=20 pF, "
         "ICMR+=1.6/ICMR-=0.8 V, Power<0.3 mW; + post-layout.",
    params=[
        P("device_n", "gpdk090_nmos2v", desc="NMOS", ptype="enum",
          choices=["gpdk090_nmos2v", "gpdk090_nmos1v"]),
        P("device_p", "gpdk090_pmos2v", desc="PMOS", ptype="enum",
          choices=["gpdk090_pmos2v", "gpdk090_pmos1v"]),
        P("vdd", "1.8", "V", "supply"),
        P("vcm", "0.9", "V", "input common-mode"),
        P("ibias", "15u", "A", "bias current"),
        P("w_in", "30u", "m", "input pair width"),
        P("w_load", "10u", "m", "1st-stage PMOS load width"),
        P("w_tail", "20u", "m", "tail mirror width"),
        P("w_mirror", "10u", "m", "bias diode width"),
        P("w_s2p", "60u", "m", "2nd-stage PMOS width"),
        P("w_s2n", "40u", "m", "2nd-stage NMOS width"),
        P("l", "1u", "m", "length"),
        P("cc", "3p", "F", "Miller compensation cap"),
        P("cl", "20p", "F", "load cap (spec)"),
        P("vstep", "0.1", "V", "slew step amplitude", group="Stimulus"),
        P("tperiod", "2u", "s", "step period", group="Stimulus"),
        P("tpw", "1u", "s", "pulse width", group="Stimulus"),
        P("tedge", "1n", "s", "edge time", group="Stimulus"),
        P("fstart", "1", "Hz", "AC start", group="Sim"),
        P("fstop", "1G", "Hz", "AC stop", group="Sim"),
        P("fdec", "20", "", "pts/decade", group="Sim"),
        *COMMON,
    ],
    build=_build_exp9,
    analyses=[{"name": "acs", "kind": "ac", "desc": "Open-loop gain / phase (GBP, PM)"},
              {"name": "icmr", "kind": "dc", "desc": "Input common-mode range"},
              {"name": "slew", "kind": "tran", "desc": "Slew-rate step response"}],
    plots=[
        {"title": "Open-loop gain", "analysis": "acs", "x": "@sweep", "y": ["out"],
         "ytransform": "db", "xscale": "log", "xlabel": "f (Hz)", "ylabel": "Gain (dB)"},
        {"title": "Open-loop phase", "analysis": "acs", "x": "@sweep", "y": ["out"],
         "ytransform": "phase", "xscale": "log", "xlabel": "f (Hz)", "ylabel": "Phase (°)"},
        {"title": "ICMR", "analysis": "icmr", "x": "@sweep", "y": ["out"],
         "xlabel": "Vcm (V)", "ylabel": "Vout (V)"},
        {"title": "Slew step", "analysis": "slew", "x": "time", "y": ["out", "inp"],
         "xlabel": "t (s)", "ylabel": "V"},
    ],
    measure=_meas_exp9,
    notes="Open-loop deck for gain/GBP/PM/ICMR/slew. For closed-loop slew, wire "
          "out->inm (unity feedback) via the vin sources. Layout+post-layout are GUI steps.",
))


# =========================================================================== #
#  EXP 10 — Open project: raw netlist passthrough
# =========================================================================== #
def _build_exp10(p):
    body = p.get("netlist", "").strip()
    if "simulator lang=spectre" in body:
        return body
    return _header(p) + body + "\n"


_reg(Experiment(
    id="10", title="Open Project (custom netlist)", co="CO1-CO4",
    spec="Bring your own Spectre deck; full access to every analysis.",
    params=[
        P("netlist", "// paste a full spectre deck here\n", desc="Spectre netlist body",
          ptype="multiline", group="Design"),
        *COMMON,
    ],
    build=_build_exp10,
    analyses=[], plots=[], measure=lambda res: {"devices": device_table(res.opinfo),
                                                "power_w": res.opinfo.get("total_power_w")},
    notes="Any analysis Spectre supports (pss/pnoise/hb/stb/pz/sp/montecarlo…).",
))


# --------------------------------------------------------------------------- #
def list_experiments():
    return [{"id": e.id, "title": e.title, "co": e.co, "spec": e.spec,
             "n_params": len(e.params), "analyses": [a["name"] for a in e.analyses]}
            for e in REG.values()]


def get(exp_id: str) -> Experiment | None:
    return REG.get(str(exp_id))
