"""Open the Spectre PSF results in Virtuoso (OCEAN/ViVA) and screenshot each graph:
  p_swrs  : IOUT vs RS (ideal-R sweep)        - reference Fig 2 analogue
  p_swvdd : IOUT + supply current vs VDD      - reference Fig 3 analogue
  p_vout  : IOUT vs VOUT (output compliance)
  p_tran  : IOUT vs time (steady 1 uA)
  p_segl  : IOUT vs poly resistor length (design centering)
Also annotates the flat schematic with the simulated DC operating point."""
import sys, re; sys.path.insert(0, "designs/widlar")
from vgui import run_gui

il = r'''
printf("SKILL_START\n")
RUNS = "/home/work/mcp_runs"

procedure( shotWin(name)
  hiRedraw() mcpShot(name))

; ---------- annotate flat schematic with the DC op point ----------
cv = dbOpenCellViewByType("widlar_lib" "widlar" "schematic" "schematic" "a")
procedure( NOTE(cv x y txt)
  let((r) r = errset(schCreateNoteLabel(cv list(x y) txt "lowerLeft" "R0" "stick" 0.14) t)
    unless(r errset(dbCreateLabel(cv list("annotate" "drawing") list(x y) txt "lowerLeft" "R0" "stick" 0.14) t))))
NOTE(cv 3.6 0.55 "id=1.00001u")
NOTE(cv 3.6 0.35 "vgs=569.70m")
NOTE(cv 3.6 0.15 "vds=529.05m")
NOTE(cv 3.6 -0.05 "gm=23.813u")
NOTE(cv -1.6 0.55 "id=100.0u")
NOTE(cv -1.6 0.35 "vgs=840.68m")
NOTE(cv -1.6 0.15 "gm=544.79u")
NOTE(cv -0.2 1.1 "840.68m")
NOTE(cv 3.35 -0.75 "270.98m")
NOTE(cv 3.35 1.1 "800.03m")
NOTE(cv -3.9 3.6 "1.8")
NOTE(cv 4.4 -32.0 "IOUT=999.97n")
dbSave(cv)
printf("MCP:annotated=t\n")
w0 = geOpen(?lib "widlar_lib" ?cell "widlar" ?view "schematic" ?mode "r")
hiResizeWindow(hiGetCurrentWindow() list(0:0 1600:1000))

state = 0
procedure( nextStep()
  state = state+1
  printf("MCP:step=%d\n" state)
  case( state
    (1  errset(evalstring(hiGetBindKey("Schematics" "<Key>f")) t) hiRegTimer("nextStep()" 30))
    (2  shotWin("sch_annot")
        errset(hiCloseWindow(w0) t)
        ; ---------- swrs ----------
        openResults(strcat(RUNS "/widlar_swrs/psf"))
        printf("MCP:res_swrs=%L\n" results())
        selectResult('swrs)
        plot(getData("RL:1") ?expr list("IOUT (A) vs RS (ohm)"))
        hiRegTimer("nextStep()" 50))
    (3  shotWin("p_swrs")
        clearAll() newWindow()
        openResults(strcat(RUNS "/widlar_main/psf"))
        printf("MCP:res_main=%L\n" results())
        selectResult('swvdd)
        plot(getData("RL:1") ?expr list("IOUT (A)"))
        plot(getData("VDD:p") ?expr list("I(VDD) (A)"))
        hiRegTimer("nextStep()" 50))
    (4  shotWin("p_swvdd")
        clearAll() newWindow()
        selectResult('swsegl)
        plot(getData("RL:1") ?expr list("IOUT (A) vs poly length (m)"))
        hiRegTimer("nextStep()" 50))
    (5  shotWin("p_segl")
        clearAll() newWindow()
        selectResult('tr)
        plot(getData("RL:1") ?expr list("IOUT (A) vs time"))
        hiRegTimer("nextStep()" 50))
    (6  shotWin("p_tran")
        clearAll() newWindow()
        openResults(strcat(RUNS "/widlar_compl/psf"))
        printf("MCP:res_compl=%L\n" results())
        selectResult('swvout)
        plot(getData("M2:d") ?expr list("IOUT = ID(M2) (A) vs VOUT (V)"))
        hiRegTimer("nextStep()" 50))
    (7  shotWin("p_vout") printf("MCP:OK=1\n") exit(0))
  ))
hiRegTimer("nextStep()" 40)
'''
log, got, _ = run_gui(il, shots=["sch_annot", "p_swrs", "p_swvdd", "p_segl", "p_tran", "p_vout"],
                      timeout=900, tag="plots")
open("designs/widlar/plots.log", "w", encoding="utf-8").write(log)
print(got)
print("\n".join(re.findall(r"MCP:[^\n]*|\*Error\*[^\n]*", log))[:7000])
