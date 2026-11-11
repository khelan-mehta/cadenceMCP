"""Fix the 2 DRC issues (IREF notch; labels on pin purpose), re-run DRC,
extract, and LVS (foreground), reading back every LVS artifact."""
import re
from cadence_mcp import skill

DIVA = "/home/work/gpdk090_v4.6/diva"

il = r'''
printf("SKILL_START\n")
cv = dbOpenCellViewByType("widlar_lib" "widlar_lay" "layout" "maskLayout" "a")
; 1. move labels from ("Metal1" "pin") to ("Metal1" "drawing")
foreach(sh cv~>shapes
  when( sh~>objType=="label" && sh~>purpose=="pin"
    sh~>lpp = list("Metal1" "drawing")))
; 2. fill the connector/riser notches of the IREF plate (both devices)
nIREF = car(setof(n cv~>nets n~>name=="IREF"))
procedure( fillRect(x0 y0 x1 y1)
  dbAddFigToNet(dbCreateRect(cv list("Metal1" "drawing") list(x0:y0 x1:y1)) nIREF))
fillRect(0.08 3.26 0.58 3.72)
fillRect(6.08 3.26 6.58 3.72)
dbSave(cv)
printf("MCP:fixed=t\n")

drcA = errset( ivDRC( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
extA = errset( ivExtract( ?cell cv ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)
lvs1 = errset(
  ivLVS( "./LVSrun" "widlar_lib" "widlar_lay" "extracted" t
         "widlar_lib" "widlar_core" "schematic" t
         t nil t nil "" t 0 t "" "@DIVA@/divaLVS.rul" "" "" nil) t)
printf("MCP:lvs1=%L\n" errset(lvs1 nil))
foreach(f getDirFiles("./LVSrun") printf("MCP:lvsfile=%s\n" f))
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA)
r = skill.run_skill(il, run_name="widlar_fixdrc",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    read_back=["./LVSrun/si.out", "./LVSrun/si.foregnd.log",
                               "./LVSrun/si.env", "./LVSrun/layout/netlist",
                               "./LVSrun/schematic/netlist"],
                    timeout=900)
open("designs/widlar/fixdrc.log", "w", encoding="utf-8").write(r.log)
print("values:", r.values)
for name, body in r.files.items():
    print("=" * 20, name)
    print(body[-3500:])
tail = skill.ciw_tail(r.log, 16000)
keep = [l for l in tail.splitlines() if l.startswith("\\o") and
        re.search(r"rror|violat|Total|match|Match|terminated|Summary|net|device|run", l)]
print("\n".join(keep[-50:]))
