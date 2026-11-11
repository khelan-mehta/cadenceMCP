"""Layout iteration 3.
1. Flatten pcell copies in a scratch cell to learn the TRUE Metal1/Cont geometry.
2. Rebuild widlar_lay with routes landing on real contact metal.
3. DRC / extract with visible error text; LVS on the layout view (proven form).
"""
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

; ---------- 1. flatten probe ----------
sc = dbOpenCellViewByType(lib "scratch_flat" "layout" "maskLayout" "w")
mp1 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top"))
mp2 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "None") list("connectGates" "string" "Top"))
i1 = dbCreateParamInstByMasterName(sc "gpdk090" "nmos2v" "layout" "F1" 0:0 "R0" 1 mp1)
i2 = dbCreateParamInstByMasterName(sc "gpdk090" "nmos2v" "layout" "F2" 20.0:0 "R0" 1 mp2)
dbFlattenInst(i1 32 t t)
dbFlattenInst(i2 32 t t)
foreach(sh sc~>shapes
  when( sh~>layerName=="Metal1" && sh~>purpose=="drawing"
    printf("MCP:m1 %L\n" sh~>bBox)))
dbSave(sc) dbClose(sc)

; ---------- 2. rebuild layout ----------
cv = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "w")
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 0:0 "R0" 1 mp1)
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 6.0:0 "R0" 1 mp2)
RS = dbCreateParamInstByMasterName(cv "gpdk090" "resnsppoly" "layout" "RS" 0:-32.0 "R0" 1
      list(list("segments" "int" @SEGS@) list("segW" "float" 1e-6) list("segL" "float" @SEGL@e-6)
           list("connection" "string" "Series")))
d1 = termBox(MA "D") g1 = termBox(MA "G") b1 = termBox(MA "B")
d2 = termBox(MB "D") g2 = termBox(MB "G") s2 = termBox(MB "S")
rp = termBox(RS "PLUS") rm = termBox(RS "MINUS")
; source-column metal x-range, from the flatten probe: the narrow Metal1 column
; inside the S diffusion. We recompute it generically: source metal column =
; Metal1 rect whose x-range lies inside the S box of the probe cells.
; For tap=None (M2) the probe showed its own column; apply the offset directly.
sMet2x0 = @SM2X0@ + 6.0 - 20.0   ; probe F2 at x=20 -> M2 at x=6
sMet2x1 = @SM2X1@ + 6.0 - 20.0
printf("MCP:nscol=%L %L\n" sMet2x0 sMet2x1)

nIREF = dbCreateNet(cv "IREF") nIOUT = dbCreateNet(cv "IOUT")
nGND = dbCreateNet(cv "GND")  nNS  = dbCreateNet(cv "NS")
railY0 = -2.0 railY1 = -1.6
netRect(cv nGND -1.0 railY0 45.0 railY1)
netRect(cv nGND xCoord(lowerLeft(b1)) railY1 xCoord(upperRight(b1)) 0.1)
netRect(cv nGND xCoord(lowerLeft(rm)) yCoord(lowerLeft(rm)) 45.0 yCoord(upperRight(rm)))
netRect(cv nGND 44.88 yCoord(lowerLeft(rm)) 45.0 railY1)
netRect(cv nNS sMet2x0 -1.1 sMet2x1 0.1)
netRect(cv nNS -1.4 -1.1 sMet2x1 -0.9)
netRect(cv nNS -1.4 yCoord(lowerLeft(rp)) -1.28 -0.9)
netRect(cv nNS -1.4 yCoord(lowerLeft(rp)) xCoord(upperRight(rp)) yCoord(upperRight(rp)))
dx0 = xCoord(lowerLeft(d1)) dx1 = xCoord(upperRight(d1))
barY0 = 3.6 barY1 = 3.72
netRect(cv nIREF dx0 yCoord(upperRight(d1))-0.1 dx1 barY1)
netRect(cv nIREF -1.4 barY0 xCoord(upperRight(g2))-0.02 barY1)
gc1 = (xCoord(lowerLeft(g1))+xCoord(upperRight(g1)))/2.0
gc2 = (xCoord(lowerLeft(g2))+xCoord(upperRight(g2)))/2.0
netRect(cv nIREF gc1-0.06 yCoord(lowerLeft(g1))+0.02 gc1+0.06 barY1)
netRect(cv nIREF gc2-0.06 yCoord(lowerLeft(g2))+0.02 gc2+0.06 barY1)
ox0 = xCoord(lowerLeft(d2)) ox1 = xCoord(upperRight(d2))
netRect(cv nIOUT ox0 -0.75 ox1 0.1)
netRect(cv nIOUT ox0 -0.75 8.3 -0.63)
mkPin(cv nIREF -1.4 barY0 -0.9 barY1)
mkPin(cv nIOUT 7.8 -0.75 8.3 -0.63)
mkPin(cv nGND 4.0 railY0 4.5 railY1)
printf("MCP:routed=t nets=%L\n" cv~>nets~>name)
dbSave(cv)

; ---------- 3. DRC (verbose errors) ----------
lay = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "r")
drcRes = errset( ivDRC( ?cell lay ?rulesFilePath "/home/work/gpdk090_v4.6/diva/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drc_call=%L err=%L\n" drcRes errset.errset)
extRes = errset( ivExtract( ?cell lay ?rulesFilePath "/home/work/gpdk090_v4.6/diva/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:ext_call=%L err=%L\n" extRes errset.errset)
lvsRes = errset(
  ivLVS( "./LVSrun" lib "widlar_lay" "layout" t
         lib "widlar_core" "schematic" t
         t nil t nil "" t 0 t "" "/home/work/gpdk090_v4.6/diva/divaLVS.rul" "" ) t)
printf("MCP:lvs_call=%L err=%L\n" lvsRes errset.errset)
printf("MCP:OK=1\n")
exit(0)
'''
il = il.replace("@SEGS@", str(SEGS)).replace("@SEGL@", f"{SEGL}")

# two-phase: first run only the flatten probe to learn metal columns? To keep it
# one boot, run probe phase now with placeholder, parse, then substitute & run fully.
probe = il.split("; ---------- 2. rebuild layout ----------")[0] + '\nprintf("MCP:OK=1\\n")\nexit(0)\n'
log, _, _ = run_gui(probe, shots=[], timeout=600, tag="flatprobe")
# simpler reparse
boxes = []
for a, b in re.findall(r"MCP:m1 \(\(([^)]+)\) \(([^)]+)\)\)", log):
    x0, y0 = map(float, a.split()); x1, y1 = map(float, b.split())
    boxes.append((x0, y0, x1, y1))
print("Metal1 boxes:", boxes)
# F2 (tap=None) at x=20: its source column = narrow vertical Metal1 with x in [19..20.6], tall (y span > 2)
cand = [b for b in boxes if 18.5 < b[0] < 20.3 and (b[3] - b[1]) > 2.0 and (b[2] - b[0]) < 0.4]
print("F2 source-col candidates:", cand)
assert cand, "no source column metal found for tap=None device"
smx0, smx1 = cand[0][0], cand[0][2]
il = il.replace("@SM2X0@", f"{smx0}").replace("@SM2X1@", f"{smx1}")
log2, got, files = run_gui(il, shots=[], timeout=900, tag="lay3",
                           read_back=["/home/work/widlar_run/LVSrun/si.out"])
open("designs/widlar/build_lay3.log", "w", encoding="utf-8").write(log2)
print("\n".join(re.findall(r"MCP:(?:routed|drc_call|ext_call|lvs_call|nscol)[^\n]*", log2)))
for k, v in files.items():
    print("==== ", k); print(v[-2500:])
