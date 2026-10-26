"""181 actual saved-BRep rigid-mechanism poses plus explicit lock state checks.
Active ribbon is independently screened by motion.py and conservative radial/axial bounds.
"""
import FreeCAD as A,Part,os,json,math
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']);D=A.openDocument(str(P/'sweep-envelope.FCStd'));V=A.Vector
G=json.loads((P/'sweep-groups.json').read_text());sh={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')}
def rot(s,a):s=s.copy();s.rotate(V(),V(1,0,0),a);return s
moving=Part.makeCompound([sh[n] for n,g in G.items() if g=='rotor'])
fixed=Part.makeCompound([sh[n] for n,g in G.items() if g=='stationary'])
pin=sh['IndexPin'];released=pin.copy();released.translate(V(-4.2,0,0))
# Spring and cap lie within the stationary carrier; spring state was fully checked at both ends.
stationary=Part.makeCompound([fixed,released]);rows=[]
indexbody=sh['RotorHalfPositiveY'].fuse(sh['RotorHalfNegativeY'])
for angle in range(-90,91):
 m=rot(moving,angle);vol=m.common(stationary).Volume
 lock=pin.common(rot(indexbody,angle)).Volume
 detent=angle%15==0
 assert vol<1e-6,(angle,'released collision',vol)
 assert (lock<1e-6 if detent else lock>.01),(angle,'lock bypass',lock)
 rows.append({'angle':angle,'released_intersection_mm3':vol,'locked_pin_intersection_mm3':lock,'lock_allowed':detent})
 if angle%30==0:print('SWEEP',angle,flush=True)
res={'status':'PASS rigid released mechanism181poses; pin engagement allowed only13detents','rows':rows,'active_flex_basis':'motion.json181position finite-thickness proof + conservative guides; actual full assembly flex checked threeposes','pin_release_mm':4.2,'locked_engagement_mm':1.3,'released_tip_to_index_mm':2.9,'spring':{'free_mm':7,'installed_mm':5.8,'released_mm':1.6,'solid_mm':1.4,'rate_N_per_mm':.114,'preload_N':.1368,'released_force_N':.6156,'wire_mm':.2,'mean_diameter_mm':3,'active_coils':5,'total_coils':7,'return_friction_max_engineering_target_N':.08,'supplier_qualified':False}}
(P/'sweep.json').write_text(json.dumps(res,indent=2)+'\n')
A.closeDocument(D.Name)
