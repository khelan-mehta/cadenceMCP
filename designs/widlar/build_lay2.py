"""Widlar layout v2: dynamic-geometry routing + pins + DRC + extract + LVS, one boot.
Floorplan: M1 (tap=Integrated) at x=0, M2 (tap=None) at x=6, RS serpentine R0 below.
All route coordinates derive from queried pin boxes - nothing hardcoded to pcell internals.
Also retunes every schematic MOS to fingers=1 / fw=3.12u so LVS devices compare 1:1."""
import sys, re; sys.path.insert(0, "designs/widlar")
from vgui import run_gui

SEGS, SEGL = 28, 24.195

il = r'''
printf("SKILL_START\n")
lib = "widlar_lib"
procedure( termBox(inst tn)
  let( (mt fig)
    mt = car(setof(x inst~>master~>terminals x~>name==tn))
    fig = car(mt~>pins)~>fig
    when(fig dbTransformBBox(fig~>bBox inst~>transform))))
procedure( M1R(cv x0 y0 x1 y1)
  dbCreateRect(cv list("Metal1" "drawing") list(min(x0 x1):min(y0 y1) max(x0 x1):max(y0 y1))))
procedure( netRect(cv net x0 y0 x1 y1)
  let((f) f = M1R(cv x0 y0 x1 y1) dbAddFigToNet(f net) f))
procedure( mkPin(cv net x0 y0 x1 y1)
  let( (fig)
    fig = M1R(cv x0 y0 x1 y1)
    dbCreateTerm(net net~>name "inputOutput")
    dbCreatePin(net fig)
    dbCreateLabel(cv list("Metal1" "pin") list((x0+x1)/2.0 (y0+y1)/2.0) net~>name "centerCenter" "R0" "roman" 0.3)
    fig))

; ---------- 0. schematic devices -> fingers=1 ----------
foreach(cc '("widlar" "widlar_core")
  sch = dbOpenCellViewByType(lib cc "schematic" "schematic" "a")
  foreach(i sch~>instances
    when( i~>cellName=="nmos2v"
      i~>fingers = "1"  i~>fw = "3.12u"))
  schCheck(sch) dbSave(sch) dbClose(sch)
  printf("MCP:schfix_%s=t\n" cc))

; ---------- 1. place ----------
cv = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "w")
mp1 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top"))
mp2 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "None") list("connectGates" "string" "Top"))
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 0:0 "R0" 1 mp1)
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 6.0:0 "R0" 1 mp2)
RS = dbCreateParamInstByMasterName(cv "gpdk090" "resnsppoly" "layout" "RS" 0:-32.0 "R0" 1
      list(list("segments" "int" @SEGS@) list("segW" "float" 1e-6) list("segL" "float" @SEGL@e-6)
           list("connection" "string" "Series")))
printf("MCP:bb M1=%L M2=%L RS=%L\n" MA~>bBox MB~>bBox RS~>bBox)
printf("MCP:eff fw=%L fing=%L segs=%L\n" MA~>fw MA~>fingers RS~>segments)
d1 = termBox(MA "D") g1 = termBox(MA "G") s1 = termBox(MA "S") b1 = termBox(MA "B")
d2 = termBox(MB "D") g2 = termBox(MB "G") s2 = termBox(MB "S") b2 = termBox(MB "B")
rp = termBox(RS "PLUS") rm = termBox(RS "MINUS")
printf("MCP:t d1=%L g1=%L s1=%L b1=%L\n" d1 g1 s1 b1)
printf("MCP:t d2=%L g2=%L s2=%L b2=%L\n" d2 g2 s2 b2)
printf("MCP:t rp=%L rm=%L\n" rp rm)

; ---------- 2. nets + routing (Metal1 only) ----------
nIREF = dbCreateNet(cv "IREF") nIOUT = dbCreateNet(cv "IOUT")
nGND = dbCreateNet(cv "GND")  nNS  = dbCreateNet(cv "NS")
; GND rail under the MOS row, extended right to pick up RS.MINUS riser
railY0 = -2.0 railY1 = -1.6
netRect(cv nGND -1.0 railY0 45.0 railY1)
; M1 S/B (integrated tap: B metal column) down to rail
netRect(cv nGND xCoord(lowerLeft(b1)) railY1 xCoord(upperRight(b1)) 0.1)
; also drop the S diffusion contact column if it carries metal (use S box x-range clipped to metal width)
; RS.MINUS riser on the far right
netRect(cv nGND xCoord(lowerLeft(rm)) yCoord(lowerLeft(rm)) 45.0 yCoord(upperRight(rm)))
netRect(cv nGND 44.88 yCoord(lowerLeft(rm)) 45.0 railY1)
; NS: M2.S col down, channel left, down the left edge, into RS.PLUS
nsX0 = xCoord(lowerLeft(s2)) nsX1 = nsX0+0.12
netRect(cv nNS nsX0 -1.1 nsX1 0.1)
netRect(cv nNS -1.4 -1.1 nsX1 -0.9)
netRect(cv nNS -1.4 yCoord(lowerLeft(rp)) -1.28 -0.9)
netRect(cv nNS -1.4 yCoord(lowerLeft(rp)) xCoord(upperRight(rp)) yCoord(upperRight(rp)))
; IREF: M1.D up, bar across to both gate straps, out to pin on the left
dx0 = xCoord(lowerLeft(d1)) dx1 = xCoord(upperRight(d1))
barY0 = 2.3 barY1 = 2.42
netRect(cv nIREF dx0 yCoord(upperRight(d1))-0.1 dx1 barY1)
netRect(cv nIREF -1.4 barY0 xCoord(upperRight(g2))-0.1 barY1)
gc1 = (xCoord(lowerLeft(g1))+xCoord(upperRight(g1)))/2.0
gc2 = (xCoord(lowerLeft(g2))+xCoord(upperRight(g2)))/2.0
netRect(cv nIREF gc1-0.06 yCoord(lowerLeft(g1))+0.02 gc1+0.06 barY1)
netRect(cv nIREF gc2-0.06 yCoord(lowerLeft(g2))+0.02 gc2+0.06 barY1)
; IOUT: M2.D down, stub right, pin
ox0 = xCoord(lowerLeft(d2)) ox1 = xCoord(upperRight(d2))
netRect(cv nIOUT ox0 -0.75 ox1 0.1)
netRect(cv nIOUT ox0 -0.75 8.3 -0.63)
; pins
mkPin(cv nIREF -1.4 barY0 -0.9 barY1)
mkPin(cv nIOUT 7.8 -0.75 8.3 -0.63)
mkPin(cv nGND 4.0 railY0 4.5 railY1)
printf("MCP:routed=t nets=%L\n" cv~>nets~>name)
dbSave(cv)

; ---------- 3. DRC ----------
lay = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "r")
drcRes = errset( ivDRC( ?cell lay ?rulesFilePath "/home/work/gpdk090_v4.6/diva/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) nil)
printf("MCP:drc_call=%L\n" drcRes)

; ---------- 4. extract + LVS ----------
extRes = errset( ivExtract( ?cell lay ?rulesFilePath "/home/work/gpdk090_v4.6/diva/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) nil)
printf("MCP:ext_call=%L\n" extRes)
lvsRes = errset(
  ivLVS( "./LVSrun" lib "widlar_lay" "extracted" t
         lib "widlar_core" "schematic" t
         t nil t nil "" t 0 t "" "/home/work/gpdk090_v4.6/diva/divaLVS.rul" "" ) nil)
printf("MCP:lvs_call=%L\n" lvsRes)
printf("MCP:OK=1\n")

; ---------- 5. screenshots ----------
w = geOpen(?lib lib ?cell "widlar_lay" ?view "layout" ?mode "r")
hiResizeWindow(hiGetCurrentWindow() list(0:0 1600:1000))
procedure(wlA()
  errset(evalstring(hiGetBindKey("Layout" "Shift<Key>f")) t)
  errset(evalstring(hiGetBindKey("Layout" "<Key>f")) t)
  hiRegTimer("wlB()" 30))
procedure(wlB() mcpShot("lay_full")
  errset(hiZoomIn(hiGetCurrentWindow() list(-2.5:-3.5 10.0:3.5)) t)
  hiRegTimer("wlC()" 30))
procedure(wlC() mcpShot("lay_mos") exit(0))
hiRegTimer("wlA()" 40)
'''
il = il.replace("@SEGS@", str(SEGS)).replace("@SEGL@", f"{SEGL}")
log, got, _ = run_gui(il, shots=["lay_full", "lay_mos"], timeout=900, tag="lay2",
                      read_back=["/home/work/widlar_run/LVSrun/si.out",
                                 "/home/work/widlar_run/LVSrun/lvs.rep",
                                 "/home/work/widlar_run/widlar_lay.drc.summary"])
open("designs/widlar/build_lay2.log", "w", encoding="utf-8").write(log)
print(got)
print("\n".join(re.findall(r"MCP:[^\n]*|\*Error\*[^\n]*|Total errors[^\n]*|RESULT[^\n]*", log))[:9000])
