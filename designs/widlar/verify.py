"""DRC + extract + LVS, headless. ivDRC/ivExtract with ?rulesFromUnix t;
ivLVS positional with runInBg nil so the boot waits for completion."""
import re
from cadence_mcp import skill

DIVA = "/home/work/gpdk090_v4.6/diva"

il = r'''
printf("SKILL_START\n")
lay = dbOpenCellViewByType("widlar_lib" "widlar_lay" "layout" "maskLayout" "a")
printf("MCP:open=%L\n" lay!=nil)
drcA = errset( ivDRC( ?cell lay ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaDRC.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:drcA=%L\n" drcA)
unless( drcA && car(drcA)
  drcB = errset( ivDRC( ?cell lay ?rulesFilePath "divaDRC.rul" ?rulesLibName "gpdk090" ?hier t ?echo t) t)
  printf("MCP:drcB=%L\n" drcB))
extA = errset( ivExtract( ?cell lay ?rulesFromUnix t ?rulesFilePath "@DIVA@/divaEXT.rul" ?rulesLibName "" ?hier t ?echo t) t)
printf("MCP:extA=%L\n" extA)
unless( extA && car(extA)
  extB = errset( ivExtract( ?cell lay ?rulesFilePath "divaEXT.rul" ?rulesLibName "gpdk090" ?hier t ?echo t) t)
  printf("MCP:extB=%L\n" extB))
printf("MCP:extview=%L\n" ddGetObj("widlar_lib" "widlar_lay" "extracted")!=nil)
lvs1 = errset(
  ivLVS( "./LVSrun" "widlar_lib" "widlar_lay" "extracted" t
         "widlar_lib" "widlar_core" "schematic" t
         t nil t nil "" t 0 t "" "@DIVA@/divaLVS.rul" "" "" nil) t)
printf("MCP:lvs1=%L\n" lvs1)
foreach(f getDirFiles("./LVSrun") printf("MCP:lvsfile=%s\n" f))
printf("MCP:OK=1\n")
exit(0)
'''.replace("@DIVA@", DIVA)
r = skill.run_skill(il, run_name="widlar_verify4",
                    extra_defines=["DEFINE widlar_lib /home/work/widlar_lib"],
                    read_back=["./LVSrun/si.out", "./LVSrun/lvs.rep", "./LVSrun/si.log"],
                    timeout=900)
open("designs/widlar/verify4.log", "w", encoding="utf-8").write(r.log)
print("values:", r.values)
for name, body in r.files.items():
    print("=" * 20, name)
    print(body[-4000:])
tail = skill.ciw_tail(r.log, 16000)
keep = [l for l in tail.splitlines() if not l.startswith("\\i") and
        re.search(r"rror|violat|Total|rules|RESULT|match|Match|terminated|DRC|Extract|saved|net|device", l)]
print("\n".join(keep[-80:]))
