from pathlib import Path
import FreeCAD as A,Part,json,hashlib
P=Path(__file__).resolve().parent;S=P.parent/'cylindrical-source-repair';V=A.Vector
D=A.openDocument(str(S/'prototype.FCStd'));old=D.getObject('UpperShellRetention').Shape.copy();upper=old.copy();G=json.loads((S/'groups.json').read_text());rows=[]
for n in sorted(x for x in G if x.startswith('ClosureTool_')):
 tool=D.getObject(n).Shape;b=tool.BoundBox;x=(b.XMin+b.XMax)/2;y=(b.YMin+b.YMax)/2
 before=tool.common(old).Volume
 assert before>1,(n,before)
 cutter=Part.makeCylinder(2.75,37,V(x,y,4.5),V(0,0,1))
 upper=upper.cut(cutter)
 rows.append({'tool':n,'centre_xy':[x,y],'tool_diameter':5,'tool_z':[b.ZMin,b.ZMax],'passage_diameter':5.5,'passage_z':[4.5,41.5],'before_installed_upper_intersection_mm3':before})
assert upper.isValid() and upper.isClosed() and len(upper.Solids)==1
assert upper.cut(old).Volume<1e-7
# Seats and bosses below Z4.5 are exactly preserved, not merely inferred from picture.
seat=Part.makeBox(100,100,4.5,V(-120,-50,0));assert old.common(seat).cut(upper).Volume<1e-7
for row in rows:
 row['after_installed_upper_intersection_mm3']=D.getObject(row['tool']).Shape.common(upper).Volume;assert row['after_installed_upper_intersection_mm3']<1e-7
D.getObject('UpperShellRetention').Shape=upper
# Existing object properties and every other object are preserved by native save-copy.
D.recompute();D.saveAs(str(P/'prototype.FCStd'))
(P/'patch.json').write_text(json.dumps({'changed_part':'UpperShellRetention','source_native_sha256':hashlib.sha256((S/'prototype.FCStd').read_bytes()).hexdigest(),'source_receipt_sha256':hashlib.sha256((S/'receipt.json').read_bytes()).hexdigest(),'rows':rows,'removed_volume_mm3':old.Volume-upper.Volume,'added_volume_mm3':upper.cut(old).Volume,'unchanged_seat_below_z':4.5,'single_connected_closed_valid':True,'radial_nominal_clearance':.25,'proposed_tolerance_budget':{'passage_radius_undersize':.1,'driver_radius_oversize':.05,'axis_position_error':.05,'remaining_radial_clearance':.05},'ratings_or_supplier_tool_qualification':False},indent=2)+'\n');print('PATCH',rows,'REMOVED',old.Volume-upper.Volume,flush=True)
A.closeDocument(D.Name)
