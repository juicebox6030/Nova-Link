"""Read saved native geometry, export edges for auditable dimensioned projections."""
from pathlib import Path
import FreeCAD as A,Part,json,traceback
P=Path(__file__).resolve().parent
try:
 d=A.openDocument(str(P/'stationary-integration.FCStd'));out={}
 for o in d.Objects:
  es=[]
  for e in o.Shape.Edges:
   ps=e.discretize(Deflection=.12)
   es.append([[p.x,p.y,p.z] for p in ps])
  b=o.Shape.BoundBox
  out[o.Name]={'edges':es,'bbox':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],'solids':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume}
 s=Part.read(str(P/'stationary-integration.step'))
 rows=[];remaining=list(s.Solids)
 for o in d.Objects:
  b=o.Shape.BoundBox
  bb=lambda q:[q.BoundBox.XMin,q.BoundBox.YMin,q.BoundBox.ZMin,q.BoundBox.XMax,q.BoundBox.YMax,q.BoundBox.ZMax]
  vals=bb(o.Shape);q=min(remaining,key=lambda q:sum(abs(x-y) for x,y in zip(vals,bb(q))));remaining.remove(q)
  surface=Part.makeCompound(q.Faces);gap=0
  for edge in o.Shape.Edges:
   for pt in edge.discretize(Number=7):gap=max(gap,Part.Vertex(pt).distToShape(surface)[0])
  nsurface=Part.makeCompound(o.Shape.Faces)
  for edge in q.Edges:
   for pt in edge.discretize(Number=7):gap=max(gap,Part.Vertex(pt).distToShape(nsurface)[0])
  rows.append({'bidirectional_edge_sample_max_surface_gap_mm':gap,'part':o.Name,'native_volume_mm3':o.Shape.Volume,'STEP_volume_mm3':q.Volume,'difference_mm3':q.Volume-o.Shape.Volume,'bbox_max_error_mm':max(abs(x-y) for x,y in zip(vals,bb(q)))})
 (P/'step-parts.json').write_text(json.dumps(rows,indent=2)+'\n')
 nativevol=sum(o.Shape.Volume for o in d.Objects);stepvol=sum(q.Volume for q in s.Solids)
 (P/'step-transfer.json').write_text(json.dumps({'valid':s.isValid(),'native_volume_mm3':nativevol,'STEP_volume_mm3':stepvol,'difference_mm3':stepvol-nativevol,'solid_count':len(s.Solids)},indent=2)+'\n')
 (P/'saved-projections.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('PROJECTED',len(out),'saved objects')
except BaseException:
 traceback.print_exc();raise
