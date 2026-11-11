"""HS-cascode layout v2 (verified-geometry plan):
M0@0 Int | M1@6 Int | M2@12 Int (bottom row); M3@6+16 None+switchSD (S over
M1.D) | M4@12+16 None (NB jog). IIN crosses the NA lane on a short Metal2
bridge with Via1 pads. Then DRC + extract + netlist dump + LVS binary."""
import re
from cadence_mcp import skill, vm

DIVA = "/home/work/gpdk090_v4.6/diva"

il = r'''
printf("SKILL_START\n")
lib = "widlar_lib"
procedure( M1R(cv x0 y0 x1 y1)
  dbCreateRect(cv list("Metal1" "drawing") list(min(x0 x1):min(y0 y1) max(x0 x1):max(y0 y1))))
procedure( LR(cv lay x0 y0 x1 y1)
  dbCreateRect(cv list(lay "drawing") list(min(x0 x1):min(y0 y1) max(x0 x1):max(y0 y1))))
procedure( netRect(cv net x0 y0 x1 y1)
  let((f) f = M1R(cv x0 y0 x1 y1) dbAddFigToNet(f net) f))
procedure( netLR(cv net lay x0 y0 x1 y1)
  let((f) f = LR(cv lay x0 y0 x1 y1) dbAddFigToNet(f net) f))
procedure( mkPin(cv net x0 y0 x1 y1)
  let( (fig)
    fig = M1R(cv x0 y0 x1 y1)
    dbCreateTerm(net net~>name "inputOutput")
    dbCreatePin(net fig)
    dbCreateLabel(cv list("Metal1" "label") list((x0+x1)/2.0 (y0+y1)/2.0) net~>name "centerCenter" "R0" "roman" 0.3)
    fig))
cv = dbOpenCellViewByType(lib "hsc_lay" "layout" "maskLayout" "w")
M0 = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M0" 0:0 "R0" 1
      list(list("fw" "float" 3e-6) list("l" "float" 1e-6) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top")))
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 6.0:0 "R0" 1
      list(list("fw" "float" 12e-6) list("l" "float" 1e-6) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top")))
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 12.0:0 "R0" 1
      list(list("fw" "float" 12e-6) list("l" "float" 1e-6) list("fingers" "int" 1)
           list("tap" "string" "Integrated") list("connectGates" "string" "Top")))
MC = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M3" 6.0:16.0 "R0" 1
      list(list("fw" "float" 12e-6) list("l" "float" 1e-6) list("fingers" "int" 1)
           list("tap" "string" "None") list("connectGates" "string" "Top") list("switchSD" "boolean" t)))
MD = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M4" 12.0:16.0 "R0" 1
      list(list("fw" "float" 12e-6) list("l" "float" 1e-6) list("fingers" "int" 1)
           list("tap" "string" "None") list("connectGates" "string" "Top")))
printf("MCP:placed=t\n")
nGND=dbCreateNet(cv "GND") nVB=dbCreateNet(cv "IBIAS") nIN=dbCreateNet(cv "IIN")
nNA=dbCreateNet(cv "NA") nNB=dbCreateNet(cv "NB") nOUT=dbCreateNet(cv "IOUT")
; ---- GND ----
netRect(cv nGND -2.0 -2.0 15.0 -1.6)
netRect(cv nGND -0.5 -1.6 -0.12 0.1)
netRect(cv nGND 5.5 -1.6 5.88 0.1)
netRect(cv nGND 11.5 -1.6 11.88 0.1)
mkPin(cv nGND 2.0 -2.0 2.5 -1.6)
; ---- vb (IBIAS): M0 diode plate, left leg, top bar, strap drops ----
netRect(cv nVB 0.08 2.9 1.24 3.52)
netRect(cv nVB -1.0 3.4 1.24 3.52)
netRect(cv nVB -1.0 3.4 -0.88 28.56)
netRect(cv nVB -2.0 28.44 12.62 28.56)
netRect(cv nVB 6.5 28.2 6.62 28.56)
netRect(cv nVB 12.5 28.2 12.62 28.56)
mkPin(cv nVB -2.0 28.44 -1.5 28.56)
; ---- NA: single vertical, S3 (east col of M3, switched) over D1 ----
netRect(cv nNA 7.12 11.9 7.24 16.1)
; ---- NB: S4 west col down, jog, into D2 ----
netRect(cv nNB 11.76 13.18 11.88 16.1)
netRect(cv nNB 11.76 13.18 13.24 13.3)
netRect(cv nNB 13.12 11.9 13.24 13.3)
; ---- IIN: D3 (west col) drop + west bar + strap drops + M2 piece + M2 bridge ----
netRect(cv nIN 5.76 12.44 5.88 16.1)
netRect(cv nIN 4.5 12.44 6.94 12.56)
netRect(cv nIN 6.3 12.2 6.42 12.56)
netRect(cv nIN 7.42 12.44 12.42 12.56)
netRect(cv nIN 12.3 12.2 12.42 12.56)
; via landing pads (Metal1), Via1 cuts, Metal2 bridge
netRect(cv nIN 6.3 12.4 6.86 12.72)
netRect(cv nIN 7.5 12.4 7.9 12.72)
netLR(cv nIN "Via1" 6.56 12.49 6.70 12.63)
netLR(cv nIN "Via1" 7.62 12.49 7.76 12.63)
netLR(cv nIN "Metal2" 6.46 12.4 7.9 12.72)
mkPin(cv nIN 4.5 12.44 5.0 12.56)
; ---- IOUT: D4 east col exit right ----
netRect(cv nOUT 13.12 16.0 15.0 16.12)
mkPin(cv nOUT 14.5 16.0 15.0 16.12)
printf("MCP:routed=t\n")
dbSave(cv)
drcA = errset( ivDRC( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
extA = errset( ivExtract( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)
procedure( mcpNum(v)
  if( floatp(v) || fixp(v) then float(v)
    else let((r) r = errset(cdfParseFloatString(v) nil) if(r && floatp(car(r)) then car(r) else 0.0))))
procedure( dumpNL(cvv fname)
  let( (op ni k nets)
    op = outfile(fname "w")
    ni = makeTable("ni" nil) k = 0
    nets = cvv~>nets
    foreach(n nets ni[n~>name] = k k = k+1)
    foreach(tm cvv~>terminals
      fprintf(op "t %d %s inputOutput\n" ni[tm~>net~>name] tm~>name))
    foreach(n nets fprintf(op "n %d /%s\n" ni[n~>name] n~>name))
    k = 0
    foreach(i cvv~>instances
      when( i~>cellName=="nmos2v"
        fprintf(op "; nmos2v Instance /%s = auLvs device M%d\n" i~>name k)
        fprintf(op "d nmos2v D G S B (p D S)\n")
        fprintf(op "i %d nmos2v" k)
        foreach(tn '("D" "G" "S" "B")
          let((it) it = car(setof(x i~>instTerms x~>name==tn))
            fprintf(op " %d" ni[it~>net~>name])))
        fprintf(op " \" m 1.0 l %g w %g \"\n" mcpNum(i~>l) mcpNum(i~>w))
        k = k+1))
    close(op)
    printf("MCP:dumped=%s devs=%d\n" fname k)))
system("mkdir -p ./CMPRUN/layout ./CMPRUN/schematic")
ext = dbOpenCellViewByType(lib "hsc_lay" "extracted" nil "r")
when(ext dumpNL(ext "./CMPRUN/layout/netlist")
  foreach(i ext~>instances
    when( i~>cellName=="nmos2v"
      printf("MCP:extmos %s w=%L %L\n" i~>name i~>w
        mapcar(lambda((it) list(it~>name it~>net~>name)) i~>instTerms)))))
sch = dbOpenCellViewByType(lib "hsc_core" "schematic" nil "r")
dumpNL(sch "./CMPRUN/schematic/netlist")
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA)
r = skill.run_skill(il, run_name="hsc_lay3",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    timeout=900)
open("designs/hscasc/build_lay3.log", "w", encoding="utf-8").write(r.log)
print("values:", {k: v for k, v in r.values.items() if "%" not in v})
i = r.log.find("Summary of rule violations")
print(r.log[i-60:i+500] if i >= 0 else "no DRC summary")
for l in r.log.splitlines():
    if "MCP:extmos" in l and "%" not in l: print(l[3:])

rb = vm.run_script(r'''
cd /home/work/mcp_skill_runs/hsc_lay3/CMPRUN
cp /home/work/gpdk090_v4.6/diva/divaLVS.rul .
cp /home/work/mcp_skill_runs/widlar_fix2/LVSrun/si.env . 2>/dev/null
LVS -dir . -l -s -x./xref.out -f -t layout schematic > lvsbin.log 2>&1
echo LVS_RC=$?
grep -E "net-lists|un-matched|size errors" lvsbin.log | head -8
''', timeout=400, tag="hsclvs2")
print(rb.log[-1500:])
