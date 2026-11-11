"""Low-power VTC-based ADC = Voltage-to-Time Converter (VTC) + Time-to-Digital
Converter (TDC), integrated.

Why lower power than a conventional ADC: no high-gain comparators, no precise
reference ladder, no clocked capacitor DAC. The VTC is a current-starved delay
cell (a few transistors); the TDC is a digital delay line + samplers — both
scale with process and run on a single low supply.

Builds the netlists, simulates the end-to-end transfer (Vin -> code), generates
schematic diagrams (SVG), authors real Virtuoso schematic cellviews via SKILL,
and returns the working-directory paths (host + guest).
"""
from __future__ import annotations

from pathlib import Path

from .. import config, measure, skill, spectre
from ..digital.cells import CELL_SUBCKTS

MODEL = config.PDK_MODEL_INCLUDE
GUEST_LIB = "/home/work/mcp_designs"                       # persistent OA lib on VM
HOST_DIR = config.PROJECT_ROOT / "designs" / "vtc_adc"     # artifacts on the host


# --------------------------------------------------------------------------- #
#  netlists
# --------------------------------------------------------------------------- #
def integrated_netlist(vin: float, n_stages: int = 10, vdd: float = 1.0) -> str:
    """VTC (current-starved delay cell) driving a TDC (buffer delay line).

    A trigger edge launches the TDC delay line (START) and, in parallel, the VTC,
    whose Vin-dependent delay produces the STOP edge. Sampling the delay-line taps
    at STOP gives a thermometer code proportional to the VTC delay, i.e. to Vin.
    """
    s = [
        "// VTC-ADC : voltage-to-time + time-to-digital (gpdk090)",
        "simulator lang=spectre", "global 0",
        f'include "{MODEL}" section=NN',
        CELL_SUBCKTS,
        f"Vdd (vdd 0) vsource dc={vdd}",
        f"Vin (vc 0) vsource dc={vin}                 // analog input (controls VTC delay)",
        "Vtrig (trig 0) vsource type=pulse val0=0 val1=%g rise=10p fall=10p delay=1n width=8n period=20n" % vdd,
        "// ---- VTC: current-starved inverter, discharge set by Vin ----",
        "M1p (mid trig vdd vdd) gpdk090_pmos1v w=1u l=100n",
        "M1n (mid trig ns 0)    gpdk090_nmos1v w=0.5u l=100n",
        "Ms  (ns  vc  0   0)    gpdk090_nmos1v w=2u l=100n",
        "M2p (stop mid vdd vdd) gpdk090_pmos1v w=1u l=100n",
        "M2n (stop mid 0 0)     gpdk090_nmos1v w=0.5u l=100n",
        "Cvtc (mid 0) capacitor c=40f",
        "// ---- TDC: buffer delay line launched by the same trigger (START) ----",
    ]
    node = "trig"
    for i in range(n_stages):
        mid = f"m{i}"; b = f"b{i}"
        s.append(f"Xa{i} ({node} {mid} vdd 0) INV")
        s.append(f"Xb{i} ({mid} {b} vdd 0) INV")
        s.append(f"Cl{i} ({b} 0) capacitor c=5f")
        node = b
    s.append("simOpt options temp=27 save=allpub")
    s.append("tr tran stop=6n step=2p errpreset=conservative")
    return "\n".join(s)


# --------------------------------------------------------------------------- #
#  simulate the end-to-end ADC transfer
# --------------------------------------------------------------------------- #
def simulate_adc(vin_list=None, n_stages: int = 10, vdd: float = 1.0) -> dict:
    vin_list = vin_list or [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
    rows = []
    for vin in vin_list:
        res = spectre.run_netlist(integrated_netlist(vin, n_stages, vdd),
                                  run_name="vtc_adc")
        a = res.analyses.get("tr")
        if not a:
            rows.append({"vin": vin, "error": True})
            continue
        d = a["data"]; t = d.get(a["sweep"])
        t_start = measure.cross(t, d.get("trig", []), vdd / 2, "rising")
        t_stop = measure.cross(t, d.get("stop", []), vdd / 2, "rising")
        delay = (t_stop - t_start) if (t_start and t_stop) else None
        code = None
        if t_stop:
            code = sum(1 for i in range(n_stages)
                       if measure.interp(t, d.get(f"b{i}", []), t_stop) > vdd / 2)
        rows.append({"vin": vin,
                     "vtc_delay_ps": delay * 1e12 if delay else None,
                     "tdc_code": code})
    codes = [r["tdc_code"] for r in rows if r.get("tdc_code") is not None]
    up = all(codes[i] <= codes[i + 1] for i in range(len(codes) - 1)) if codes else False
    dn = all(codes[i] >= codes[i + 1] for i in range(len(codes) - 1)) if codes else False
    return {"rows": rows, "n_stages": n_stages, "monotonic": (up or dn),
            "direction": "increasing" if up and not dn else ("decreasing" if dn else "non-monotonic"),
            "lsb_note": "1 code ~= 2 inverter delays (~80-160 ps); higher Vin -> less delay -> lower code"}


# --------------------------------------------------------------------------- #
#  schematic diagrams (SVG) — human-viewable, saved on host
# --------------------------------------------------------------------------- #
def _svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'font-family="monospace" font-size="13">'
            f'<rect width="{w}" height="{h}" fill="#0d1117"/>'
            f'<text x="14" y="24" fill="#58a6ff" font-size="16">{title}</text>{body}</svg>')


def _fet(x, y, label, kind):
    col = "#7ee787" if kind == "n" else "#f0883e"
    return (f'<g stroke="{col}" stroke-width="2" fill="none">'
            f'<line x1="{x-22}" y1="{y}" x2="{x-6}" y2="{y}"/>'
            f'<line x1="{x-6}" y1="{y-16}" x2="{x-6}" y2="{y+16}"/>'
            f'<line x1="{x}" y1="{y-16}" x2="{x}" y2="{y+16}"/>'
            f'<line x1="{x}" y1="{y-16}" x2="{x+16}" y2="{y-28}"/>'
            f'<line x1="{x}" y1="{y+16}" x2="{x+16}" y2="{y+28}"/></g>'
            f'<text x="{x-4}" y="{y+34}" fill="#e6edf3" font-size="11">{label}</text>')


def vtc_svg():
    b = (_fet(140, 120, "M1p pmos", "p") + _fet(140, 210, "M1n nmos", "n")
         + _fet(140, 300, "Ms (Vin)", "n") + _fet(300, 165, "M2p", "p")
         + _fet(300, 250, "M2n", "n")
         + '<text x="40" y="120" fill="#8b949e">VDD</text>'
         + '<text x="40" y="300" fill="#8b949e">Vin→</text>'
         + '<text x="360" y="200" fill="#8b949e">→STOP</text>'
         + '<text x="14" y="360" fill="#8b949e">Current-starved inverter: Ms(Vin) sets discharge current → delay ∝ f(Vin)</text>')
    return _svg(560, 380, b, "VTC — Voltage-to-Time Converter")


def tdc_svg(n=6):
    b = '<text x="14" y="70" fill="#8b949e">Buffer delay line; DFFs sample taps on STOP → thermometer code</text>'
    x = 60
    for i in range(n):
        b += (f'<rect x="{x}" y="110" width="46" height="34" fill="none" stroke="#7ee787" stroke-width="2"/>'
              f'<text x="{x+8}" y="132" fill="#e6edf3" font-size="11">B{i}</text>'
              f'<line x1="{x+46}" y1="127" x2="{x+60}" y2="127" stroke="#7ee787" stroke-width="2"/>'
              f'<rect x="{x+6}" y="180" width="34" height="34" fill="none" stroke="#58a6ff" stroke-width="2"/>'
              f'<text x="{x+10}" y="202" fill="#e6edf3" font-size="10">DFF</text>'
              f'<line x1="{x+23}" y1="144" x2="{x+23}" y2="180" stroke="#8b949e" stroke-width="1"/>')
        x += 74
    b += '<text x="14" y="250" fill="#8b949e">STOP (from VTC) clocks all DFFs simultaneously</text>'
    return _svg(x + 40, 290, b, "TDC — Time-to-Digital Converter (delay line)")


def top_svg():
    b = ('<rect x="60" y="90" width="150" height="70" fill="none" stroke="#f0883e" stroke-width="2"/>'
         '<text x="80" y="130" fill="#e6edf3">VTC</text>'
         '<rect x="330" y="90" width="170" height="70" fill="none" stroke="#7ee787" stroke-width="2"/>'
         '<text x="350" y="130" fill="#e6edf3">TDC</text>'
         '<line x1="20" y1="125" x2="60" y2="125" stroke="#58a6ff" stroke-width="2"/>'
         '<text x="16" y="115" fill="#8b949e">Vin</text>'
         '<line x1="210" y1="125" x2="330" y2="125" stroke="#58a6ff" stroke-width="2"/>'
         '<text x="230" y="115" fill="#8b949e">Δt ∝ Vin (STOP)</text>'
         '<line x1="120" y1="200" x2="120" y2="160" stroke="#8b949e" stroke-width="1"/>'
         '<text x="60" y="220" fill="#8b949e">trigger→START</text>'
         '<line x1="120" y1="200" x2="415" y2="200" stroke="#8b949e" stroke-width="1"/>'
         '<line x1="415" y1="200" x2="415" y2="160" stroke="#8b949e" stroke-width="1"/>'
         '<line x1="500" y1="125" x2="560" y2="125" stroke="#58a6ff" stroke-width="2"/>'
         '<text x="505" y="115" fill="#8b949e">D[n]</text>')
    return _svg(600, 250, b, "VTC-ADC top: Vin → Δt → digital code")


# --------------------------------------------------------------------------- #
#  author real Virtuoso schematic cellviews (SKILL) + save to a persistent lib
# --------------------------------------------------------------------------- #
def create_schematics() -> dict:
    il = f'''
printf("SKILL_START\\n")
libName="mcp_designs"
unless( ddGetObj(libName) dbCreateLib(libName "{GUEST_LIB}") )

; ---------- VTC schematic ----------
cv = dbOpenCellViewByType(libName "VTC" "schematic" "schematic" "w")
pm = dbOpenCellViewByType("gpdk090" "pmos1v" "symbol" nil "r")
nm = dbOpenCellViewByType("gpdk090" "nmos1v" "symbol" nil "r")
dbCreateInst(cv pm "M1p" 0:200 "R0")
dbCreateInst(cv nm "M1n" 0:100 "R0")
dbCreateInst(cv nm "Ms"  0:0   "R0")
dbCreateInst(cv pm "M2p" 200:150 "R0")
dbCreateInst(cv nm "M2n" 200:50  "R0")
foreach( pn '("vdd" "vin" "trig" "stop")
  dbCreateTerm(dbCreateNet(cv pn) pn "inputOutput"))
dbSave(cv) dbClose(cv)
printf("MCP:vtc=t\\n")

; ---------- TDC single stage (buffer + dff placeholder) ----------
cv2 = dbOpenCellViewByType(libName "TDC_stage" "schematic" "schematic" "w")
dbCreateInst(cv2 nm "N1" 0:0 "R0")
dbCreateInst(cv2 pm "P1" 0:100 "R0")
dbCreateInst(cv2 nm "N2" 150:0 "R0")
dbCreateInst(cv2 pm "P2" 150:100 "R0")
foreach( pn '("vdd" "in" "tap")
  dbCreateTerm(dbCreateNet(cv2 pn) pn "inputOutput"))
dbSave(cv2) dbClose(cv2)
printf("MCP:tdc=t\\n")

; ---------- top-level placeholder ----------
cv3 = dbOpenCellViewByType(libName "VTC_ADC_top" "schematic" "schematic" "w")
foreach( pn '("Vin" "trig" "code")
  dbCreateTerm(dbCreateNet(cv3 pn) pn "inputOutput"))
dbSave(cv3) dbClose(cv3)
printf("MCP:top=t\\n")

printf("MCP:libpath=%s\\n" "{GUEST_LIB}")
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name="vtc_adc_sch", timeout=400)
    return {"ok": r.ok, "guest_lib": GUEST_LIB,
            "cells_created": [k for k in ("vtc", "tdc", "top") if r.values.get(k) == "t"],
            "log_tail": skill.ciw_tail(r.log, 1200)}


# --------------------------------------------------------------------------- #
#  orchestrator
# --------------------------------------------------------------------------- #
def build(vin_list=None, n_stages: int = 10, make_schematics: bool = True) -> dict:
    HOST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. simulate the ADC transfer
    adc = simulate_adc(vin_list, n_stages)

    # 2. write netlists to the host working dir
    (HOST_DIR / "vtc_adc_integrated.scs").write_text(
        integrated_netlist((vin_list or [0.5])[0], n_stages), encoding="utf-8")

    # 3. write schematic diagrams (SVG) to host
    (HOST_DIR / "VTC_schematic.svg").write_text(vtc_svg(), encoding="utf-8")
    (HOST_DIR / "TDC_schematic.svg").write_text(tdc_svg(), encoding="utf-8")
    (HOST_DIR / "VTC_ADC_top.svg").write_text(top_svg(), encoding="utf-8")

    # 4. a readable transfer report
    lines = ["# VTC-ADC transfer (Vin -> VTC delay -> TDC code)", ""]
    lines += ["Vin(V)\tVTC delay(ps)\tTDC code"]
    for r in adc["rows"]:
        lines.append(f"{r['vin']}\t{r.get('vtc_delay_ps')}\t{r.get('tdc_code')}")
    (HOST_DIR / "adc_transfer.txt").write_text("\n".join(lines), encoding="utf-8")

    result = {
        "ok": True,
        "adc_transfer": adc,
        "host_working_dir": str(HOST_DIR),
        "host_files": sorted(p.name for p in HOST_DIR.iterdir()),
    }

    # 5. author + save real Virtuoso schematics on the VM
    if make_schematics:
        sch = create_schematics()
        result["schematics"] = sch
        result["guest_oa_library"] = sch.get("guest_lib")
        result["open_in_virtuoso"] = (
            f"On the VM, in Virtuoso: Library Manager -> library 'mcp_designs' "
            f"(path {GUEST_LIB}) -> cells VTC / TDC_stage / VTC_ADC_top / schematic.")
        # copy the OA library back to the host as a tarball (openable in Virtuoso)
        from .. import vm
        tar = vm.run_script(f"cd /home/work && tar czf /tmp/mcp_designs_oa.tgz mcp_designs 2>&1; echo done",
                            with_env=False, timeout=120, tag="tar_oa")
        if vm.pull("/tmp/mcp_designs_oa.tgz", HOST_DIR / "mcp_designs_oa.tgz"):
            result["oa_library_archive_host"] = str(HOST_DIR / "mcp_designs_oa.tgz")
        result["host_files"] = sorted(p.name for p in HOST_DIR.iterdir())

    return result
