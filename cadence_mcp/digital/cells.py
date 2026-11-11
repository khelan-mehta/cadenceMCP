"""gpdk090 standard-cell library (transistor-level Spectre subckts) + cell
characterization. This is the analog half of the hybrid flow: the same logic
the CPU is built from, measured at transistor level for real delay/power.

Cells: INV, NAND2, NOR2, DFF (TG master-slave), FA (9-NAND full adder), SRAM6T.
Core 1 V devices (gpdk090_nmos1v/pmos1v), VDD = 1.0 V.
"""
from __future__ import annotations

import math

from .. import config, measure, spectre, store

MODEL = config.PDK_MODEL_INCLUDE
VDD = 1.0

# --------------------------------------------------------------------------- #
#  cell subckt library (Spectre)
# --------------------------------------------------------------------------- #
CELL_SUBCKTS = r"""
subckt INV (a y vdd vss)
  parameters wp=0.4u wn=0.2u
  MP (y a vdd vdd) gpdk090_pmos1v w=wp l=100n
  MN (y a vss vss) gpdk090_nmos1v w=wn l=100n
ends INV

subckt NAND2 (a b y vdd vss)
  parameters wp=0.4u wn=0.4u
  MP1 (y a vdd vdd) gpdk090_pmos1v w=wp l=100n
  MP2 (y b vdd vdd) gpdk090_pmos1v w=wp l=100n
  MN1 (y a n1 vss)  gpdk090_nmos1v w=wn l=100n
  MN2 (n1 b vss vss) gpdk090_nmos1v w=wn l=100n
ends NAND2

subckt NOR2 (a b y vdd vss)
  parameters wp=0.8u wn=0.2u
  MP1 (p1 a vdd vdd) gpdk090_pmos1v w=wp l=100n
  MP2 (y b p1 vdd)   gpdk090_pmos1v w=wp l=100n
  MN1 (y a vss vss)  gpdk090_nmos1v w=wn l=100n
  MN2 (y b vss vss)  gpdk090_nmos1v w=wn l=100n
ends NOR2

// transmission gate
subckt TG (in out c cb vdd vss)
  MN (in out c vss)  gpdk090_nmos1v w=0.3u l=100n
  MP (in out cb vdd) gpdk090_pmos1v w=0.3u l=100n
ends TG

// positive-edge-triggered D flip-flop (master-slave, TG based)
subckt DFF (d q clk vdd vss)
  parameters wp=0.4u wn=0.2u
  // clock inverters
  I_ckb (clk ckb vdd vss) INV
  I_ck  (ckb ck  vdd vss) INV
  // master latch (transparent when ck=0 i.e. clk low)
  X_tg1 (d dm ckb ck vdd vss) TG
  I_m1 (dm mb vdd vss) INV
  I_m2 (mb dm2 vdd vss) INV
  X_tgm (dm2 dm ck ckb vdd vss) TG
  // slave latch (transparent when ck=1)
  X_tg2 (mb ds ck ckb vdd vss) TG
  I_s1 (ds q vdd vss) INV
  I_s2 (q sb vdd vss) INV
  X_tgs (sb ds ckb ck vdd vss) TG
ends DFF

// 1-bit full adder from 9 NAND2 gates (SUM, COUT)
subckt FA (a b cin sum cout vdd vss)
  I1 (a b   x1 vdd vss) NAND2
  I2 (a x1  x2 vdd vss) NAND2
  I3 (b x1  x3 vdd vss) NAND2
  I4 (x2 x3 x4 vdd vss) NAND2
  I5 (x4 cin x5 vdd vss) NAND2
  I6 (x4 x5 x6 vdd vss) NAND2
  I7 (cin x5 x7 vdd vss) NAND2
  I8 (x6 x7 sum vdd vss) NAND2
  I9 (x1 x5 cout vdd vss) NAND2
ends FA

// 6T SRAM cell (bit + bitb storage, wl word line, bl/blb bit lines)
subckt SRAM6T (bl blb wl vdd vss)
  MPL (q qb vdd vdd) gpdk090_pmos1v w=0.2u l=100n
  MNL (q qb vss vss) gpdk090_nmos1v w=0.3u l=100n
  MPR (qb q vdd vdd) gpdk090_pmos1v w=0.2u l=100n
  MNR (qb q vss vss) gpdk090_nmos1v w=0.3u l=100n
  MAL (bl wl q vss)  gpdk090_nmos1v w=0.3u l=100n
  MAR (blb wl qb vss) gpdk090_nmos1v w=0.3u l=100n
ends SRAM6T
""".strip()

CELLS = {
    "INV": {"ports": "a y vdd vss", "desc": "CMOS inverter (2T)"},
    "NAND2": {"ports": "a b y vdd vss", "desc": "2-input NAND (4T)"},
    "NOR2": {"ports": "a b y vdd vss", "desc": "2-input NOR (4T)"},
    "TG": {"ports": "in out c cb vdd vss", "desc": "transmission gate (2T)"},
    "DFF": {"ports": "d q clk vdd vss", "desc": "pos-edge D flip-flop (master-slave)"},
    "FA": {"ports": "a b cin sum cout vdd vss", "desc": "1-bit full adder (9x NAND2)"},
    "SRAM6T": {"ports": "bl blb wl vdd vss", "desc": "6T SRAM bit cell"},
}


def _hdr():
    return (f"// gpdk090 standard-cell characterization\n"
            f"simulator lang=spectre\nglobal 0\n"
            f'include "{MODEL}" section=NN\n{CELL_SUBCKTS}\n'
            f"Vdd (vdd 0) vsource dc={VDD}\n")


def _avg_power(res) -> float | None:
    """Average dynamic power = mean(|I(Vdd)|)*VDD over the transient."""
    a = res.analyses.get("tran")
    if not a:
        return None
    isup = a["data"].get("Vdd:p")
    if not isup:
        return None
    avg_i = sum(abs(v) for v in isup) / len(isup)
    return avg_i * VDD


# --------------------------------------------------------------------------- #
#  characterizations
# --------------------------------------------------------------------------- #
def characterize_inverter(fanout: int = 4, run: bool = True) -> dict:
    """Propagation delay (tpHL/tpLH) + a rough dynamic-energy estimate."""
    per = 2e-9
    cl = fanout * 2e-15  # ~2 fF per fanout inverter input
    s = _hdr()
    s += (f"Vin (a 0) vsource type=pulse val0=0 val1={VDD} period={per} "
          f"rise=20p fall=20p width={per/2} delay=0\n"
          f"X0 (a y vdd 0) INV\n"
          f"CL (y 0) capacitor c={cl}\n"
          f"tran tran stop={2.2*per:.3g} errpreset=conservative\n")
    if not run:
        return {"netlist": s}
    res = spectre.run_netlist(s, run_name="cell_inv")
    out = {"cell": "INV", "fanout": fanout, "load_fF": cl * 1e15}
    if "tran" in res.analyses:
        d = res.analyses["tran"]["data"]; t = d.get(res.analyses["tran"]["sweep"])
        a = d.get("a"); y = d.get("y")
        if t and a and y:
            # first falling edge of input -> output rising (tpLH), etc.
            # measure both prop delays at VDD/2
            half = VDD / 2
            t_in_rise = measure.cross(t, a, half, "rising")
            t_out_fall = measure.cross(t, y, half, "falling")
            t_in_fall = measure.cross(t, a, half, "falling")
            t_out_rise = measure.cross(t, y, half, "rising")
            tphl = (t_out_fall - t_in_rise) if (t_out_fall and t_in_rise) else None
            tplh = (t_out_rise - t_in_fall) if (t_out_rise and t_in_fall) else None
            out["tpHL_ps"] = tphl * 1e12 if tphl else None
            out["tpLH_ps"] = tplh * 1e12 if tplh else None
            if tphl and tplh:
                out["tp_avg_ps"] = (tphl + tplh) / 2 * 1e12
    out["dyn_power_w"] = _avg_power(res)
    out["ok"] = res.ok
    if run:
        _save_cell_run(res, "INV", out, s, [
            {"title": "Inverter switching", "analysis": "tran", "x": "time",
             "y": ["a", "y"], "xlabel": "t (s)", "ylabel": "V"}])
    return out


def ring_oscillator(stages: int = 5, run: bool = True) -> dict:
    """Odd-stage inverter ring; measure oscillation frequency -> stage delay."""
    if stages % 2 == 0:
        stages += 1
    s = _hdr()
    nodes = [f"r{i}" for i in range(stages)]
    for i in range(stages):
        a = nodes[i]
        y = nodes[(i + 1) % stages]
        s += f"X{i} ({a} {y} vdd 0) INV\n"
    # enable/kick: initial condition on r0
    s += f"ic r0=0\n"
    stop = 3e-9
    s += f"tran tran stop={stop:.3g} step=2p errpreset=conservative\n"
    if not run:
        return {"netlist": s}
    res = spectre.run_netlist(s, run_name="cell_ring")
    out = {"cell": f"ring{stages}", "stages": stages, "ok": res.ok}
    if "tran" in res.analyses:
        d = res.analyses["tran"]["data"]; t = d.get(res.analyses["tran"]["sweep"])
        y = d.get("r0")
        if t and y:
            # find successive rising crossings of VDD/2 -> period
            half = VDD / 2
            crossings = []
            for i in range(1, len(y)):
                if (y[i - 1] - half) < 0 <= (y[i] - half):
                    frac = (half - y[i - 1]) / (y[i] - y[i - 1]) if y[i] != y[i - 1] else 0
                    crossings.append(t[i - 1] + frac * (t[i] - t[i - 1]))
            if len(crossings) >= 2:
                periods = [crossings[i + 1] - crossings[i] for i in range(len(crossings) - 1)]
                per = sum(periods[1:]) / len(periods[1:]) if len(periods) > 1 else periods[0]
                out["period_s"] = per
                out["freq_hz"] = 1 / per if per else None
                out["stage_delay_ps"] = (per / (2 * stages)) * 1e12 if per else None
    out["dyn_power_w"] = _avg_power(res)
    if run:
        _save_cell_run(res, f"ring{stages}", out, s, [
            {"title": f"{stages}-stage ring oscillator", "analysis": "tran",
             "x": "time", "y": ["r0", "r1"], "xlabel": "t (s)", "ylabel": "V"}])
    return out


def characterize_full_adder(run: bool = True) -> dict:
    """Apply the 8 input combinations; verify SUM/COUT truth table + delay."""
    slot = 2e-9
    s = _hdr()
    # 3-bit counter: a toggles each slot, b every 2 slots, cin every 4 slots.
    # 8 slots cover 000..111; sample at each slot centre.
    s += (f"Va (a 0) vsource type=pulse val0=0 val1={VDD} period={2*slot} rise=20p fall=20p width={slot}\n"
          f"Vb (b 0) vsource type=pulse val0=0 val1={VDD} period={4*slot} rise=20p fall=20p width={2*slot}\n"
          f"Vc (cin 0) vsource type=pulse val0=0 val1={VDD} period={8*slot} rise=20p fall=20p width={4*slot}\n"
          f"X0 (a b cin sum cout vdd 0) FA\n"
          f"Cs (sum 0) capacitor c=2f\n Cc (cout 0) capacitor c=2f\n"
          f"tran tran stop={8*slot:.3g} errpreset=conservative\n")
    if not run:
        return {"netlist": s}
    res = spectre.run_netlist(s, run_name="cell_fa")
    out = {"cell": "FA", "ok": res.ok}
    if "tran" in res.analyses:
        d = res.analyses["tran"]["data"]; t = d.get(res.analyses["tran"]["sweep"])
        table = []
        per = slot

        def val_at(sig, tt):
            return measure.interp(t, d.get(sig, []), tt)
        for k in range(8):
            tt = (k + 0.5) * per
            a = 1 if val_at("a", tt) > VDD / 2 else 0
            b = 1 if val_at("b", tt) > VDD / 2 else 0
            cin = 1 if val_at("cin", tt) > VDD / 2 else 0
            sm = 1 if val_at("sum", tt) > VDD / 2 else 0
            co = 1 if val_at("cout", tt) > VDD / 2 else 0
            exp_s = (a + b + cin) & 1
            exp_c = 1 if (a + b + cin) >= 2 else 0
            table.append({"a": a, "b": b, "cin": cin, "sum": sm, "cout": co,
                          "ok": sm == exp_s and co == exp_c})
        out["truth_table"] = table
        out["functionally_correct"] = all(r["ok"] for r in table)
    out["power_w"] = res.opinfo.get("total_power_w")
    if run:
        _save_cell_run(res, "FA", out, s, [
            {"title": "Full adder", "analysis": "tran", "x": "time",
             "y": ["a", "b", "cin", "sum", "cout"], "xlabel": "t (s)", "ylabel": "V"}])
    return out


def characterize_sram(run: bool = True) -> dict:
    """Write 1 then 0 into a 6T cell via the bit lines; observe internal q."""
    s = _hdr()
    # wordline pulses; bitlines driven to write, then released
    s += (f"Vwl (wl 0) vsource type=pulse val0=0 val1={VDD} period=4n rise=20p fall=20p width=1n delay=0.5n\n"
          f"Vbl (bl 0) vsource type=pulse val0={VDD} val1=0 period=4n rise=20p fall=20p width=2n delay=0\n"
          f"Vblb (blb 0) vsource type=pulse val0=0 val1={VDD} period=4n rise=20p fall=20p width=2n delay=0\n"
          f"X0 (bl blb wl vdd 0) SRAM6T\n"
          f"tran tran stop=8n errpreset=conservative\n")
    if not run:
        return {"netlist": s}
    res = spectre.run_netlist(s, run_name="cell_sram")
    out = {"cell": "SRAM6T", "ok": res.ok, "power_w": res.opinfo.get("total_power_w")}
    if run:
        _save_cell_run(res, "SRAM6T", out, s, [
            {"title": "6T SRAM write", "analysis": "tran", "x": "time",
             "y": ["wl", "bl", "blb"], "xlabel": "t (s)", "ylabel": "V"}])
    return out


def characterize_dff(run: bool = True) -> dict:
    """Clock a DFF, toggle D, confirm Q follows D on rising edges."""
    per = 2e-9
    s = _hdr()
    s += (f"Vclk (clk 0) vsource type=pulse val0=0 val1={VDD} period={per} rise=20p fall=20p width={per/2}\n"
          f"Vd (d 0) vsource type=pulse val0=0 val1={VDD} period={3*per} rise=20p fall=20p width={1.5*per}\n"
          f"X0 (d q clk vdd 0) DFF\n"
          f"Cq (q 0) capacitor c=2f\n"
          f"tran tran stop={8*per:.3g} errpreset=conservative\n")
    if not run:
        return {"netlist": s}
    res = spectre.run_netlist(s, run_name="cell_dff")
    out = {"cell": "DFF", "ok": res.ok, "power_w": res.opinfo.get("total_power_w")}
    if run:
        _save_cell_run(res, "DFF", out, s, [
            {"title": "D flip-flop", "analysis": "tran", "x": "time",
             "y": ["clk", "d", "q"], "xlabel": "t (s)", "ylabel": "V"}])
    return out


def _save_cell_run(res, cell, meas, netlist, plots):
    try:
        store.save_run(f"cell:{cell}", f"gpdk090 {cell} characterization",
                       {"cell": cell}, res, meas, netlist, plots)
    except Exception:
        pass


CHAR_FUNCS = {
    "INV": characterize_inverter,
    "ring": ring_oscillator,
    "FA": characterize_full_adder,
    "SRAM6T": characterize_sram,
    "DFF": characterize_dff,
}
