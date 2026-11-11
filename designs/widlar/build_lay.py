"""Widlar layout: M1 + M2 (nmos2v, 2 fingers, integrated taps, connectGates=Top)
side by side, resnsppoly serpentine below M2, Metal1 routing, pins,
then Diva DRC + extract + LVS against widlar_core — all in one Virtuoso boot.
Every geometry step prints MCP markers; the result is screenshotted."""
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
procedure( allTermBoxes(inst tn)
  let( (mt)
    mt = car(setof(x inst~>master~>terminals x~>name==tn))
    foreach(p mt~>pins
      printf("MCP:tb %s.%s %s %L\n" inst~>name tn p~>fig~>layerName dbTransformBBox(p~>fig~>bBox inst~>transform)))))
procedure( M1R(cv x0 y0 x1 y1)
  dbCreateRect(cv list("Metal1" "drawing") list(min(x0 x1):min(y0 y1) max(x0 x1):max(y0 y1))))
procedure( ctr(bb) list((xCoord(lowerLeft(bb))+xCoord(upperRight(bb)))/2.0 (yCoord(lowerLeft(bb))+yCoord(upperRight(bb)))/2.0))

; ---------- open layout ----------
cv = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "w")
mosP = list(list("fw" "float" 1.56e-6) list("l" "float" 2.8e-7) list("fingers" "int" 2)
            list("tap" "string" "Integrated") list("connectGates" "string" "Top")
            list("connectSD" "string" "Source"))
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 0:0 "R0" 1 mosP)
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 6.0:0 "R0" 1 mosP)
rsP = list(list("segments" "int" @SEGS@) list("segW" "float" 1e-6) list("segL" "float" @SEGL@e-6)
           list("connection" "string" "Series") list("leftTap" "boolean" t))
RS = dbCreateParamInstByMasterName(cv "gpdk090" "resnsppoly" "layout" "RS" 0:-32.0 "R0" 1 rsP)
printf("MCP:placed=%L\n" list(MA!=nil MB!=nil RS!=nil))
printf("MCP:mosbb=%L %L\n" MA~>bBox MB~>bBox)
printf("MCP:rsbb=%L\n" RS~>bBox)
printf("MCP:eff=%L %L %L\n" MA~>fw MA~>fingers RS~>segments)
foreach(tn '("D" "G" "S" "B") allTermBoxes(MA tn))
foreach(tn RS~>master~>terminals~>name allTermBoxes(RS tn))
printf("MCP:cdsd=%L
" errset(cdfParseCallbacks(nil) nil))
printf("MCP:envprobe=%L
" errset(envGetVal("layout" "stopLevel") nil))
printf("MCP:bk_shiftf=%L
" hiGetBindKey("Layout" "Shift<Key>f"))
dbSave(cv)
printf("MCP:OK=1\n")
w = geOpen(?lib lib ?cell "widlar_lay" ?view "layout" ?mode "r")
hiResizeWindow(hiGetCurrentWindow() list(0:0 1600:1000))
procedure(wlA()
  errset(envSetVal("layout" "stopLevel" 'int 32) nil)
  errset(evalstring(hiGetBindKey("Layout" "Shift<Key>f")) t)
  errset(evalstring(hiGetBindKey("Layout" "<Key>f")) t)
  hiRegTimer("wlB()" 30))
procedure(wlB() mcpShot("lay_probe") exit(0))
hiRegTimer("wlA()" 40)
'''
il = il.replace("@SEGS@", str(SEGS)).replace("@SEGL@", f"{SEGL}")
log, got, _ = run_gui(il, shots=["lay_probe"], timeout=700, tag="layp")
open("designs/widlar/build_lay.log", "w", encoding="utf-8").write(log)
print(got)
print("\n".join(re.findall(r"MCP:[^\n]*|\*Error\*[^\n]*", log))[:8000])
