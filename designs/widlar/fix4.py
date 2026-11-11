"""Layout fix 3: NS rerouted down the RIGHT side (no crossing of M1's GND drop).
Rebuild -> DRC -> extract -> dump auLvs-format netlists from the REAL extracted
view + schematic -> run the LVS comparator binary. One boot + one bash step."""
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
d2 = termBox(MB "D") g2 = termBox(MB "G")
rp = termBox(RS "PLUS") rm = termBox(RS "MINUS") rb = termBox(RS "B")
nIREF = dbCreateNet(cv "IREF") nIOUT = dbCreateNet(cv "IOUT")
nGND = dbCreateNet(cv "GND")  nNS  = dbCreateNet(cv "NS")
railY0 = -2.0 railY1 = -1.6
netRect(cv nGND -1.0 railY0 45.0 railY1)
netRect(cv nGND xCoord(lowerLeft(b1)) railY1 xCoord(upperRight(b1)) 0.1)
netRect(cv nGND xCoord(lowerLeft(rm)) yCoord(lowerLeft(rm)) 45.0 yCoord(upperRight(rm)))
netRect(cv nGND 44.88 yCoord(lowerLeft(rm)) 45.0 railY1)
netRect(cv nGND xCoord(lowerLeft(rb)) yCoord(upperRight(rb))-0.1 xCoord(upperRight(rb)) railY1)
; NS: M2 source col -> channel RIGHT -> down the right edge -> under the array -> up into PLUS
netRect(cv nNS 5.76 -1.1 5.88 0.1)
netRect(cv nNS 5.76 -1.1 46.12 -0.9)
netRect(cv nNS 46.0 -33.0 46.12 -0.9)
netRect(cv nNS 0.44 -33.0 46.12 -32.88)
netRect(cv nNS 0.44 -33.0 0.56 yCoord(lowerLeft(rp))+0.1)
dx0 = xCoord(lowerLeft(d1)) dx1 = xCoord(upperRight(d1))
barY0 = 3.6 barY1 = 3.72
netRect(cv nIREF dx0 yCoord(upperRight(d1))-0.1 dx1 barY1)
netRect(cv nIREF -1.4 barY0 xCoord(upperRight(g2))-0.02 barY1)
netRect(cv nIREF 0.08 3.26 dx1 barY1)
netRect(cv nIREF 6.08 3.26 xCoord(upperRight(d2)) barY1)
ox0 = xCoord(lowerLeft(d2)) ox1 = xCoord(upperRight(d2))
netRect(cv nIOUT ox0 -0.7 ox1 0.1)
netRect(cv nIOUT ox0 -0.7 8.3 -0.58)
mkPin(cv nIREF -1.4 barY0 -0.9 barY1)
mkPin(cv nIOUT 7.8 -0.7 8.3 -0.58)
mkPin(cv nGND 4.0 railY0 4.5 railY1)
printf("MCP:routed=t\n")
dbSave(cv)
drcA = errset( ivDRC( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
extA = errset( ivExtract( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)

; ---------- netlist dumper (auLvs 'simple file' format) ----------
procedure( mcpNum(v)
  if( floatp(v) || fixp(v) then float(v)
    else let((r) r = errset(cdfParseFloatString(v) nil) if(r && floatp(car(r)) then car(r) else 0.0))))
procedure( dumpNL(cv fname termOrderTbl)
  let( (op ni k nets)
    op = outfile(fname "w")
    ni = makeTable("ni" nil)
    k = 0
    nets = cv~>nets
    foreach(n nets ni[n~>name] = k k = k+1)
    foreach(tm cv~>terminals
      fprintf(op "t %d %s inputOutput\n" ni[tm~>net~>name] tm~>name))
    foreach(n nets fprintf(op "n %d /%s\n" ni[n~>name] n~>name))
    k = 0
    foreach(i cv~>instances
      let( (cn tl)
        cn = i~>cellName
        tl = termOrderTbl[cn]
        when( tl
          fprintf(op "; %s Instance /%s = auLvs device M%d\n" cn i~>name k)
          fprintf(op "d %s %s (p %s)\n" cn buildString(car(tl) " ") buildString(cadr(tl) " "))
          fprintf(op "i %d %s" k cn)
          foreach(tn car(tl)
            let((it) it = car(setof(x i~>instTerms x~>name==tn))
              fprintf(op " %d" ni[it~>net~>name])))
          if( cn=="resnsppoly" then
            fprintf(op " \" l %g w %g \"\n" mcpNum(i~>l) mcpNum(i~>w))
          else
            fprintf(op " \" m 1.0 l %g w %g \"\n" mcpNum(i~>l) mcpNum(i~>w)))
          k = k+1)))
    close(op)
    printf("MCP:dumped=%s devs=%d\n" fname k)))
tord = makeTable("to" nil)
tord["nmos2v"] = list(list("D" "G" "S" "B") list("D" "S"))
tord["resnsppoly"] = list(list("PLUS" "MINUS" "B") list("PLUS" "MINUS"))
system("mkdir -p ./CMPRUN/layout ./CMPRUN/schematic")
ext = dbOpenCellViewByType(lib "widlar_lay" "extracted" nil "r")
dumpNL(ext "./CMPRUN/layout/netlist" tord)
sch = dbOpenCellViewByType(lib "widlar_core" "schematic" nil "r")
dumpNL(sch "./CMPRUN/schematic/netlist" tord)
; sanity: print NS connectivity of the new extract
foreach(i ext~>instances
  when( i~>cellName=="nmos2v"
    printf("MCP:extmos %s %L\n" i~>name mapcar(lambda((it) list(it~>name it~>net~>name)) i~>instTerms))))
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA).replace("@SEGS@", str(SEGS)).replace("@SEGL@", f"{SEGL}")
r = skill.run_skill(il, run_name="widlar_fix4",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    read_back=["./CMPRUN/layout/netlist", "./CMPRUN/schematic/netlist"],
                    timeout=900)
open("designs/widlar/fix4.log", "w", encoding="utf-8").write(r.log)
print("values:", {k: v for k, v in r.values.items() if "%" not in v})
i = r.log.find("Summary of rule violations")
print(r.log[i-60:i+400] if i >= 0 else "no DRC summary")
for name, body in r.files.items():
    print("=" * 20, name)
    print(body[:1800])

rb = vm.run_script(r'''
cd /home/work/mcp_skill_runs/widlar_fix4/CMPRUN
cp /home/work/gpdk090_v4.6/diva/divaLVS.rul .
cp /home/work/mcp_skill_runs/widlar_fix2/LVSrun/si.env . 2>/dev/null
LVS -dir . -l -s -x./xref.out -f -t layout schematic > lvsbin.log 2>&1
echo LVS_RC=$?
echo ==== si.out ====
cat si.out 2>/dev/null
''', timeout=400, tag="lvsbin")
print(rb.log[-5000:])
