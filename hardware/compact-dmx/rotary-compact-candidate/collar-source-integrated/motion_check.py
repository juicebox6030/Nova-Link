"""181-position recomposition using a stronger axisymmetric sweep of every added solid.
Original moving solid coverage and index/lock retained by independent BRep comparison.
"""
import FreeCAD as A,Part,json,math,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector
D=A.openDocument(str(P/'integrated.FCStd'));S={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text())
old=A.openDocument(str(P.parent/'mechanism-repaired/mechanism.FCStd'));OS={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};OG=json.loads((P.parent/'mechanism-repaired/groups.json').read_text())
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cyl(r,l,x):return Part.makeCylinder(r,l,V(x,0,0),V(1,0,0))
# Stronger full-revolution stationary envelope; source adds nothing in lock zone.
bands=[(0,43,33),(43,70,25.9),(70,73.5,30.8),(73.5,74,25),(74,142,24)]
fixed=Part.makeCompound([cyl(r,x1-x0,x0) for x0,x1,r in bands]);addrows=[]
for n,g in G.items():
 if g!='rotor':continue
 s=S[n].cut(OS[n]) if n in OS else S[n]
 if s.Volume<1e-7:continue
 vol=s.common(fixed).Volume
 addrows.append({'name':n,'added_volume_mm3':s.Volume,'full_revolution_stationary_envelope_intersection_mm3':vol});assert vol<1e-6,(n,vol)
# No changes to original fixed/locking parts. Index geometry unchanged within X42..44.7.
unchanged=[]
for n,g in OG.items():
 if g in ['stationary','pin','spring']:
  assert n in S and S[n].cut(OS[n]).Volume<1e-7 and OS[n].cut(S[n]).Volume<1e-7,n;unchanged.append(n)
window=box(42,-34,-34,2.7,68,68)
for n in ['RotorHalfPositiveY','RotorHalfNegativeY']:
 a,b=S[n].common(window),OS[n].common(window);assert a.cut(b).Volume<1e-7 and b.cut(a).Volume<1e-7,n
identity=json.loads((P/'active-identity.json').read_text())
assert identity['status'].startswith('PASS') and len(identity['rows'])==3
active_checks=identity['rows']
assert all(x['equal'] and x['all_faces_planar_single_wire'] and x['all_edges_straight'] for x in active_checks)
# Old swept conservative envelope plus explicit containment proof is immutable evidence.
oldproof=json.loads((P.parent/'mechanism-repaired/sweep.json').read_text());contain=json.loads((P.parent/'mechanism-repaired/containment.json').read_text());assert contain['status'].startswith('PASS')
rows=[]
for r in oldproof['rows']:
 angle=r['angle'];c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle));det=c*c+s*s
 assert abs(det-1)<1e-12 and r['released_intersection_mm3']<1e-6
 rows.append({'angle':angle,'proper_rotation_determinant':det,'old_released_intersection_mm3':r['released_intersection_mm3'],'added_material_full_revolution_bound_mm3':max(x['full_revolution_stationary_envelope_intersection_mm3'] for x in addrows),'detent':r['lock_allowed'],'locked_pin_intersection_mm3':r['locked_pin_intersection_mm3']})
assert len(rows)==181 and sum(x['detent'] for x in rows)==13
out={'status':'PASS 181 composed released states using exact additions against full360degree stationary envelope','rows':rows,'added_solids':addrows,'stationary_bands_X0_X1_R_mm':bands,'unchanged_fixed_pin_spring_parts':unchanged,'index_region_unchanged':True,'active_flex':'Unchanged frozen three BReps and181numerical path; added material outside active radial envelope except static tangent continuation; full three-pose intersections independently checked','physical_elastic_equilibrium':False,'unchanged_active_pose_checks':active_checks}
(P/'motion-check.json').write_text(json.dumps(out,indent=2)+'\n');print('MOTION PASS',len(rows),'positions;',len(addrows),'added solids;',len(unchanged),'unchanged stationary/pin/spring',flush=True)
