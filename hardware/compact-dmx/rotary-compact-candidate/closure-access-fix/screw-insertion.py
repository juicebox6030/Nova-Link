from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.openDocument(str(P/'prototype.FCStd'));N={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P.parent/'cylindrical-source-repair/groups.json').read_text());exclude={'reserve','tool','corridor','unbuilt','access','collar_pose-90','collar_pose90','rotating_landing_reserve','stationary_landing_reserve'};physical=[n for n in N if G[n] not in exclude];rows=[];positive=[]
for name in sorted(n for n in N if n.startswith('ClosureScrew_')):
 b=N[name].BoundBox;x=(b.XMin+b.XMax)/2;y=(b.YMin+b.YMax)/2
 # Exact union envelope of coaxial cylinderhead andshaft translated0..60 in +Z.
 sweep=Part.makeCylinder(2,61.5,V(x,y,3)).fuse(Part.makeCylinder(1,67,V(x,y,-4)))
 for part in physical:
  if part==name:continue
  v=sweep.common(N[part]).Volume if sweep.BoundBox.intersect(N[part].BoundBox) else 0
  limit=math.pi*(1-.8**2)*4+1e-6 if part=='LowerShellPosts' else 1e-7
  assert v<=limit,(name,part,v);rows.append({'screw':name,'part':part,'volume_mm3':v,'limit_mm3':limit})
  if v>1e-7:positive.append(rows[-1])
(P/'screw-insertion.json').write_text(json.dumps({'pairs':len(rows),'positive':positive,'unintended':[],'upper_installed':True,'translation_envelope_mm':60,'thread_engagement':'Only original four M2/diameter1.6 pilot overlaps permitted; turning/threadstrength/process unqualified','head_to_passage_nominal_radial_clearance':.75,'shaft_to_existing_clearance_hole_radial_clearance':.2},indent=2)+'\n');print('SCREW INSERTION PASS',len(rows),len(positive),'THREADINTERFACES',flush=True)
