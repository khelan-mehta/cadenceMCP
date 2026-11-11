from cadence_mcp import spectre, config
MODEL = config.PDK_MODEL_INCLUDE
deck = f'''simulator lang=spectre
global 0
include "{MODEL}" section=NN
parameters rs=300k wn=3.12u ln=280n iref=100u
VDD (vdd 0) vsource dc=1.8
IREF (vdd nref) isource dc=iref
M1 (nref nref 0 0) gpdk090_nmos2v w=wn l=ln
M2 (nout nref ns 0) gpdk090_nmos2v w=wn l=ln
RS (ns 0) resistor r=rs
RL (vdd nout) resistor r=1M
* characterisation device: diode at swept current
IC (vdd nd) isource dc=1u
MC (nd nd 0 0) gpdk090_nmos2v w=wn l=ln
op dc oppoint=rawfile
info1 info what=oppoint where=file file="op.info"
swrs dc param=rs start=100k stop=500k step=1k
swic dc dev=IC param=dc start=0.1u stop=200u dec=40
'''
r = spectre.run_netlist(deck, run_name="widlar_size1")
print("ok", r.ok, r.errors)
for k,v in r.analyses.items():
    print(k, list(v.keys())[:10])
import json, pickle
pickle.dump(r, open("designs/widlar/size1.pkl","wb"))
for inst in ("M1","M2","MC"):
    d = r.opinfo.get(inst) or {}
    print(inst, {k:d.get(k) for k in ("id","vgs","vds","vth","vdsat","gm","gds","region")})
