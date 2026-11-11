"""Final capture session: verified-layout shots, op-annotated schematic,
and ViVA waveform shots driven by iterating results() names directly."""
import sys, re; sys.path.insert(0, "designs/widlar")
from vgui import run_gui

il = r'''
printf("SKILL_START\n")
RUNS = "/home/work/mcp_runs"

; ---------- annotate flat schematic (clean slate, correct 8-arg call) ----------
cv = dbOpenCellViewByType("widlar_lib" "widlar" "schematic" "schematic" "a")
foreach(sh cv~>shapes
  when( sh~>objType=="label" && sh~>layerName=="annotate" dbDeleteObject(sh)))
procedure( NOTE(x y txt)
  let((r)
    r = errset(schCreateNoteLabel(cv list(x y) txt "lowerLeft" "R0" "stick" 0.14 nil) nil)
    unless( r && car(r)
      errset(dbCreateLabel(cv list("annotate" "drawing") list(x y) txt "lowerLeft" "R0" "stick" 0.14) nil))))
NOTE(3.6 0.75 "id=1.00001u")
NOTE(3.6 0.55 "vgs=569.70m")
NOTE(3.6 0.35 "vds=529.05m")
NOTE(3.6 0.15 "gm=23.813u")
NOTE(-2.3 0.75 "id=100.0u")
NOTE(-2.3 0.55 "vgs=840.68m")
NOTE(-2.3 0.35 "gm=544.79u")
NOTE(-0.15 1.2 "840.68m")
NOTE(3.4 -0.85 "270.98m")
NOTE(3.4 1.2 "800.03m")
NOTE(-3.9 3.6 "1.8V")
NOTE(1.3 -2.3 "IOUT=999.97n")
dbSave(cv)
printf("MCP:annotated=t\n")

procedure( plotFromRun(dir exprs)
  let( (rs ok)
    openResults(dir)
    rs = results()
    printf("MCP:results %s = %L\n" dir rs)
    ok = nil
    foreach(rr rs
      unless(ok
        when( errset(selectResult(rr) nil)
          when( car(errset(getData(car(exprs)) nil))
            ok = rr)))
      )
    when(ok selectResult(ok)
      foreach(e exprs errset(plot(getData(e)) t)))
    printf("MCP:plotted %s via %L\n" dir ok)))
procedure( plotNamed(dir rname exprs)
  openResults(dir)
  when( errset(selectResult(rname) nil)
    foreach(e exprs errset(plot(getData(e)) t))
    printf("MCP:plotnamed %s %L ok\n" dir rname)))

state = 0
w0 = nil wl = nil
procedure( nextStep()
  state = state+1
  printf("MCP:step=%d\n" state)
  case( state
    (1  wl = geOpen(?lib "widlar_lib" ?cell "widlar_lay" ?view "layout" ?mode "r")
        hiSetCurrentWindow(wl)
        hiResizeWindow(wl list(0:0 1600:1000))
        errset(evalstring(hiGetBindKey("Layout" "Shift<Key>f")) t)
        errset(evalstring(hiGetBindKey("Layout" "<Key>f")) t)
        hiRegTimer("nextStep()" 40))
    (2  mcpShot("lay_final_full")
        errset(hiZoomIn(wl list(-2.5:-4.0 10.5:4.5)) t)
        hiRegTimer("nextStep()" 30))
    (3  mcpShot("lay_final_mos")
        errset(hiCloseWindow(wl) t)
        w0 = geOpen(?lib "widlar_lib" ?cell "widlar" ?view "schematic" ?mode "r")
        hiSetCurrentWindow(w0)
        hiResizeWindow(w0 list(0:0 1600:1000))
        errset(evalstring(hiGetBindKey("Schematics" "<Key>f")) t)
        hiRegTimer("nextStep()" 40))
    (4  mcpShot("sch_annot")
        errset(hiCloseWindow(w0) t)
        plotFromRun(strcat(RUNS "/widlar_swrs/psf") list("RL:1"))
        hiRegTimer("nextStep()" 60))
    (5  mcpShot("p_swrs")
        clearAll() newWindow()
        plotNamed(strcat(RUNS "/widlar_main/psf") "swvdd-dc" list("RL:1" "VDD:p"))
        hiRegTimer("nextStep()" 60))
    (6  mcpShot("p_swvdd")
        clearAll() newWindow()
        plotNamed(strcat(RUNS "/widlar_main/psf") "swsegl-dc" list("RL:1"))
        hiRegTimer("nextStep()" 60))
    (7  mcpShot("p_segl")
        clearAll() newWindow()
        plotNamed(strcat(RUNS "/widlar_main/psf") 'tran list("RL:1"))
        hiRegTimer("nextStep()" 60))
    (8  mcpShot("p_tran")
        clearAll() newWindow()
        plotFromRun(strcat(RUNS "/widlar_compl/psf") list("M2:d"))
        hiRegTimer("nextStep()" 60))
    (9  mcpShot("p_vout") printf("MCP:OK=1\n") exit(0))
  ))
hiRegTimer("nextStep()" 40)
'''
log, got, _ = run_gui(il, shots=["lay_final_full", "lay_final_mos", "sch_annot",
                                 "p_swrs", "p_swvdd", "p_segl", "p_tran", "p_vout"],
                      timeout=900, tag="final")
open("designs/widlar/final_shots.log", "w", encoding="utf-8").write(log)
print(got)
print("\n".join(l for l in re.findall(r"MCP:[^\n]*|\*Error\*[^\n]*", log) if "%" not in l)[:5000])
