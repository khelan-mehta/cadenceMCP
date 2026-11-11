"""Design templates as *data* (not tools).

Each template is a parameterized Spectre netlist ({param} placeholders) plus its
default params, suggested tunable knobs, and a default measure set. Claude loads
one, edits params, and feeds it to the general `simulate` / `optimize` primitives.
This is how new circuits (incl. the VTC-ADC) get done without new Python tools.
"""
from __future__ import annotations

from . import config
from .digital.cells import CELL_SUBCKTS

MODEL = config.PDK_MODEL_INCLUDE


def _hdr(corner="NN"):
    return (f"simulator lang=spectre\nglobal 0\n"
            f'include "{MODEL}" section={corner}\n')


TEMPLATES = {
    "mos_iv": {
        "desc": "MOS I-V characterization -> VT0, Kn, lambda, fT (Exp 2).",
        "netlist": _hdr() +
            "parameters vgs={vgs} vds={vdd} vbs={vbs}\n"
            "Vg (g 0) vsource dc=vgs\nVd (d 0) vsource dc=vds\nVb (b 0) vsource dc=vbs\n"
            "M0 (d g 0 b) {device} w={w} l={l}\n"
            "simOpt options temp=27 save=allpub\n"
            "idvgs dc param=vgs start=0 stop={vdd} step=0.02\n"
            "idvds dc param=vds start=0 stop={vdd} step=0.02\n"
            "oppoint dc\nopinfo info what=oppoint where=file file=\"op.info\"\n",
        "params": {"device": "gpdk090_nmos1v", "w": "1u", "l": "100n",
                   "vdd": "1.8", "vgs": "0.9", "vbs": "0"},
        "knobs": ["w"],
        "measures": [
            {"name": "vt0", "metric": "vt0", "analysis": "idvgs", "signal": "Vd:p", "transform": "abs"},
            {"name": "kn", "metric": "kn", "analysis": "idvgs", "signal": "Vd:p", "transform": "abs"},
            {"name": "lambda", "metric": "lambda", "analysis": "idvds", "signal": "Vd:p", "transform": "abs"},
            {"name": "gm_M0", "metric": "device", "instance": "M0", "param": "gm"},
            {"name": "ft_M0", "metric": "device", "instance": "M0", "param": "fug"},
        ],
    },
    "cs_amp": {
        "desc": "Common-source amplifier (resistive load). AC gain/BW/PM + power.",
        "netlist": _hdr() +
            "Vdd (vdd 0) vsource dc={vdd}\n"
            "Vin (in 0) vsource dc={vin} mag=1 type=sine sinedc={vin} ampl={vac} freq={fin}\n"
            "M0 (out in 0 0) {device} w={w} l={l}\n"
            "RD (vdd out) resistor r={rd}\nCL (out 0) capacitor c={cl}\n"
            "simOpt options temp=27 save=allpub\n"
            "dcsw dc dev=Vin param=dc start=0 stop={vdd} step=0.01\n"
            "acs ac start=1 stop=1e9 dec=20\n"
            "trans tran stop=5u errpreset=conservative\n"
            "oppoint dc\nopinfo info what=oppoint where=file file=\"op.info\"\n",
        "params": {"device": "gpdk090_nmos2v", "w": "10u", "l": "1u", "rd": "10k",
                   "vdd": "1.8", "vin": "0.7", "vac": "5m", "fin": "1M", "cl": "100f"},
        "knobs": ["w", "rd"],
        "measures": [
            {"name": "gain_db", "metric": "gain_db", "analysis": "acs", "signal": "out"},
            {"name": "bandwidth_hz", "metric": "bandwidth_hz", "analysis": "acs", "signal": "out"},
            {"name": "phase_margin_deg", "metric": "phase_margin_deg", "analysis": "acs", "signal": "out"},
            {"name": "power", "metric": "power"},
        ],
    },
    "diff_amp": {
        "desc": "NMOS diff pair, PMOS mirror load, tail current. Differential gain.",
        "netlist": _hdr() +
            "Vdd (vdd 0) vsource dc={vdd}\n"
            "Vip (inp 0) vsource dc={vcm} mag=0.5\nVin (inm 0) vsource dc={vcm} mag=-0.5\n"
            "Itail (tail 0) isource dc={itail}\n"
            "M1 (op inp tail 0) {ndev} w={w} l={l}\nM2 (om inm tail 0) {ndev} w={w} l={l}\n"
            "M3 (op op vdd vdd) {pdev} w={wl} l={l}\nM4 (om op vdd vdd) {pdev} w={wl} l={l}\n"
            "CL (om 0) capacitor c={cl}\n"
            "simOpt options temp=27 save=allpub\n"
            "acs ac start=1 stop=1e9 dec=20\n"
            "oppoint dc\nopinfo info what=oppoint where=file file=\"op.info\"\n",
        "params": {"ndev": "gpdk090_nmos2v", "pdev": "gpdk090_pmos2v", "vdd": "1.8",
                   "vcm": "0.9", "itail": "2.7m", "w": "20u", "wl": "20u", "l": "1u", "cl": "1p"},
        "knobs": ["w", "wl", "l"],
        "measures": [
            {"name": "gain_db", "metric": "gain_db", "analysis": "acs", "signal": "om"},
            {"name": "bandwidth_hz", "metric": "bandwidth_hz", "analysis": "acs", "signal": "om"},
            {"name": "power", "metric": "power"},
        ],
    },
    "inverter_cell": {
        "desc": "Transistor-level CMOS inverter: propagation delay + switching.",
        "netlist": _hdr() + CELL_SUBCKTS + "\n" +
            "Vdd (vdd 0) vsource dc=1.0\n"
            "Vin (a 0) vsource type=pulse val0=0 val1=1.0 period=2n rise=20p fall=20p width=1n\n"
            "X0 (a y vdd 0) INV\nCL (y 0) capacitor c={cl}\n"
            "simOpt options temp=27 save=allpub\n"
            "trans tran stop=4n step=2p errpreset=conservative\n",
        "params": {"cl": "8f"},
        "knobs": ["cl"],
        "measures": [
            {"name": "tpHL_ps", "metric": "delay", "analysis": "trans", "from": "a", "to": "y",
             "level": 0.5, "edge_from": "rising", "edge_to": "falling"},
        ],
    },
    "rc_lowpass": {
        "desc": "Ideal 1st-order RC low-pass (series R, shunt C). -3dB cutoff + passband gain.",
        "netlist": "simulator lang=spectre\nglobal 0\n"
            "Vin (in 0) vsource dc=0 mag=1 type=dc\n"
            "R0 (in out) resistor r={r}\nC0 (out 0) capacitor c={c}\n"
            "acs ac start=0.1 stop=1e10 dec=20\n",
        "params": {"r": "1.5915k", "c": "100p"},
        "knobs": ["r", "c"],
        "measures": [
            {"name": "f0", "metric": "bandwidth_hz", "analysis": "acs", "signal": "out"},
            {"name": "gain_dc", "metric": "gain_db", "analysis": "acs", "signal": "out"},
        ],
    },
    "vtc_adc": {
        "desc": "VTC (current-starved delay cell) + TDC (buffer delay line): Vin->time->code.",
        "netlist": _hdr() + CELL_SUBCKTS + "\n" +
            "Vdd (vdd 0) vsource dc=1.0\nVin (vc 0) vsource dc={vin}\n"
            "Vtrig (trig 0) vsource type=pulse val0=0 val1=1.0 rise=10p fall=10p delay=1n width=8n period=20n\n"
            "M1p (mid trig vdd vdd) gpdk090_pmos1v w=1u l=100n\n"
            "M1n (mid trig ns 0) gpdk090_nmos1v w=0.5u l=100n\n"
            "Ms (ns vc 0 0) gpdk090_nmos1v w={wstarve} l=100n\n"
            "M2p (stop mid vdd vdd) gpdk090_pmos1v w=1u l=100n\n"
            "M2n (stop mid 0 0) gpdk090_nmos1v w=0.5u l=100n\n"
            "Cvtc (mid 0) capacitor c={cvtc}\n"
            "Xa0 (trig m0 vdd 0) INV\nXb0 (m0 b0 vdd 0) INV\nCl0 (b0 0) capacitor c=5f\n"
            "Xa1 (b0 m1 vdd 0) INV\nXb1 (m1 b1 vdd 0) INV\nCl1 (b1 0) capacitor c=5f\n"
            "simOpt options temp=27 save=allpub\n"
            "tr tran stop=6n step=2p errpreset=conservative\n",
        "params": {"vin": "0.5", "wstarve": "2u", "cvtc": "40f"},
        "knobs": ["wstarve", "cvtc"],
        "measures": [
            {"name": "vtc_delay", "metric": "delay", "analysis": "tr", "from": "trig", "to": "stop",
             "level": 0.5, "edge_from": "rising", "edge_to": "rising"},
        ],
    },
}


def list_templates() -> list:
    return [{"name": n, "desc": t["desc"], "params": list(t["params"].keys()),
             "knobs": t["knobs"]} for n, t in TEMPLATES.items()]


def get_template(name: str) -> dict | None:
    t = TEMPLATES.get(name)
    if not t:
        return None
    return {"name": name, **t}
