from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'prototype.FCStd'));old=A.openDocument(str(P.parent/'cylindrical-source-repair/prototype.FCStd'));pts=[V(-32,24,-6),V(-32,43,-6),V(-32,43,44),V(-32,24,44)];plane=Part.Face(Part.makePolygon(pts+[pts[0]]));out={}
for name in ['UpperShellRetention','LowerShellPosts','ClosureScrew_m32_32','ClosureTool_m32_32']:
 out[name]=[[[v.y,v.z] for v in e.discretize(Deflection=.015)] for e in d.getObject(name).Shape.section(plane).Edges]
out['OriginalUpperGhost']=[[[v.y,v.z] for v in e.discretize(Deflection=.015)] for e in old.getObject('UpperShellRetention').Shape.section(plane).Edges]
seats=[]
for x in [-110,-32]:
 for y in [-32,32]:
  q=Part.makeCylinder(2,.01,V(x,y,2.99));a=old.getObject('UpperShellRetention').Shape.common(q).Volume/.01;b=d.getObject('UpperShellRetention').Shape.common(q).Volume/.01;assert abs(a-b)<1e-6 and abs(b-math.pi*(4-1.2**2))<1e-5;seats.append({'xy':[x,y],'old_bearing_area_mm2':a,'new_bearing_area_mm2':b})
(P/'section.json').write_text(json.dumps({'curves':out,'bearing_seats':seats,'centreline_inner_z':math.sqrt(35.5**2-32**2),'centreline_outer_z':math.sqrt(38.5**2-32**2)},indent=2)+'\n');print('SECTION/4SEATS PASS',flush=True)
