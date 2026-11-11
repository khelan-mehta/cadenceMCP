"""Full characterization of the Widlar mirror.

Runs:
  A: ideal-RS fine sweep        -> IOUT(RS), pick RS for 1 uA
  B: pcell poly RS (w/l form)   -> op + op.info, segL sweep, VDD sweep, transient
  C: output compliance          -> IOUT vs VOUT (vsource on output)
The poly resistor spectre subckt is gpdk090_resnsppoly (PLUS MINUS B) w/ params w,l;
R = rsh*l/w = 400 * l/w.  28 segments x 24.195u x 1u wide -> 270.98k.
"""
import pickle
import sys
from cadence_mcp import spectre, config

MODEL = config.PDK_MODEL_INCLUDE
EFFL = 28 * 24.195   # um

HDR = f'''simulator lang=spectre
global 0
include "{MODEL}" section=NN
parameters vdd=1.8 iref=100u reff={EFFL}u wn=3.12u ln=280n
'''

CORE_PCELL = '''VDD (vdd 0) vsource dc=vdd
IREF (vdd nref) isource dc=iref
M1 (nref nref 0 0) gpdk090_nmos2v w=wn l=ln fingers=2 fw=wn/2
M2 (nout nref ns 0) gpdk090_nmos2v w=wn l=ln fingers=2 fw=wn/2
RS (ns 0 0) gpdk090_resnsppoly w=1u l=reff
opts options save=allpub currents=all
'''

deckA = HDR + '''VDD (vdd 0) vsource dc=vdd
IREF (vdd nref) isource dc=iref
M1 (nref nref 0 0) gpdk090_nmos2v w=wn l=ln fingers=2 fw=wn/2
M2 (nout nref ns 0) gpdk090_nmos2v w=wn l=ln fingers=2 fw=wn/2
RS (ns 0) resistor r=rsx
RL (vdd nout) resistor r=1M
parameters rsx=271k
opts options save=allpub currents=all
swrs dc param=rsx start=150k stop=400k step=500
'''

deckB = HDR + CORE_PCELL + '''RL (vdd nout) resistor r=1M
op dc oppoint=rawfile
info1 info what=oppoint where=file file="op.info"
swsegl dc param=reff start=500u stop=850u step=1u
swvdd dc dev=VDD param=dc start=0 stop=1.8 step=5m
tr tran stop=100u
'''

deckC = HDR + CORE_PCELL + '''VOUT (nout 0) vsource dc=0.9
swvout dc dev=VOUT param=dc start=0 stop=1.8 step=5m
'''

if __name__ == "__main__":
    sel = sys.argv[1] if len(sys.argv) > 1 else "ABC"
    if "A" in sel:
        r = spectre.run_netlist(deckA, run_name="widlar_swrs")
        print("A ok", r.ok, r.errors)
        pickle.dump(r, open("designs/widlar/simA.pkl", "wb"))
        if not r.ok:
            i = r.log.find("ERROR"); print(r.log[max(0, i-200):i+800])
    if "B" in sel:
        r = spectre.run_netlist(deckB, run_name="widlar_main")
        print("B ok", r.ok, r.errors)
        pickle.dump(r, open("designs/widlar/simB.pkl", "wb"))
        if not r.ok:
            i = r.log.find("ERROR"); print(r.log[max(0, i-200):i+800])
    if "C" in sel:
        r = spectre.run_netlist(deckC, run_name="widlar_compl")
        print("C ok", r.ok, r.errors)
        pickle.dump(r, open("designs/widlar/simC.pkl", "wb"))
        if not r.ok:
            i = r.log.find("ERROR"); print(r.log[max(0, i-200):i+800])
