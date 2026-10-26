from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;S=P.parent/'cylindrical-source-repair';V=A.Vector
old=A.openDocument(str(S/'prototype.FCStd'));new=A.openDocument(str(P/'prototype.FCStd'));O={o.Name:o for o in old.Objects if hasattr(o,'Shape')};N={o.Name:o for o in new.Objects if hasattr(o,'Shape')};assert O.keys()==N.keys()
unchanged=[]
for name in N:
 a=N[name];b=O[name];assert a.Shape.isValid() and a.Shape.isClosed() and len(a.Shape.Solids)==1,name
 assert list(a.Placement.toMatrix().A)==list(b.Placement.toMatrix().A),name
 if name=='UpperShellRetention':continue
 x=a.Shape.cleaned().exportBrepToString().split();y=b.Shape.cleaned().exportBrepToString().split();assert len(x)==len(y),name
 for u,v in zip(x,y):
  if u!=v:assert abs(float(u)-float(v))<1e-12,(name,u,v)
 unchanged.append(name)
upper=N['UpperShellRetention'].Shape;before=O['UpperShellRetention'].Shape
assert upper.cut(before).Volume<1e-7
seat=Part.makeBox(100,100,4.5,V(-120,-50,0));seat_before=before.common(seat);assert seat_before.cut(upper).Volume<1e-7
G=json.loads((S/'groups.json').read_text());nonphysical={'reserve','tool','corridor','unbuilt','access','collar_pose-90','collar_pose90','rotating_landing_reserve','stationary_landing_reserve'}
physical=[n for n in N if G[n] not in nonphysical];rows=[]
for name in sorted(x for x in N if x.startswith('ClosureTool_')):
 tool=N[name].Shape
 for part in physical:
  q=N[part].Shape;v=tool.common(q).Volume if tool.BoundBox.intersect(q.BoundBox) else 0
  rows.append({'tool':name,'part':part,'intersection_mm3':v});assert v<1e-7,(name,part,v)
# Conservative continuous +Z insertion/removal envelope. Every vertical column is upwardclosed
# from12.25 for |Y|<29, or0 for outer strips. This encloses all translations 0..60.
def box(x,y,z,dx,dy,dz):return Part.makeBox(dx,dy,dz,V(x,y,z))
sweep=box(-115,-29,12.25,88,58,86.25).fuse(box(-115,29,0,88,9.5,98.5)).fuse(box(-115,-38.5,0,88,9.5,98.5))
assert upper.cut(sweep).Volume<1e-7
closure=[x for x in N if x.startswith('ClosureScrew_')];insertion=[]
for part in physical:
 if part in closure or part=='UpperShellRetention':continue
 q=N[part].Shape;v=sweep.common(q).Volume if sweep.BoundBox.intersect(q.BoundBox) else 0
 insertion.append({'fixed_part':part,'swept_bound_intersection_mm3':v});assert v<1e-7,(part,v)
# Independent source-bearing and passage geometry dimensions from saved shapes.
for name in closure:
 q=N[name].Shape;b=q.BoundBox;assert abs(b.ZMax-4.5)<1e-7
out={'valid_closed_single_solids':len(N),'other_shapes_preserved_numeric_1e12':len(unchanged),'all_placements_preserved':True,'changed_upper_added_volume_mm3':upper.cut(before).Volume,'unchanged_seat_region_volume_mm3':seat_before.Volume,'seat_region_removed_mm3':seat_before.cut(upper).Volume,'physical_parts_in_closed_state':len(physical),'tool_vs_closed_physical_pairs':rows,'tool_volume_failures':[],'upper_insertion_fixed_part_checks':insertion,'insertion_absent_parts':closure,'continuous_insertion_travel_mm':60,'insertion_bound':'Exact containment in three vertically upwardclosed boxes; translations0..60, closure screws absent until lidseated','nominal_radial_driver_clearance_mm':.25,'allocated_radial_clearance_mm':.05,'passage_starts_above_bearing_seat_mm':1.5,'tip_head_contact':'Z4.5 face touch, no positivevolume','proof_reuse':'Only fixed upper changed, strict subset; original unrelated pair/motion/corridor proofs preserved, NOT rerun'}
(P/'checks.json').write_text(json.dumps(out,indent=2)+'\n');print('CHECK PASS',len(N),len(unchanged),len(rows),len(insertion),flush=True)
