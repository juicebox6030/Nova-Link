from pathlib import Path
import FreeCAD as A,Part,json
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());kept=set(json.loads((P/'preserved-names.json').read_text()));new=[n for n in S if n not in kept and G[n] in ['newphysical','source','fastener','stationary_wire']]
def rot(s,a):q=s.copy();q.rotate(V(),V(1,0,0),a);return q
track=S['COL_StationarySpool'].common(Part.makeBox(1.4,70,70,V(49.6,-35,-35)));peg=Part.makeCylinder(1,1.3,V(49.7,-28.5,0),V(1,0,0));assert abs(S['RotorHalfNegativeY'].common(peg).Volume-peg.Volume)<1e-6
stops=[]
for a in range(-90,91):
 v=rot(peg,a).common(track).Volume;assert v<1e-7;stops.append({'angle':a,'volume':v})
beyond={str(a):rot(peg,a).common(track).Volume for a in [-90.5,90.5]};assert min(beyond.values())>1e-5
locks=[]
for a in range(-90,91,15):
 vols=[rot(S[n],a).common(S['COL_IndexPin']).Volume for n in ['RotorHalfPositiveY','RotorHalfNegativeY']];assert max(vols)<1e-7;locks.append({'angle':a,'volumes':vols})
released=[]
for n in [x for x in S if G[x]=='collar_pin']:
 q=S[n].copy();q.translate(V(-4.2,0,0))
 for other in new:
  v=q.common(S[other]).Volume if q.BoundBox.intersect(S[other].BoundBox) else 0;assert v<1e-7,(n,other,v);released.append({'pin_part':n,'new_part':other,'volume':v})
# Same compressed spring envelope used by frozen CIR release export.
spring=Part.makeCylinder(1.6,1.6,V(12.2,28.5,0),V(1,0,0)).cut(Part.makeCylinder(1.4,1.62,V(12.19,28.5,0),V(1,0,0)))
for other in new:
 v=spring.common(S[other]).Volume if spring.BoundBox.intersect(S[other].BoundBox) else 0;assert v<1e-7,('ReleasedSpring',other,v);released.append({'pin_part':'ReleasedSpringEnvelope','new_part':other,'volume':v})
# Exact BRep distance to the boundary of the tolerance-reduced free volume.
free=Part.makeCylinder(35.3,110,V(-137,0,0),V(1,0,0)).fuse(Part.makeCone(35.3,21.3,27,V(-27,0,0),V(1,0,0))).fuse(Part.makeCylinder(21.3,110,V(0,0,0),V(1,0,0)))
dist=[]
for n in ['L','N','PE']:
 q=S['Trunk'+n+'Corridor'];gap=q.distToShape(free.Shells[0])[0];assert gap>0;dist.append({'lane':n,'minimum_BRep_boundary_distance_mm':gap})
(P/'motion-clearance.json').write_text(json.dumps({'stop_positions':stops,'beyond_stop_collision_mm3':beyond,'lock_positions':locks,'released_pin_new_part_pairs':released,'released_pin_basis':'Stationary release parts independent of rotorangle; checked once and valid across181positions','corridor_boundary_distances':dist,'new_rotor_motion_basis':'cad-check.json axial/R24 exactcontainment certificates, validallangles; existing activeflex family unchanged'},indent=2)+'\n');print('MOTION181 LOCK13 RELEASE',len(released),'DIST',dist,flush=True)
