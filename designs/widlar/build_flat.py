"""Flat single-sheet Widlar schematic laid out exactly like the reference figure:
Vdd (left) | Iref over diode-connected M1 | gate bus with loop-over tie |
M2 with Rload above and Rs below | common ground rail with gnd symbol."""
import sys, re; sys.path.insert(0, "designs/widlar")
from vgui import run_gui

SEGS, SEGL = 28, 24.195
RTOT = 400 * SEGS * SEGL          # ohms
EFFL = SEGS * SEGL

il = r'''
printf("SKILL_START\n")
lib = "widlar_lib"
procedure( pinPt(inst tn)
  let( (mt fig)
    mt = car(setof(x inst~>master~>terminals x~>name==tn))
    fig = car(mt~>pins)~>fig
    dbTransformPoint(centerBox(fig~>bBox) inst~>transform)))
procedure( W(cv pts) schCreateWire(cv "route" "full" pts 0.0 0.0 0.0))
; place an instance so that terminal tn lands exactly at pt
procedure( placeAt(cv master name tn pt orient props)
  let( (i p)
    i = dbCreateParamInst(cv master name 0:0 orient 1 props)
    p = pinPt(i tn)
    i~>xy = list(xCoord(pt)-xCoord(p) yCoord(pt)-yCoord(p))
    i))
nm   = dbOpenCellViewByType("gpdk090" "nmos2v" "symbol" nil "r")
rpm  = dbOpenCellViewByType("gpdk090" "resnsppoly" "symbol" nil "r")
resM = dbOpenCellViewByType("analogLib" "res" "symbol" nil "r")
vdcM = dbOpenCellViewByType("analogLib" "vdc" "symbol" nil "r")
idcM = dbOpenCellViewByType("analogLib" "idc" "symbol" nil "r")
gndM = dbOpenCellViewByType("analogLib" "gnd" "symbol" nil "r")

cv = dbOpenCellViewByType(lib "widlar" "schematic" "schematic" "w")
mosP = list(list("model" "string" "gpdk090_nmos2v") list("w" "string" "3.12u") list("fw" "string" "1.56u")
            list("l" "string" "280n") list("fingers" "string" "2") list("m" "string" "1"))
M1 = dbCreateParamInst(cv nm "M1" 0:0 "MY" 1 mosP)
M2 = dbCreateParamInst(cv nm "M2" 3.0:0 "R0" 1 mosP)
d1 = pinPt(M1 "D") s1 = pinPt(M1 "S") b1 = pinPt(M1 "B") g1 = pinPt(M1 "G")
d2 = pinPt(M2 "D") s2 = pinPt(M2 "S") b2 = pinPt(M2 "B") g2 = pinPt(M2 "G")
xd1 = xCoord(d1) xd2 = xCoord(d2)
yTop = 3.5  yBot = -2.5  xj = 1.75  yA = 1.0  xV = -4.0

rsP = list(list("model" "string" "gpdk090_resnsppoly") list("segments" "int" @SEGS@) list("ssegs" "int" @SEGS@)
           list("psegs" "int" 1) list("segW" "string" "1u") list("segL" "string" "@SEGL@u")
           list("r" "string" "@RVAL@") list("segR" "string" "@SEGR@")
           list("effW" "string" "1u") list("effL" "string" "@EFFL@u")
           list("w" "string" "1u") list("l" "string" "@EFFL@u"))
Rs    = placeAt(cv rpm  "Rs"    "PLUS"  list(xd2 -1.25) "R0" rsP)
Rload = placeAt(cv resM "Rload" "MINUS" list(xd2 1.5)  "R0" list(list("r" "string" "1M")))
Iref  = placeAt(cv idcM "Iref"  "MINUS" list(xd1 1.75) "R0" list(list("idc" "string" "100u")))
Vdd   = placeAt(cv vdcM "Vdd"   "PLUS"  list(xV 2.25)  "R0" list(list("vdc" "string" "1.8")))
rp = pinPt(Rs "PLUS") rm = pinPt(Rs "MINUS") rb = pinPt(Rs "B")
lp = pinPt(Rload "PLUS") lm = pinPt(Rload "MINUS")
ip = pinPt(Iref "PLUS")  im = pinPt(Iref "MINUS")
vp = pinPt(Vdd "PLUS")   vm = pinPt(Vdd "MINUS")

; top rail
W(cv list(vp xV:yTop))
W(cv list(xV:yTop xd1:yTop))
W(cv list(xd1:yTop xd2:yTop))
W(cv list(ip xd1:yTop))
W(cv list(lp xd2:yTop))
; Iref -> M1 drain, with diode-tie junction at yA
W(cv list(im xd1:yA))
W(cv list(xd1:yA d1))
W(cv list(xd1:yA xj:yA))
W(cv list(xj:yA xj:0.0))
; gate bus
W(cv list(g1 xj:0.0))
W(cv list(xj:0.0 g2))
; Rload -> M2 drain
W(cv list(lm d2))
; M2 source -> Rs
W(cv list(s2 rp))
; ground returns
W(cv list(vm xV:yBot))
W(cv list(xV:yBot xd2:yBot))
W(cv list(rm xd2:yBot))
W(cv list(s1 xCoord(s1):yBot))
W(cv list(b1 -0.75:yCoord(b1)))
W(cv list(-0.75:yCoord(b1) -0.75:yBot))
W(cv list(b2 3.75:yCoord(b2)))
W(cv list(3.75:yCoord(b2) 3.75:-0.8))
W(cv list(3.75:-0.8 4.25:-0.8))
W(cv list(4.25:-0.8 4.25:yBot))
W(cv list(rb 4.25:yCoord(rb)))
W(cv list(xd2:yBot 4.25:yBot))
G0 = placeAt(cv gndM "G0" "gnd!" list(1.5 yBot) "R0" nil)
chk = schCheck(cv)
printf("MCP:flatcheck=%L\n" chk)
dbSave(cv)
printf("MCP:flat_nets=%L\n" cv~>nets~>name)
foreach(i list(M1 M2 Rs Rload Iref Vdd G0)
  foreach(it i~>instTerms printf("MCP:conn %s.%s=%s\n" i~>name it~>name it~>net~>name)))

w1 = geOpen(?lib lib ?cell "widlar" ?view "schematic" ?mode "r")
hiResizeWindow(hiGetCurrentWindow() list(0:0 1600:1000))
procedure(wlA() errset(evalstring(hiGetBindKey("Schematics" "<Key>f")) t) hiRegTimer("wlB()" 30))
procedure(wlB() mcpShot("sch_flat") printf("MCP:OK=1\n") exit(0))
hiRegTimer("wlA()" 40)
'''
for k, v in {"@SEGS@": str(SEGS), "@SEGL@": f"{SEGL}", "@RVAL@": f"{RTOT:.6g}",
             "@SEGR@": f"{RTOT/SEGS:.6g}", "@EFFL@": f"{EFFL:.4f}"}.items():
    il = il.replace(k, v)
log, got, _ = run_gui(il, shots=["sch_flat"], timeout=700, tag="flat")
open("designs/widlar/build_flat.log", "w", encoding="utf-8").write(log)
print(got)
lines = re.findall(r"MCP:[^\n]*|\*Error\*[^\n]*", log)
print("\n".join(lines)[:6000])

# ---- hard verification of connectivity ----
conn = dict(re.findall(r"MCP:conn (\S+)=(\S+)", log))
nets = {}
for term, net in conn.items():
    nets.setdefault(net, set()).add(term)
groups = {frozenset(v) for v in nets.values()}
want = [
    {"Vdd.PLUS", "Iref.PLUS", "Rload.PLUS"},
    {"Iref.MINUS", "M1.D", "M1.G", "M2.G"},
    {"Rload.MINUS", "M2.D"},
    {"M2.S", "Rs.PLUS"},
    {"Vdd.MINUS", "M1.S", "M1.B", "M2.B", "Rs.MINUS", "Rs.B", "G0.gnd!"},
]
ok = all(frozenset(w) in groups for w in want) and len(nets) == 5
print("CONNECTIVITY", "PASS" if ok else "FAIL", {k: sorted(v) for k, v in nets.items()})
