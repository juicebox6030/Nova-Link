from pathlib import Path
import numpy as np,json,math,hashlib
from scipy.special import betainc
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parent;motion=json.loads((P.parent/'constant-length-mechanism/motion.json').read_text());ms=np.array(json.loads((P/'moving-path.json').read_text())['samples']);pts=np.vstack([a+(b-a)*t for a,b in zip(ms[:-1],ms[1:]) for t in np.linspace(0,1,129,endpoint=False)]+[ms[-1]])
# CAD uses ruled straight segments between these sections; sampled segment-distance bound.
step=max(np.linalg.norm(np.diff(pts[:,:3],axis=0),axis=1));rows=[]
for row in motion['rows']:
 angle=row['angle'];k=row['k'];n=6+angle/360;t=np.linspace(0,1,8193);r=25+.3*n*t+(5.5-.3*n)*betainc(2+math.exp(k),2+math.exp(-k),t);ph=2*math.pi*n*t;xy=np.c_[r*np.cos(ph),r*np.sin(ph)];a=math.radians(angle);yy=pts[:,1]*math.cos(a)-pts[:,2]*math.sin(a);zz=pts[:,1]*math.sin(a)+pts[:,2]*math.cos(a);dist=cKDTree(xy).query(np.c_[yy,zz])[0];xgap=np.maximum(0,pts[:,0]-10-44.2);sep=np.hypot(dist,xgap)
 bound=.5*max(np.linalg.norm(np.diff(xy,axis=0),axis=1))+.5*step+.001
 gap=float(sep.min()-.16-bound);rows.append({'angle':angle,'lower_gap_mm':gap,'sampling_allowance_mm':bound})
assert len(rows)==181 and min(r['lower_gap_mm'] for r in rows)>0
(P/'active-fanout-check.json').write_text(json.dumps({'rows':rows,'min_moving_gap':min(r['lower_gap_mm'] for r in rows),'fixed_gap':json.loads((P/'fanout-probe.json').read_text())['minimum_active_gap'],'basis':'Nearest sampled centreline with half-segment allowances; 20mm extrusions, finite .16mm total ribbons; geometric path only','status':'PASS'},indent=2)+'\n');print('ACTIVE/FANOUT181 PASS',min(r['lower_gap_mm'] for r in rows))
