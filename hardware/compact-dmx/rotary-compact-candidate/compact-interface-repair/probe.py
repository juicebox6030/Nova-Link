"""Bounded static fanout geometry, preserving the frozen active path family."""
from pathlib import Path
import numpy as np,math,json,hashlib
from scipy.special import betainc
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parent;S=P.parent/'constant-length-mechanism';src=S/'motion.json';motion=json.loads(src.read_text());B=.3/(2*math.pi);a=-.3;r=25+B*a
start=np.array([r*math.cos(a),r*math.sin(a)]);der=np.array([-B*math.cos(a)+r*math.sin(a),-B*math.sin(a)-r*math.cos(a)]);der/=np.linalg.norm(der)
ctrl=np.array([start,start+8*der,[14.68,-17],[14.68,-10]])
t=np.linspace(0,1,4097);u=1-t
p=u[:,None]**3*ctrl[0]+3*(u*u*t)[:,None]*ctrl[1]+3*(u*t*t)[:,None]*ctrl[2]+t[:,None]**3*ctrl[3]
d=3*(u*u)[:,None]*(ctrl[1]-ctrl[0])+6*(u*t)[:,None]*(ctrl[2]-ctrl[1])+3*(t*t)[:,None]*(ctrl[3]-ctrl[2]);dd=6*u[:,None]*(ctrl[2]-2*ctrl[1]+ctrl[0])+6*t[:,None]*(ctrl[3]-2*ctrl[2]+ctrl[1]);speed=np.linalg.norm(d,axis=1);curv=np.abs(d[:,0]*dd[:,1]-d[:,1]*dd[:,0])/speed**3
normal=np.c_[-d[:,1],d[:,0]]/speed[:,None];path=np.vstack([p,np.c_[np.full(101,14.68),np.linspace(-10,-4.8,101)[1:]]]) if False else np.vstack([p,np.c_[np.full(100,14.68),np.linspace(-10,-4.8,101)[1:]]]);norm=np.vstack([normal,np.tile([-1.,0],(100,1))])
length=float(np.sum(np.linalg.norm(np.diff(path,axis=0),axis=1)));rows=[]
for row in motion['rows']:
 angle=row['angle'];n=6+angle/360;k=row['k'];tt=np.linspace(0,1,8193);rad=25+.3*n*tt+(5.5-.3*n)*betainc(2+math.exp(k),2+math.exp(-k),tt);ph=2*math.pi*n*tt;xy=np.c_[rad*np.cos(ph),rad*np.sin(ph)];dist,ix=cKDTree(xy).query(path);gap=float(dist.min()-.16-.003)
 rows.append({'angle':angle,'sampled_surface_gap_with_0p003_chord_allowance':gap})
# Two copper8mm traces,70um, plus25um oneface/65umother dielectric; BOTHends access.
# This stack is engineering-proposed. Minco p10 lists1-layer2-sidedaccess; no supplier approval.
R20=2*.017241*(length/1000)/.56;R85=R20*(1+.00393*65)
out={'source_motion_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'control_points_YZ':ctrl.tolist(),'length':length,'min_bend_radius':float(1/curv.max()),'max_radius':float(np.linalg.norm(path,axis=1).max()),'stationary_origin':[22.2,14.5,8],'proper_transform':['22.2+x','14.5+z','8-y'],'pad_J2_contacts':{'1':'FPC positive laneX25.7..33.7','2':'FPC return laneX34.7..42.7'},'end_normal':norm[-1].tolist(),'copper_offsets':[-.055,.015],'stationary_contact_face':'back-access atoffset+.015; Y14.665 to solderpreformtop14.665; padtop14.535, solder0.13','copper_R20_loop':R20,'copper_R85_loop':R85,'drop_2A_85C':2*R85,'heat_2A_85C':4*R85,'motion_rows':rows,'minimum_active_gap':min(x['sampled_surface_gap_with_0p003_chord_allowance'] for x in rows),'samples':np.c_[path,norm].tolist(),'status':'numeric stationaryfanout candidate; no assemblyPASS'}
(P/'fanout-probe.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['samples','motion_rows']})
