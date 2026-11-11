"""High-swing (Sooch) cascode current mirror - gpdk090 nmos2v, L=1u, 100uA.

Topology (matches the reference schematic image):
  M0: W=wb, diode (G=D), fed by I0=100u  -> Vb = VTH + 2*Vov   (cascode bias)
  M3: W=w,  G=Vb, D=nin (I1=100u), S=na
  M1: W=w,  G=nin (gate driven from the INPUT node, the wide-swing tie), S=0
  M4: W=w,  G=Vb, D=nout, S=nb
  M2: W=w,  G=na, D=nb, S=0
Run A: op + compliance sweep + VDD sweep + AC Rout + transient (100mV/1kHz on out)
Run B: comparison - simple mirror vs conventional cascode vs high-swing,
       all 100uA, one shared swept output voltage vx -> 3 curves.
"""
import pickle, sys
import numpy as np
from cadence_mcp import spectre, config

MODEL = config.PDK_MODEL_INCLUDE
HDR = f'''simulator lang=spectre
global 0
include "{MODEL}" section=NN
parameters vdd=1.8 iref=100u w=12u wb=3u l=1u vx=0.9
'''

CORE = '''VDD (vdd 0) vsource dc=vdd
I0 (vdd vb) isource dc=iref
M0 (vb vb 0 0) gpdk090_nmos2v w=wb l=l fw=wb
I1 (vdd nin) isource dc=iref
M3 (nin vb na 0) gpdk090_nmos2v w=w l=l fw=w
M1 (na nin 0 0) gpdk090_nmos2v w=w l=l fw=w
M4 (nout vb nb 0) gpdk090_nmos2v w=w l=l fw=w
M2 (nb nin 0 0) gpdk090_nmos2v w=w l=l fw=w
opts options save=allpub currents=all
'''

deckA = HDR + CORE + '''VOUT (nout 0) vsource dc=vx mag=1 type=sine ampl=100m freq=1k sinedc=vx
op dc oppoint=rawfile
info1 info what=oppoint where=file file="op.info"
swvout dc dev=VOUT param=dc start=0 stop=1.8 step=2m
swvdd dc dev=VDD param=dc start=0 stop=1.8 step=5m
acr ac start=1 stop=1M dec=20
tr tran stop=5m
'''

deckB = HDR + '''VDD (vdd 0) vsource dc=vdd
* ---- (a) simple mirror ----
IA (vdd nda) isource dc=iref
MA1 (nda nda 0 0) gpdk090_nmos2v w=w l=l fw=w
MA2 (nouta nda 0 0) gpdk090_nmos2v w=w l=l fw=w
VA (nouta 0) vsource dc=vx
* ---- (b) conventional cascode (stacked diodes input) ----
IB (vdd ndb2) isource dc=iref
MB4 (ndb2 ndb2 ndb1 0) gpdk090_nmos2v w=w l=l fw=w
MB3 (ndb1 ndb1 0 0) gpdk090_nmos2v w=w l=l fw=w
MB2 (noutb ndb2 nbb 0) gpdk090_nmos2v w=w l=l fw=w
MB1 (nbb ndb1 0 0) gpdk090_nmos2v w=w l=l fw=w
VB (noutb 0) vsource dc=vx
* ---- (c) high-swing cascode ----
IC0 (vdd vbc) isource dc=iref
MC0 (vbc vbc 0 0) gpdk090_nmos2v w=wb l=l fw=wb
IC1 (vdd ninc) isource dc=iref
MC3 (ninc vbc nac 0) gpdk090_nmos2v w=w l=l fw=w
MC1 (nac ninc 0 0) gpdk090_nmos2v w=w l=l fw=w
MC4 (noutc vbc nbc 0) gpdk090_nmos2v w=w l=l fw=w
MC2 (nbc ninc 0 0) gpdk090_nmos2v w=w l=l fw=w
VC (noutc 0) vsource dc=vx
opts options save=allpub currents=all
swcmp dc param=vx start=0 stop=1.8 step=2m
'''

if __name__ == "__main__":
    sel = sys.argv[1] if len(sys.argv) > 1 else "AB"
    if "A" in sel:
        r = spectre.run_netlist(deckA, run_name="hsc_main")
        print("A ok", r.ok, r.errors)
        pickle.dump(r, open("designs/hscasc/simA.pkl", "wb"))
        if not r.ok:
            i = r.log.find("ERROR"); print(r.log[max(0,i-200):i+800])
        else:
            inst = r.opinfo['instances']
            for n in ("M0","M1","M2","M3","M4"):
                d = inst[n]['params']; g = lambda k: d[k]['si']
                print(n, d['region']['raw'], "id=%.4g vgs=%.4g vds=%.4g vth=%.4g vdsat=%.4g gm=%.4g gds=%.4g"
                      % (g('id'), g('vgs'), g('vds'), g('vth'), g('vdsat'), g('gm'), g('gds')))
            a = r.analyses['swvout']
            vx = np.array(a['data']['dc']); io = np.array(a['data']['M4:d'])
            for v in (0.1,0.2,0.3,0.4,0.6,0.9,1.2,1.8):
                print("VOUT=%.2f IOUT=%.4f uA" % (v, np.interp(v, vx, io)*1e6))
            ac = r.analyses['acr']
            f = np.array(ac['data']['freq']); vout = np.array(ac['cdata']['nout']) if 'nout' in ac.get('cdata',{}) else None
            iv = ac['cdata'].get('VOUT:p')
            if iv is not None:
                ivา = np.ravel(np.array(iv))
                z = np.abs(1.0/ivา)
                fr = np.ravel(np.array(f))
                print("Rout @1k = %.4g MOhm" % (np.interp(1e3, fr, z)/1e6))
                print("Rout @1Hz = %.4g MOhm" % (z[0]/1e6))
    if "B" in sel:
        r = spectre.run_netlist(deckB, run_name="hsc_cmp")
        print("B ok", r.ok, r.errors)
        pickle.dump(r, open("designs/hscasc/simB.pkl", "wb"))
        if not r.ok:
            i = r.log.find("ERROR"); print(r.log[max(0,i-200):i+800])
        else:
            a = r.analyses['swcmp']; vx = np.array(a['data']['vx'])
            for sig, name in (("MA2:d","simple"),("MB2:d","conv casc"),("MC4:d","high-swing")):
                io = np.array(a['data'][sig])
                v95 = vx[np.argmax(io > 0.95*io[-1])] if io[-1]>0 else -1
                print(name, "I@1.8=%.4f uA, reaches 95%% at VOUT=%.3f" % (io[-1]*1e6, v95))
