"""Canonical planar-boundary identity, independent of BRep serialization ordering/tolerances.
All active-flex boundaries must be planar polygons with straight edges. No surface sampling.
"""
import FreeCAD as A,json,math,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'integrated.FCStd'));old=A.openDocument(str(P.parent/'mechanism-repaired/mechanism.FCStd'));rows=[]
def canonical(shape):
 faces=[]
 for f in shape.Faces:
  assert type(f.Surface).__name__=='Plane',type(f.Surface).__name__
  assert len(f.Wires)==1
  assert all(type(e.Curve).__name__ in ['Line','LineSegment'] for e in f.Edges)
  # Ordered wire preserves every polygon edge; canonical start and direction only.
  pts=[tuple(round(q,9) for q in (v.Point.x,v.Point.y,v.Point.z)) for v in f.Wires[0].OrderedVertexes]
  seqs=[]
  for a in [pts,list(reversed(pts))]:
   i=min(range(len(a)),key=lambda j:a[j]);seqs.append(tuple(a[i:]+a[:i]))
  faces.append(min(seqs))
 return sorted(faces)
for n in ['Flex_minus90','Flex_0','Flex_90']:
 a=d.getObject(n).Shape;b=old.getObject(n).Shape;ca,cb=canonical(a),canonical(b)
 assert ca==cb,n
 assert abs(a.Volume-b.Volume)<1e-7 and abs(a.Area-b.Area)<1e-7
 ha=hashlib.sha256(json.dumps(ca,separators=(',',':')).encode()).hexdigest()
 rows.append({'name':n,'plane_polygon_faces':len(ca),'all_edges_straight':True,'all_faces_planar_single_wire':True,'canonical_boundary_sha256':ha,'coordinate_rounding_mm':1e-9,'volume_difference_mm3':abs(a.Volume-b.Volume),'area_difference_mm2':abs(a.Area-b.Area),'equal':True});print(n,'PASS',len(ca),'complete polygon boundaries',flush=True)
(P/'active-identity.json').write_text(json.dumps({'status':'PASS canonical full planar-boundary identity at1e-9mm coordinate rounding','rows':rows,'note':'Raw BRep byte strings are not canonical after save/reopen. This proof compares complete straight-edge polygon topology, not sampled points or volume alone.'},indent=2)+'\n')
A.closeDocument(d.Name);A.closeDocument(old.Name)
