"""gpdk090 (90 nm) device catalog.

Instance parameters that the schematics expose and the MCP lets you tweak, plus
the operating-point quantities Spectre reports for each device. Device subckt
names were confirmed live from gpdk090_mos.scs (all BSIM3v3).
"""
from __future__ import annotations

# unit multipliers understood by the netlist writer / UI
UNITS = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3,
         "k": 1e3, "K": 1e3, "M": 1e6, "g": 1e9, "G": 1e9}

MOS_INSTANCE_PARAMS = [
    {"name": "w", "unit": "m", "default": "1u", "min": "120n", "max": "500u",
     "desc": "channel width"},
    {"name": "l", "unit": "m", "default": "100n", "min": "100n", "max": "10u",
     "desc": "channel length (min 100n for 1v, 100n core)"},
    {"name": "m", "unit": "", "default": "1", "min": "1", "max": "256",
     "desc": "device multiplier (parallel fingers)"},
]

# Operating-point quantities Spectre saves for a MOS (save=allpub / .op)
MOS_OP_QUANTITIES = [
    "id", "vgs", "vds", "vth", "vdsat", "gm", "gds", "gmbs",
    "cgs", "cgd", "cdb", "csb", "region", "ron", "gmoverid",
]

DEVICES = {
    "gpdk090_nmos1v": {
        "type": "nmos", "model": "bsim3v3", "rail": "1.0 V core",
        "desc": "Core 1 V NMOS (standard-Vt). Default driver for gain stages, "
                "mirrors, diff pairs.",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_pmos1v": {
        "type": "pmos", "model": "bsim3v3", "rail": "1.0 V core",
        "desc": "Core 1 V PMOS (standard-Vt). Loads, current sources, PMOS diff loads.",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_nmos2v": {
        "type": "nmos", "model": "bsim3v3", "rail": "2.5 V thick-oxide IO",
        "desc": "Thick-oxide 2 V NMOS. Use for the 1.8 V-rail labs (Exp 3, 8, 9).",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_pmos2v": {
        "type": "pmos", "model": "bsim3v3", "rail": "2.5 V thick-oxide IO",
        "desc": "Thick-oxide 2 V PMOS. 1.8 V-rail loads / current sources.",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_nmos1v_hvt": {
        "type": "nmos", "model": "bsim3v3", "rail": "1.0 V core (high-Vt)",
        "desc": "High-Vt core NMOS (lower leakage, higher threshold).",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_pmos1v_hvt": {
        "type": "pmos", "model": "bsim3v3", "rail": "1.0 V core (high-Vt)",
        "desc": "High-Vt core PMOS.",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "gpdk090_nmos1v_nat": {
        "type": "nmos", "model": "bsim3v3", "rail": "1.0 V core (native)",
        "desc": "Native (near-zero-Vt) core NMOS.",
        "params": MOS_INSTANCE_PARAMS, "op": MOS_OP_QUANTITIES, "terminals": "D G S B",
    },
    "resistor": {
        "type": "passive", "model": "spectre resistor", "rail": "-",
        "desc": "Ideal Spectre resistor (use for RSET / load R / degeneration).",
        "params": [{"name": "r", "unit": "ohm", "default": "1k", "min": "1",
                    "max": "10M", "desc": "resistance"}],
        "op": ["i", "v", "pwr"], "terminals": "+ -",
    },
    "capacitor": {
        "type": "passive", "model": "spectre capacitor", "rail": "-",
        "desc": "Ideal Spectre capacitor (load CL / Miller Cc).",
        "params": [{"name": "c", "unit": "F", "default": "1p", "min": "1f",
                    "max": "100n", "desc": "capacitance"}],
        "op": ["i", "v"], "terminals": "+ -",
    },
    "vsource": {
        "type": "source", "model": "spectre vsource", "rail": "-",
        "desc": "Voltage source. type=dc|sine|pulse; ac=1 for AC stimulus.",
        "params": [
            {"name": "dc", "unit": "V", "default": "0", "min": "-5", "max": "5",
             "desc": "DC value"},
            {"name": "mag", "unit": "V", "default": "1", "min": "0", "max": "5",
             "desc": "AC magnitude (small-signal)"},
        ],
        "op": ["i", "pwr"], "terminals": "+ -",
    },
    "isource": {
        "type": "source", "model": "spectre isource", "rail": "-",
        "desc": "Current source (tail current, bias).",
        "params": [{"name": "dc", "unit": "A", "default": "10u", "min": "0",
                    "max": "10m", "desc": "DC current"}],
        "op": ["v", "pwr"], "terminals": "+ -",
    },
}


def list_devices() -> list[dict]:
    out = []
    for name, d in DEVICES.items():
        out.append({"name": name, "type": d["type"], "rail": d["rail"], "desc": d["desc"]})
    return out


def get_device(name: str) -> dict | None:
    d = DEVICES.get(name)
    if d is None:
        return None
    return {"name": name, **d}
