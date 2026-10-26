from pathlib import Path
import FreeCAD as A,Part,json
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'interface-prototype.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text())
views={};outlines={}
for label,axis,value in [('XY',2,0),('fixed',0,34.2),('source',0,63.2)]:
 pts=[V(-180,-60,0),V(210,-60,0),V(210,70,0),V(-180,70,0)] if axis==2 else [V(value,-60,-60),V(value,60,-60),V(value,60,60),V(value,-60,60)]
 plane=Part.Face(Part.makePolygon(pts+[pts[0]]));lines=[]
 for n,s in S.items():
  if n.startswith('COL_Flex_') or G[n].endswith('_pad') or G[n] in ['insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen'] or G[n].endswith('landing_reserve'):continue
  b=s.BoundBox
  if not(getattr(b,['XMin','YMin','ZMin'][axis])-1e-7<=value<=getattr(b,['XMax','YMax','ZMax'][axis])+1e-7):continue
  q=s.section(plane)
  for e in q.Edges:
   pp=e.discretize(Deflection=.08);lines.append({'part':n,'points':[[p.x,p.y] if axis==2 else [p.y,p.z] for p in pp]})
 views[label]=lines;print('SECTION',label,len(lines),flush=True)
(P/'sections.json').write_text(json.dumps(views,separators=(',',':'))+'\n')
physical=[s.BoundBox for n,s in S.items() if G[n] not in ['insulation','tolerance','trunk_tolerance','support','access','primary_bay','pin_reserve','collar_reserve','collar_pose-90','collar_pose90','screen'] and not n.startswith('COL_Flex_')]
bounds={k:[min(getattr(b,k+'Min') for b in physical),max(getattr(b,k+'Max') for b in physical)] for k in ['X','Y','Z']};(P/'envelope.json').write_text(json.dumps({'comparison_bounds_mm':bounds,'comparison_LWH_mm':[bounds[k][1]-bounds[k][0] for k in ['X','Y','Z']],'note':'Includes provisional24mm end blanks; NOT total product/variant acceptance; supplier spline bbox can be conservative'},indent=2)+'\n')
