"""Rebuild layout with: labels on (Metal1 label), RS leftTap for substrate
stamping, NS routed under the pad row; DRC + extract + ivLVS netlist prep in
Virtuoso, then standalone `si -batch` for the LVS compare."""
import re
from cadence_mcp import skill, vm

DIVA = "/home/work/gpdk090_v4.6/diva"
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
    dbCreateLabel(cv list("Metal1" "label") list((x0+x1)/2.0 (y0+y1)/2.0) net~>name "centerCenter" "R0" "roman" 0.3)
    fig))
cv = dbOpenCellViewByType(lib "widlar_lay" "layout" "maskLayout" "w")
mp1 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top"))
mp2 = list(list("fw" "float" 3.12e-6) list("l" "float" 2.8e-7) list("fingers" "int" 1)
           list("tap" "string" "None") list("connectGates" "string" "Top"))
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 0:0 "R0" 1 mp1)
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 6.0:0 "R0" 1 mp2)
RS = dbCreateParamInstByMasterName(cv "gpdk090" "resnsppoly" "layout" "RS" 0:-32.0 "R0" 1
      list(list("segments" "int" @SEGS@) list("segW" "float" 1e-6) list("segL" "float" @SEGL@e-6)
           list("connection" "string" "Series") list("leftTap" "boolean" t)))
d1 = termBox(MA "D") g1 = termBox(MA "G") b1 = termBox(MA "B")
d2 = termBox(MB "D") g2 = termBox(MB "G") s2 = termBox(MB "S")
rp = termBox(RS "PLUS") rm = termBox(RS "MINUS") rb = termBox(RS "B")
printf("MCP:t rp=%L rm=%L rb=%L s2=%L\n" rp rm rb s2)
nIREF = dbCreateNet(cv "IREF") nIOUT = dbCreateNet(cv "IOUT")
nGND = dbCreateNet(cv "GND")  nNS  = dbCreateNet(cv "NS")
railY0 = -2.0 railY1 = -1.6
netRect(cv nGND -1.0 railY0 45.0 railY1)
netRect(cv nGND xCoord(lowerLeft(b1)) railY1 xCoord(upperRight(b1)) 0.1)
netRect(cv nGND xCoord(lowerLeft(rm)) yCoord(lowerLeft(rm)) 45.0 yCoord(upperRight(rm)))
netRect(cv nGND 44.88 yCoord(lowerLeft(rm)) 45.0 railY1)
; RS body tap strip up to the rail
netRect(cv nGND xCoord(lowerLeft(rb)) yCoord(upperRight(rb))-0.1 xCoord(upperRight(rb)) railY1)
; NS: M2 source col -> channel -> left edge -> under the pad row -> up into PLUS
nsX0 = 5.76 nsX1 = 5.88
netRect(cv nNS nsX0 -1.1 nsX1 0.1)
netRect(cv nNS -1.4 -1.1 nsX1 -0.9)
netRect(cv nNS -1.4 -33.0 -1.28 -0.9)
netRect(cv nNS -1.4 -33.0 0.56 -32.88)
netRect(cv nNS 0.44 -33.0 0.56 yCoord(lowerLeft(rp))+0.1)
dx0 = xCoord(lowerLeft(d1)) dx1 = xCoord(upperRight(d1))
barY0 = 3.6 barY1 = 3.72
netRect(cv nIREF dx0 yCoord(upperRight(d1))-0.1 dx1 barY1)
netRect(cv nIREF -1.4 barY0 xCoord(upperRight(g2))-0.02 barY1)
netRect(cv nIREF 0.08 3.26 dx1 barY1)
netRect(cv nIREF 6.08 3.26 xCoord(upperRight(d2)) barY1)
ox0 = xCoord(lowerLeft(d2)) ox1 = xCoord(upperRight(d2))
netRect(cv nIOUT ox0 -0.75 ox1 0.1)
netRect(cv nIOUT ox0 -0.75 8.3 -0.63)
mkPin(cv nIREF -1.4 barY0 -0.9 barY1)
mkPin(cv nIOUT 7.8 -0.75 8.3 -0.63)
mkPin(cv nGND 4.0 railY0 4.5 railY1)
printf("MCP:routed=t\n")
dbSave(cv)
drcA = errset( ivDRC( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
extA = errset( ivExtract( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)
lvs1 = errset(
  ivLVS( "./LVSrun" "widlar_lib" "widlar_lay" "extracted" t
         "widlar_lib" "widlar_core" "schematic" t
         t nil t nil "" t 0 t "" "@DIVA@/divaLVS.rul" "" ) t)
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA).replace("@SEGS@", str(SEGS)).replace("@SEGL@", f"{SEGL}")
r = skill.run_skill(il, run_name="widlar_fix2",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    timeout=900)
open("designs/widlar/fix2.log", "w", encoding="utf-8").write(r.log)
print("values:", {k: v for k, v in r.values.items() if "%" not in v})
i = r.log.find("Summary of rule violations")
print(r.log[i-50:i+500] if i >= 0 else "no DRC summary")

# ---- standalone si LVS ----
rb = vm.run_script(r'''
cd /home/work/mcp_skill_runs/widlar_fix2
cp cds.lib LVSrun/ 2>/dev/null
cd LVSrun
si -batch -command lvs
echo "SI_RC=$?"
echo ==== si.out ====
cat si.out 2>/dev/null | head -120
''', timeout=400, tag="silvs")
print(rb.log[-4000:])
