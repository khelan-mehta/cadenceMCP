"""High-swing cascode mirror layout + DRC + extract + netlist dump + LVS.
Floorplan: bottom row M0(x0,tap Int), M1(x6,Int), M2(x12,Int); top row M3(x6),
M4(x12) tap=None. Metal1 only. Routing coordinates from termBox queries plus
the verified S-col metal offset (origin-0.24 .. origin-0.12) for tap=None."""
import re
from cadence_mcp import skill, vm

DIVA = "/home/work/gpdk090_v4.6/diva"

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
cv = dbOpenCellViewByType(lib "hsc_lay" "layout" "maskLayout" "w")
pInt = list(list("l" "float" 1e-6) list("fingers" "int" 1)
            list("tap" "string" "Integrated") list("connectGates" "string" "Top"))
pNone = list(list("l" "float" 1e-6) list("fingers" "int" 1)
             list("tap" "string" "None") list("connectGates" "string" "Top"))
M0 = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M0" 0:0 "R0" 1
      cons(list("fw" "float" 3e-6) pInt))
MA = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M1" 6.0:0 "R0" 1
      cons(list("fw" "float" 12e-6) pInt))
MB = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M2" 12.0:0 "R0" 1
      cons(list("fw" "float" 12e-6) pInt))
MC = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M3" 6.0:16.0 "R0" 1
      cons(list("fw" "float" 12e-6) pNone))
MD = dbCreateParamInstByMasterName(cv "gpdk090" "nmos2v" "layout" "M4" 12.0:16.0 "R0" 1
      cons(list("fw" "float" 12e-6) pNone))
d0=termBox(M0 "D") g0=termBox(M0 "G") b0=termBox(M0 "B")
d1=termBox(MA "D") g1=termBox(MA "G") b1=termBox(MA "B")
d2=termBox(MB "D") g2=termBox(MB "G") b2=termBox(MB "B")
d3=termBox(MC "D") g3=termBox(MC "G")
d4=termBox(MD "D") g4=termBox(MD "G")
printf("MCP:t d0=%L g0=%L b0=%L\n" d0 g0 b0)
printf("MCP:t d3=%L g3=%L d4=%L g4=%L\n" d3 g3 d4 g4)
; tap=None source-column metal (verified offset: origin-0.24 .. origin-0.12)
s3x0 = 6.0-0.24  s3x1 = 6.0-0.12
s4x0 = 12.0-0.24 s4x1 = 12.0-0.12
nGND=dbCreateNet(cv "GND") nVB=dbCreateNet(cv "IBIAS") nIN=dbCreateNet(cv "IIN")
nNA=dbCreateNet(cv "NA") nNB=dbCreateNet(cv "NB") nOUT=dbCreateNet(cv "IOUT")
; ---- GND rail + integrated-tap drops ----
netRect(cv nGND -2.0 -2.0 14.5 -1.6)
foreach(bb list(b0 b1 b2)
  netRect(cv nGND xCoord(lowerLeft(bb)) -1.6 xCoord(upperRight(bb)) 0.1))
mkPin(cv nGND 2.0 -2.0 2.5 -1.6)
; ---- vb: M0 diode plate + left leg + top bar + strap drops ----
; solid plate over M0 G strap + D column top
netRect(cv nVB xCoord(lowerLeft(g0))+0.08 yCoord(lowerLeft(g0))
            xCoord(upperRight(d0)) yCoord(upperRight(g0))+0.26)
barY0 = yCoord(upperRight(g0))+0.14  barY1 = yCoord(upperRight(g0))+0.26
netRect(cv nVB -1.0 barY0 xCoord(upperRight(d0)) barY1)
vbY0 = yCoord(upperRight(g3))+0.14  vbY1 = yCoord(upperRight(g3))+0.26
netRect(cv nVB -1.0 barY0 -0.88 vbY1)
netRect(cv nVB -2.0 vbY0 12.12 vbY1)
; drops onto cascode gate straps (left edge of each strap)
netRect(cv nVB xCoord(lowerLeft(g3)) yCoord(upperRight(g3))-0.06 xCoord(lowerLeft(g3))+0.12 vbY1)
netRect(cv nVB xCoord(lowerLeft(g4)) yCoord(upperRight(g4))-0.06 xCoord(lowerLeft(g4))+0.12 vbY1)
mkPin(cv nVB -2.0 vbY0 -1.5 vbY1)
; ---- IIN: bottom gate bar (M1.G+M2.G) + tie up into M3.D col ----
gbY0 = yCoord(lowerLeft(g1))  gbY1 = yCoord(upperRight(g1))
netRect(cv nIN 4.8 gbY0 xCoord(upperRight(g2)) gbY1)
netRect(cv nIN xCoord(lowerLeft(d3)) gbY0 xCoord(lowerLeft(d3))+0.12 16.1)
mkPin(cv nIN 4.8 gbY0 5.3 gbY1)
; ---- NA: M3.S col down, jog right, into M1.D col top ----
netRect(cv nNA s3x0 14.8 s3x1 16.0)
netRect(cv nNA s3x0 14.8 xCoord(upperRight(d1)) 14.92)
netRect(cv nNA xCoord(upperRight(d1))-0.12 11.9 xCoord(upperRight(d1)) 14.92)
; ---- NB: M4.S col down, jog right (above gate bar), into M2.D col top ----
netRect(cv nNB s4x0 15.5 s4x1 16.0)
netRect(cv nNB s4x0 15.5 xCoord(upperRight(d2)) 15.62)
netRect(cv nNB xCoord(upperRight(d2))-0.12 11.9 xCoord(upperRight(d2)) 15.62)
; ---- IOUT: M4.D col exits right ----
netRect(cv nOUT xCoord(upperRight(d4)) 16.0 14.5 16.12)
netRect(cv nOUT xCoord(lowerLeft(d4)) 16.0 xCoord(upperRight(d4)) 16.12)
mkPin(cv nOUT 14.0 16.0 14.5 16.12)
printf("MCP:routed=t\n")
dbSave(cv)
drcA = errset( ivDRC( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
extA = errset( ivExtract( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)

; ---- netlist dump (auLvs simple-file format) ----
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
when(ext dumpNL(ext "./CMPRUN/layout/netlist"))
sch = dbOpenCellViewByType(lib "hsc_core" "schematic" nil "r")
dumpNL(sch "./CMPRUN/schematic/netlist")
when(ext
  foreach(i ext~>instances
    when( i~>cellName=="nmos2v"
      printf("MCP:extmos %s w=%L %L\n" i~>name i~>w
        mapcar(lambda((it) list(it~>name it~>net~>name)) i~>instTerms)))))
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA)
r = skill.run_skill(il, run_name="hsc_lay1",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    read_back=["./CMPRUN/layout/netlist", "./CMPRUN/schematic/netlist"],
                    timeout=900)
open("designs/hscasc/build_lay.log", "w", encoding="utf-8").write(r.log)
print("values:", {k: v for k, v in r.values.items() if "%" not in v})
i = r.log.find("Summary of rule violations")
print(r.log[i-60:i+500] if i >= 0 else "no DRC summary")
j = r.log.find("Summary of rule violations", i+10) if i >= 0 else -1
print(r.log[j-60:j+300] if j >= 0 else "")
for name, body in r.files.items():
    print("=" * 20, name); print(body[:1500])

rb = vm.run_script(r'''
cd /home/work/mcp_skill_runs/hsc_lay1/CMPRUN
cp /home/work/gpdk090_v4.6/diva/divaLVS.rul .
cp /home/work/mcp_skill_runs/widlar_fix2/LVSrun/si.env . 2>/dev/null
LVS -dir . -l -s -x./xref.out -f -t layout schematic > lvsbin.log 2>&1
echo LVS_RC=$?
grep -E "match|un-matched|size errors|summary" lvsbin.log | head -20
''', timeout=400, tag="hsclvs")
print(rb.log[-2500:])
