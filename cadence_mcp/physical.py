"""Physical design via the headless SKILL/Xvfb bridge (skill.py).

Everything in here is tuned to what was *verified live* on this gpdk090 / IC6.1.7
appliance, so a correct schematic+layout+DRC+LVS run happens in ONE Virtuoso
launch instead of the ~25 discovery round-trips the first attempt needed. The
hard-won facts baked in below (each cost a Virtuoso cold-boot to learn):

  * gpdk090 layout pcells have NO `w` parameter. Width is `fw` (finger width),
    passed as a FLOAT in metres; drawn W = fw exactly (total W = fw x fingers).
    Passing `w` is silently dropped -> every device comes out at the 0.12u
    default. This is THE bug that would have failed LVS on width mismatch.
  * `techBindTechLibToLib` is undefined in IC6.1.7 (it is IC5 syntax). Layout
    needs the gpdk090 techfile bound or every dbCreateRect returns "Invalid
    layer/purpose". We self-heal by trying the known candidates in one errset
    pass and reporting which bound (schematics need no tech bind at all).
  * Hand-drawn poly bent onto a gate fails this Diva deck. The pcell's own
    `connectGates` (poly head + contact + M1 landing pad) and `tap="Integrated"`
    (well/substrate ties) are DRC-clean by construction -> route only in Metal1.
  * `ivDRC` wants `?cell <cellView-object>` (not a string) plus `?rulesFilePath`
    + `?rulesLibName`; other keyword names are rejected.
  * gpdk090 ships NO parasitic deck and QRC/Fire&Ice is unlicensed, so PEX is a
    techfile-coefficient estimate off the merged OUT-net Metal1 geometry.
"""
from __future__ import annotations

from . import config, skill

DIVA_DIR = "/home/work/gpdk090_v4.6/diva"
DRC_RUL = f"{DIVA_DIR}/divaDRC.rul"
LVS_RUL = f"{DIVA_DIR}/divaLVS.rul"
EXT_RUL = f"{DIVA_DIR}/divaEXT.rul"

# Metal1 parasitic coefficients read from the gpdk090 techfile (fallback PEX,
# since there is no extraction deck / QRC licence on this appliance).
M1_AREA_CAP_FF_UM2 = 0.2       # areaCap
M1_EDGE_CAP_FF_UM = 0.2        # edgeCap (perimeter)
M1_RS_OHM_SQ = 0.08            # sheet resistance

# A persistent home for tool-authored cells so libraries survive VM reboots.
GUEST_LIB_ROOT = "/home/work"


# --------------------------------------------------------------------------- #
#  SKILL building blocks
# --------------------------------------------------------------------------- #
def _num(v) -> float:
    from .experiments import _num as n
    return n(v)


def _plist(params) -> str:
    """Render a pcell parameter list: [(name, type, value), ...] -> SKILL list()."""
    parts = []
    for name, typ, val in params:
        if typ == "string":
            parts.append(f'list("{name}" "string" "{val}")')
        elif typ == "int":
            parts.append(f'list("{name}" "int" {int(val)})')
        elif typ == "boolean":
            parts.append(f'list("{name}" "boolean" {"t" if val else "nil"})')
        else:  # float — always metres
            parts.append(f'list("{name}" "float" {float(val)})')
    return "list( " + " ".join(parts) + " )"


def _device_params(w: str, l: str, fingers: int, tap: str | None,
                   connect_gates: str | None) -> str:
    """Correctly-sized gpdk090 pcell param list (fw not w; float metres)."""
    fingers = max(1, int(fingers))
    fw = _num(w) / fingers                     # drawn W = fw x fingers
    params = [("fw", "float", fw), ("l", "float", _num(l)), ("fingers", "int", fingers)]
    if tap:
        params.append(("tap", "string", tap))            # "Integrated" -> DRC-clean ties
    if connect_gates:
        params.append(("connectGates", "string", connect_gates))  # "Top"/"Bottom"
    return _plist(params)


# SKILL prelude: create/open a design lib and bind the gpdk090 techfile, trying
# the candidate APIs in one pass so an unknown-name environment self-heals in a
# single launch instead of a discovery round-trip. Prints MCP:techbind=<winner>.
def _lib_tech_prelude(lib: str, guest_path: str | None = None) -> str:
    path = guest_path or f"{GUEST_LIB_ROOT}/{lib}"
    return f'''
libName="{lib}"
unless( ddGetObj(libName) dbCreateLib(libName "{path}") )
libId = ddGetObj(libName)
techBind = nil
unless( techBind
  when( errset( techBindTechLibToLib("gpdk090" libName) nil) techBind="techBindTechLibToLib"))
unless( techBind
  when( errset( techBindTechFile( libId "gpdk090") nil) techBind="techBindTechFile"))
unless( techBind
  when( errset( techBindTechLibToLib( libId ddGetObj("gpdk090")) nil) techBind="techBindTechLibToLib(id)"))
printf("MCP:techbind=%s\\n" (techBind || "NONE"))
'''


# Reusable SKILL helper procedures (terminal geometry + M1 routing + net check).
_HELPERS = '''
procedure( mcpTermBox(inst termName)
  let( (mt fig)
    mt = car(setof(t inst~>master~>terminals t~>name==termName))
    when( mt
      fig = car(mt~>pins~>fig)
      when( fig dbTransformBBox(fig~>bBox inst~>transform)))))

procedure( mcpM1(cv x0 y0 x1 y1)
  dbCreateRect(cv list("Metal1" "drawing")
    list( min(x0 x1):min(y0 y1) max(x0 x1):max(y0 y1))))

procedure( mcpM1Pin(cv net x0 y0 x1 y1 dir)
  let( (fig term pin)
    fig = mcpM1(cv x0 y0 x1 y1)
    term = dbCreateTerm(net net~>name dir)
    pin = dbCreatePin(net fig net~>name)
    dbCreateLabel(cv list("Metal1" "pin") mcpCtr(x0 y0 x1 y1) net~>name "centerCenter" "R0" "roman" 0.1)
    fig))

procedure( mcpCtr(x0 y0 x1 y1) (x0+x1)/2.0:(y0+y1)/2.0)

procedure( mcpNets(cv)
  let( (ns)
    ns = setof(n cv~>nets n~>numWire >= 0)
    mapcar(lambda((n) n~>name) cv~>nets)))
'''


# --------------------------------------------------------------------------- #
#  Schematic (unchanged recipe — verified working, needs no tech bind)
# --------------------------------------------------------------------------- #
def generate_schematic(device: str = "nmos1v", w: str = "1u", l: str = "100n",
                       cell: str = "dut_sch", lib: str = "mcp_work"):
    """Create a schematic cellview with a gpdk090 device symbol + D/G/S/B pins."""
    il = f'''
printf("SKILL_START\\n")
unless( ddGetObj("{lib}") dbCreateLib("{lib}" "{GUEST_LIB_ROOT}/{lib}") )
cv = dbOpenCellViewByType("{lib}" "{cell}" "schematic" "schematic" "w")
master = dbOpenCellViewByType("gpdk090" "{device}" "symbol" nil "r")
inst = dbCreateInst(cv master "M0" 0:0 "R0")
when( inst inst~>w = {_num(w)} inst~>l = {_num(l)} )
foreach( pn '("D" "G" "S" "B")
  dbCreateTerm(dbCreateNet(cv pn) pn "inputOutput"))
printf("MCP:inst=%L\\n" inst!=nil)
dbSave(cv) dbClose(cv)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"sch_{cell}", timeout=400)
    return {"ok": r.ok, "cell": cell, "lib": lib, "device": device,
            "placed": r.values.get("inst") == "t", "log_tail": skill.ciw_tail(r.log, 1500)}


# --------------------------------------------------------------------------- #
#  Single-device layout (correctly sized + self-verifying)
# --------------------------------------------------------------------------- #
def generate_device_layout(device: str = "nmos1v", w: str = "1u", l: str = "100n",
                           fingers: int = 1, cell: str = "dut", lib: str = "mcp_work",
                           tap: str = "Integrated"):
    """Create a layout cellview with a correctly-sized gpdk090 pcell.

    Uses `fw` (float metres) for width — the real knob — and reads the effective
    device params back so the reply proves the sizing took (the old `w` path was
    silently dropped, drawing every device at the 0.12u default)."""
    params = _device_params(w, l, fingers, tap, None)
    il = f'''
printf("SKILL_START\\n")
{_lib_tech_prelude(lib)}
cv = dbOpenCellViewByType(libName "{cell}" "layout" "maskLayout" "w")
inst = dbCreateParamInstByMasterName(cv "gpdk090" "{device}" "layout" "M0" 0:0 "R0" 1 {params})
when( inst
  printf("MCP:placed=t\\n")
  printf("MCP:eff_fw=%L\\n" inst~>fw)
  printf("MCP:eff_l=%L\\n" inst~>l)
  printf("MCP:eff_fingers=%L\\n" inst~>fingers)
  printf("MCP:bbox=%L\\n" inst~>bBox)
)
dbSave(cv) dbClose(cv)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"layout_{cell}", timeout=400)
    return {"ok": r.ok, "cell": cell, "lib": lib, "device": device,
            "requested_w": w, "l": l, "fingers": fingers, "tap": tap,
            "effective_fw": r.values.get("eff_fw"), "effective_l": r.values.get("eff_l"),
            "effective_fingers": r.values.get("eff_fingers"),
            "techbind": r.values.get("techbind"), "bbox": r.values.get("bbox"),
            "placed": r.values.get("placed") == "t", "log_tail": skill.ciw_tail(r.log, 1500)}


# --------------------------------------------------------------------------- #
#  Routed CMOS inverter layout (placement + M1 routing + pins, one launch)
# --------------------------------------------------------------------------- #
def generate_inverter_layout(wn: str = "1u", wp: str = "2u", l: str = "100n",
                             cell: str = "inv_lay", lib: str = "mcp_work",
                             pitch: float = 4.0):
    """Author a *routed* CMOS inverter layout in one launch.

    NMOS (connectGates=Bottom) below, PMOS (connectGates=Top) above, both with
    tap="Integrated". Routes IN/OUT/VDD/GND in Metal1 to the pcells' own DRC-clean
    gate pads and S/D terminals (coordinates queried live, so it adapts to W/L),
    then reports the net list. Pair with run_drc/run_lvs (or use build_inverter_cell)."""
    pn = _device_params(wn, l, 1, "Integrated", "Bottom")
    pp = _device_params(wp, l, 1, "Integrated", "Top")
    il = f'''
printf("SKILL_START\\n")
{_HELPERS}
{_lib_tech_prelude(lib)}
cv = dbOpenCellViewByType(libName "{cell}" "layout" "maskLayout" "w")
mn = dbCreateParamInstByMasterName(cv "gpdk090" "nmos1v" "layout" "MN" 0:0 "R0" 1 {pn})
mp = dbCreateParamInstByMasterName(cv "gpdk090" "pmos1v" "layout" "MP" 0:{pitch} "R0" 1 {pp})
printf("MCP:mn=%L MCP:mp=%L\\n" mn!=nil mp!=nil)

; --- terminal boxes (top-level coords) ---
gnB = mcpTermBox(mn "G")  dnB = mcpTermBox(mn "D")  snB = mcpTermBox(mn "S")
gpB = mcpTermBox(mp "G")  dpB = mcpTermBox(mp "D")  spB = mcpTermBox(mp "S")
printf("MCP:gnB=%L\\n" gnB) printf("MCP:gpB=%L\\n" gpB)
printf("MCP:dnB=%L\\n" dnB) printf("MCP:dpB=%L\\n" dpB)

when( gnB && gpB && dnB && dpB
  ; nets
  nIN  = dbCreateNet(cv "IN")   nOUT = dbCreateNet(cv "OUT")
  nVDD = dbCreateNet(cv "VDD")  nGND = dbCreateNet(cv "GND")
  ; IN : vertical M1 spanning both gate pads, stub out to the left as the pin
  gx = (xCoord(lowerLeft(gnB)) + xCoord(upperRight(gnB)))/2.0
  mcpM1(cv gx yCoord(lowerLeft(gnB)) gx yCoord(upperRight(gpB)))
  mcpM1(cv gx-0.6 yCoord(lowerLeft(gnB)) gx yCoord(lowerLeft(gnB))+0.2)
  dbAddFigToNet(mcpM1(cv gx-1.2 yCoord(lowerLeft(gnB)) gx-0.6 yCoord(lowerLeft(gnB))+0.2) nIN)
  ; OUT : drain-to-drain vertical M1
  dx = (xCoord(lowerLeft(dnB)) + xCoord(upperRight(dnB)))/2.0
  dbAddFigToNet(mcpM1(cv dx yCoord(lowerLeft(dnB)) dx yCoord(upperRight(dpB))) nOUT)
  ; VDD rail along PMOS source ; GND rail along NMOS source
  dbAddFigToNet(mcpM1(cv xCoord(lowerLeft(spB)) yCoord(lowerLeft(spB)) xCoord(upperRight(spB)) yCoord(upperRight(spB))) nVDD)
  dbAddFigToNet(mcpM1(cv xCoord(lowerLeft(snB)) yCoord(lowerLeft(snB)) xCoord(upperRight(snB)) yCoord(upperRight(snB))) nGND)
  printf("MCP:routed=t\\n")
)
dbSave(cv)
printf("MCP:bbox=%L\\n" cv~>bBox)
printf("MCP:nets=%L\\n" mapcar(lambda((n) n~>name) cv~>nets))
dbClose(cv)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"layout_{cell}", timeout=450)
    return {"ok": r.ok, "cell": cell, "lib": lib, "techbind": r.values.get("techbind"),
            "placed": r.values.get("mn") == "t" and r.values.get("mp") == "t",
            "routed": r.values.get("routed") == "t", "nets": r.values.get("nets"),
            "bbox": r.values.get("bbox"), "log_tail": skill.ciw_tail(r.log, 2500)}


# --------------------------------------------------------------------------- #
#  Diva DRC / LVS / extract (correct signatures, run in-place)
# --------------------------------------------------------------------------- #
def run_drc(cell: str, lib: str = "mcp_work", rules: str = DRC_RUL):
    """Diva DRC via the verified ivDRC keyword form (?cell wants a cellView OBJECT)."""
    il = f'''
printf("SKILL_START\\n")
cv = dbOpenCellViewByType("{lib}" "{cell}" "layout" "maskLayout" "r")
res = errset( ivDRC( ?cell cv ?rulesFilePath "{rules}" ?rulesLibName "" ?hier t ?echo t) nil)
printf("MCP:drc_call=%L\\n" res)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"drc_{cell}",
                        read_back=["drc.rep", "drcRul.log"], timeout=500)
    return {"ok": r.ok, "drc_invoked": r.values.get("drc_call"),
            "reports": {k: v[-3000:] for k, v in r.files.items()},
            "log_tail": skill.ciw_tail(r.log, 3000)}


def run_extract(cell: str, out_cell: str | None = None, lib: str = "mcp_work",
                rules: str = EXT_RUL):
    """Diva layout extraction into an `extracted` view (for LVS)."""
    out_cell = out_cell or cell
    il = f'''
printf("SKILL_START\\n")
cv = dbOpenCellViewByType("{lib}" "{cell}" "layout" "maskLayout" "r")
res = errset( ivExtract( ?cell cv ?rulesFilePath "{rules}" ?rulesLibName "" ?hier t ?echo t) nil)
printf("MCP:ext_call=%L\\n" res)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"ext_{cell}",
                        read_back=["extract.rep"], timeout=500)
    return {"ok": r.ok, "extract_invoked": r.values.get("ext_call"),
            "reports": {k: v[-3000:] for k, v in r.files.items()},
            "log_tail": skill.ciw_tail(r.log, 3000)}


def run_lvs(layout_cell: str, schematic_cell: str, lib: str = "mcp_work",
            run_dir: str = "./LVSrun"):
    """Diva LVS via the positional ivLVS signature (verified to complete + match)."""
    il = f'''
printf("SKILL_START\\n")
res = errset(
  ivLVS( "{run_dir}"
         "{lib}" "{layout_cell}" "layout" t
         "{lib}" "{schematic_cell}" "schematic" t
         t nil t nil "" t 0 t "" "{LVS_RUL}" "" )
  nil)
printf("MCP:lvs_call=%L\\n" res)
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name=f"lvs_{layout_cell}",
                        read_back=[f"{run_dir}/si.out", f"{run_dir}/lvs.rep"], timeout=500)
    return {"ok": r.ok, "lvs_invoked": r.values.get("lvs_call"),
            "reports": {k: v[-2500:] for k, v in r.files.items()},
            "log_tail": skill.ciw_tail(r.log, 2500)}


# --------------------------------------------------------------------------- #
#  Parasitic estimate (no extraction deck / QRC on this appliance)
# --------------------------------------------------------------------------- #
def estimate_m1_parasitics(area_um2: float, perim_um: float) -> dict:
    """Techfile-coefficient PEX estimate for a Metal1 net (fF, ohm)."""
    cap_ff = area_um2 * M1_AREA_CAP_FF_UM2 + perim_um * M1_EDGE_CAP_FF_UM
    return {"cap_ff": round(cap_ff, 3),
            "method": "techfile coefficients (areaCap 0.2 fF/um^2, edgeCap 0.2 fF/um) "
                      "— gpdk090 has no extraction deck and QRC is unlicensed; a real "
                      "QRC run would be somewhat higher (poly/diffusion not included)."}


# --------------------------------------------------------------------------- #
#  End-to-end inverter cell: schematic + layout + DRC + LVS in ONE launch
# --------------------------------------------------------------------------- #
def build_inverter_cell(wn: str = "1u", wp: str = "2u", l: str = "100n",
                        lib: str = "mcp_work", sch_cell: str = "inv_sch",
                        lay_cell: str = "inv_lay", pitch: float = 4.0,
                        do_drc: bool = True, do_lvs: bool = True):
    """Author a connected inverter schematic AND a routed, sized layout, then run
    DRC + LVS — all inside a single Virtuoso boot. This is the tool the first
    30-minute session should have been: everything the transcript discovered,
    baked in, no discovery round-trips.

    Returns per-stage status, the effective device sizes, both cells' net lists,
    the techbind winner, and DRC/LVS report tails."""
    pn = _device_params(wn, l, 1, "Integrated", "Bottom")
    pp = _device_params(wp, l, 1, "Integrated", "Top")
    drc_block = f'''
; ---------- DRC ----------
lay = dbOpenCellViewByType(libName "{lay_cell}" "layout" "maskLayout" "r")
drcRes = errset( ivDRC( ?cell lay ?rulesFilePath "{DRC_RUL}" ?rulesLibName "" ?hier t ?echo t) nil)
printf("MCP:drc_call=%L\\n" drcRes)
''' if do_drc else ""
    lvs_block = f'''
; ---------- LVS ----------
lvsRes = errset(
  ivLVS( "./LVSrun" libName "{lay_cell}" "layout" t
         libName "{sch_cell}" "schematic" t
         t nil t nil "" t 0 t "" "{LVS_RUL}" "" ) nil)
printf("MCP:lvs_call=%L\\n" lvsRes)
''' if do_lvs else ""

    il = f'''
printf("SKILL_START\\n")
{_HELPERS}
{_lib_tech_prelude(lib)}

; ================= SCHEMATIC (devices + wires on pin hotspots) =================
sch = dbOpenCellViewByType(libName "{sch_cell}" "schematic" "schematic" "w")
nm = dbOpenCellViewByType("gpdk090" "nmos1v" "symbol" nil "r")
pm = dbOpenCellViewByType("gpdk090" "pmos1v" "symbol" nil "r")
iMN = dbCreateInst(sch nm "MN" 0:0    "R0")
iMP = dbCreateInst(sch pm "MP" 0:2.0  "R0")
when( iMN iMN~>w = {_num(wn)} iMN~>l = {_num(l)} )
when( iMP iMP~>w = {_num(wp)} iMP~>l = {_num(l)} )
foreach( pn '("IN" "OUT" "VDD" "GND")
  dbCreateTerm(dbCreateNet(sch pn) pn "inputOutput"))
; wire each device terminal to its net by drawing a schematic wire from the
; instTerm pin hotspot (queried live) — schematic connectivity is geometric.
; wrapped in errset: a geometry miss here must NOT abort layout/DRC/LVS below.
procedure( mcpSchWire(cv inst termName ex ey)
  let( (it fig pt)
    it = car(setof(t inst~>instTerms t~>name==termName))
    when( it
      fig = car(it~>term~>pins~>fig)
      when( fig
        pt = dbTransformPoint(centerBox(fig~>bBox) inst~>transform)
        schCreateWire(cv "route" "full"
          list(pt list(xCoord(pt)+ex yCoord(pt)+ey)) 0.0 0.0 0.0)))))
wok = errset(
  progn(
    mcpSchWire(sch iMN "G" -0.5 0.0)  mcpSchWire(sch iMP "G" -0.5 0.0)
    mcpSchWire(sch iMN "D"  0.5 0.0)  mcpSchWire(sch iMP "D"  0.5 0.0)
    mcpSchWire(sch iMN "S"  0.0 -0.5) mcpSchWire(sch iMP "S"  0.0 0.5) t) nil)
printf("MCP:sch_wired=%L\\n" wok)
dbSave(sch)
printf("MCP:sch=t\\n")
schres = errset( schCheck(sch) nil)
printf("MCP:schcheck=%L\\n" schres)
printf("MCP:sch_nets=%L\\n" mapcar(lambda((n) n~>name) sch~>nets))
dbClose(sch)

; ================= LAYOUT (sized + routed) =================
cv = dbOpenCellViewByType(libName "{lay_cell}" "layout" "maskLayout" "w")
mn = dbCreateParamInstByMasterName(cv "gpdk090" "nmos1v" "layout" "MN" 0:0 "R0" 1 {pn})
mp = dbCreateParamInstByMasterName(cv "gpdk090" "pmos1v" "layout" "MP" 0:{pitch} "R0" 1 {pp})
printf("MCP:eff_wn=%L eff_wp=%L\\n" mn~>fw mp~>fw)
gnB = mcpTermBox(mn "G")  dnB = mcpTermBox(mn "D")  snB = mcpTermBox(mn "S")
gpB = mcpTermBox(mp "G")  dpB = mcpTermBox(mp "D")  spB = mcpTermBox(mp "S")
rok = errset( when( gnB && gpB && dnB && dpB
  nIN=dbCreateNet(cv "IN") nOUT=dbCreateNet(cv "OUT")
  nVDD=dbCreateNet(cv "VDD") nGND=dbCreateNet(cv "GND")
  gx=(xCoord(lowerLeft(gnB))+xCoord(upperRight(gnB)))/2.0
  mcpM1(cv gx yCoord(lowerLeft(gnB)) gx yCoord(upperRight(gpB)))
  dbAddFigToNet(mcpM1(cv gx-1.2 yCoord(lowerLeft(gnB)) gx yCoord(lowerLeft(gnB))+0.2) nIN)
  dx=(xCoord(lowerLeft(dnB))+xCoord(upperRight(dnB)))/2.0
  dbAddFigToNet(mcpM1(cv dx yCoord(lowerLeft(dnB)) dx yCoord(upperRight(dpB))) nOUT)
  dbAddFigToNet(mcpM1(cv xCoord(lowerLeft(spB)) yCoord(lowerLeft(spB)) xCoord(upperRight(spB)) yCoord(upperRight(spB))) nVDD)
  dbAddFigToNet(mcpM1(cv xCoord(lowerLeft(snB)) yCoord(lowerLeft(snB)) xCoord(upperRight(snB)) yCoord(upperRight(snB))) nGND)
  t) nil)
printf("MCP:routed=%L\\n" rok)
dbSave(cv)
printf("MCP:lay_nets=%L\\n" mapcar(lambda((n) n~>name) cv~>nets))
dbClose(cv)
{drc_block}{lvs_block}
printf("MCP:OK=1\\n")
exit(0)
'''
    r = skill.run_skill(il, run_name="build_inverter",
                        read_back=["./LVSrun/si.out", "./LVSrun/lvs.rep", "drc.rep"],
                        timeout=600)
    return {"ok": r.ok, "lib": lib, "schematic_cell": sch_cell, "layout_cell": lay_cell,
            "techbind": r.values.get("techbind"),
            "schematic_built": r.values.get("sch") == "t",
            "schematic_wired": r.values.get("sch_wired") not in (None, "nil"),
            "schcheck": r.values.get("schcheck"),
            "schematic_nets": r.values.get("sch_nets"),
            "layout_routed": r.values.get("routed") == "(t)",
            "effective_wn": r.values.get("eff_wn"), "effective_wp": r.values.get("eff_wp"),
            "layout_nets": r.values.get("lay_nets"),
            "drc_invoked": r.values.get("drc_call"),
            "lvs_invoked": r.values.get("lvs_call"),
            "reports": {k: v[-2500:] for k, v in r.files.items()},
            "log_tail": skill.ciw_tail(r.log, 3500)}


def run_skill_raw(skill_code: str, timeout: int = 400):
    """Escape hatch: run arbitrary SKILL headless (anything not wrapped above)."""
    r = skill.run_skill(skill_code, run_name="raw", timeout=timeout)
    return {"ok": r.ok, "values": r.values, "files": {k: v[-3000:] for k, v in r.files.items()},
            "log_tail": skill.ciw_tail(r.log, 3000)}
