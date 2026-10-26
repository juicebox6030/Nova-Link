from pathlib import Path
import FreeCAD as A,Part,json
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'prototype.FCStd'));G=json.loads((P/'groups.json').read_text());V=A.Vector
names=[o.Name for o in d.Objects if hasattr(o,'Shape') and G[o.Name] in ['newphysical','source','fastener']]
def face(pts):return Part.Face(Part.makePolygon([V(*p) for p in pts+[pts[0]]]))
planes={'mid_source':(face([(-71,-50,-50),(-71,50,-50),(-71,50,50),(-71,-50,50)]),lambda v:[v.y,v.z]),'post_source':(face([(-99.5,-50,-50),(-99.5,50,-50),(-99.5,50,50),(-99.5,-50,50)]),lambda v:[v.y,v.z]),'longitudinal':(face([(-135,0,-50),(110,0,-50),(110,0,50),(-135,0,50)]),lambda v:[v.x,v.z])}
for xx in [34.2,65]:planes['collar'+str(xx)]=(face([(xx,-50,-50),(xx,50,-50),(xx,50,50),(xx,-50,50)]),lambda v:[v.y,v.z])
out={}
for key,(plane,xy) in planes.items():
 lines=[]
 section_names=names if not key.startswith('collar') else [o.Name for o in d.Objects if hasattr(o,'Shape') and G[o.Name] not in ['reserve','tool','corridor','unbuilt','access','collar_pose-90','collar_pose90','rotating_landing_reserve','stationary_landing_reserve']]
 for n in section_names:
  sec=d.getObject(n).Shape.section(plane)
  for e in sec.Edges:
   pts=e.discretize(Deflection=.08);lines.append({'part':n,'points':[xy(p) for p in pts]})
 out[key]=lines
(P/'sections.json').write_text(json.dumps(out)+'\n');print('SECTIONS', {k:len(v) for k,v in out.items()},flush=True)
