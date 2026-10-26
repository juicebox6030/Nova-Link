"""Finite-thickness kinematic screen; no elastic-equilibrium claim."""
from pathlib import Path
import json, math, hashlib
import numpy as np
from scipy.special import betainc, betaln
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parent
L=1046.167655992167
B=.30/(2*math.pi)
def curve(n,k,t):
 a,b=2+math.exp(k),2+math.exp(-k);t=np.asarray(t);u=np.clip(t,1e-12,1-1e-12)
 pdf=np.exp((a-1)*np.log(u)+(b-1)*np.log1p(-u)-betaln(a,b));rem=5.5-.30*n
 r=25+.30*n*t+rem*betainc(a,b,t);d=.30*n+rem*pdf
 dd=rem*pdf*((a-1)/u-(b-1)/(1-u))
 return r,d,dd
def length(n,k):
 return quad(lambda t: math.hypot(float(curve(n,k,t)[1]),float(curve(n,k,t)[0])*2*math.pi*n),0,1,epsabs=1e-8,epsrel=1e-11,limit=150)[0]
rows=[];poses={}
for angle in range(-90,91):
 n=6+angle/360;k=brentq(lambda k:length(n,k)-L,-4,4,xtol=1e-12)
 t=np.linspace(0,1,8193);r,d,dd=curve(n,k,t);ph=2*math.pi*n*t;rp=d/(2*math.pi*n);rpp=dd/(2*math.pi*n)**2
 bend=float(np.min((r*r+rp*rp)**1.5/np.abs(r*r+2*rp*rp-r*rpp)))
 xy=np.c_[r*np.cos(ph),r*np.sin(ph)];ds,ix=cKDTree(xy).query(xy,k=24)
 h=float(np.max(np.linalg.norm(np.diff(xy,axis=0),axis=1)));gap=float(np.min(ds[np.abs(ix-np.arange(len(t))[:,None])>100]))-h*h/(4*bend)-.16
 # Exact normal offset rather than merely radial +/- .08.
 derivative=np.c_[rp*np.cos(ph)-r*np.sin(ph),rp*np.sin(ph)+r*np.cos(ph)]
 normal=np.c_[derivative[:,1],-derivative[:,0]]/np.linalg.norm(derivative,axis=1)[:,None]
 sides=[xy+.08*normal,xy-.08*normal]
 rr=np.concatenate([np.linalg.norm(p,axis=1) for p in sides]);inner=float(rr.min()-24.6);outer=float(31.0-rr.max())
 assert gap>.1 and inner>.31 and outer>.41 and abs(length(n,k)-L)<1e-7
 rows.append(dict(angle=angle,k=k,length=length(n,k),bend_radius=bend,turn_gap=gap,guide_inner_gap=inner,guide_outer_gap=outer,cheek_axial_gap=.5))
 if angle in [-90,0,90]:
  # 2049 stations; explicit polygon chord bound, not supplier smooth tooling surface.
  ids=np.arange(0,8193,4)
  poses[str(angle)]={'outer':sides[0][ids].tolist(),'inner':sides[1][ids].tolist(),'k':k,'cad_chord_bound_mm':(h*4)**2/(8*bend)}
# engineering thermal copper screen; allocated conductivity, not certified stack
R20=2*.017241*(L/1000)/(.008*70e-6*1e6) # ohm mm²/m, section .56 mm²
R85=R20*(1+.00393*65)
result={'status':'PASS active-path geometry ONLY; assembly check is separate','rows':rows,'minimum_turn_gap_mm':min(r['turn_gap'] for r in rows),'minimum_bend_R_mm':min(r['bend_radius'] for r in rows),'max_length_error_mm':max(abs(r['length']-L) for r in rows),'inner_endpoint_tangent_deg':math.degrees(math.atan(B/25)),'outer_endpoint_tangent_deg':math.degrees(math.atan(B/30.5)),'active_length_mm':L,'allocated_stack_mm':.16,'width_mm':20,'copper_um':70,'two_trace_width_mm':8,'active_loop_R20_ohm':R20,'active_loop_R85_ohm':R85,'active_drop_1p5A_85C_V':1.5*R85,'active_heat_1p5A_85C_W':2.25*R85,'limits':['181 angular samples; not continuum proof','Shape family not elastic equilibrium; clamp force, friction, hysteresis and cycle life unknown','Active length excludes static fanout and termination resistance; regulator budget owned separately']}
(P/'motion.json').write_text(json.dumps(result,indent=2)+'\n');(P/'poses.json').write_text(json.dumps(poses)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
