"""CAF-R2: lower the four passage starts to remove accidental tip/ledge contact."""
from pathlib import Path
import json,math,hashlib
import FreeCAD as A,Part
P=Path(__file__).resolve().parent;S=P.parent/'closure-access-fix';V=A.Vector
D=A.openDocument(str(S/'prototype.FCStd'));old=D.getObject('UpperShellRetention').Shape.copy();upper=old.copy()
unchanged={o.Name:(o.Shape.cleaned().exportBrepToString(),list(o.Placement.toMatrix().A)) for o in D.Objects if hasattr(o,'Shape') and o.Name!='UpperShellRetention'}
rows=[]
for name in sorted(o.Name for o in D.Objects if o.Name.startswith('ClosureTool_')):
    tool=D.getObject(name).Shape;b=tool.BoundBox;x=(b.XMin+b.XMax)/2;y=(b.YMin+b.YMax)/2
    rows.append({'tool':name,'xy':[x,y],'CAF_R1_overlap_mm3':tool.common(old).Volume,'CAF_R1_whole_tool_distance_mm':tool.distToShape(old)[0]})
    upper=upper.cut(Part.makeCylinder(2.75,37.5,V(x,y,4.0)))
assert upper.isValid() and upper.isClosed() and len(upper.Solids)==1
assert upper.cut(old).Volume<1e-7
below=Part.makeBox(100,100,4,V(-120,-50,0));assert old.common(below).cut(upper).Volume<1e-7
seats=[]
for x in(-110,-32):
    for y in(-32,32):
        disk=Part.makeCylinder(2,.01,V(x,y,2.99));a=old.common(disk).Volume/.01;b=upper.common(disk).Volume/.01
        assert abs(a-b)<1e-6 and abs(b-math.pi*(4-1.2**2))<1e-5
        seats.append({'xy':[x,y],'old_area_mm2':a,'new_area_mm2':b})
for r in rows:
    tool=D.getObject(r['tool']).Shape;r['CAF_R2_overlap_mm3']=tool.common(upper).Volume;r['CAF_R2_whole_tool_distance_mm']=tool.distToShape(upper)[0]
    assert r['CAF_R2_overlap_mm3']<1e-7 and r['CAF_R2_whole_tool_distance_mm']>.249999,r
D.getObject('UpperShellRetention').Shape=upper;D.recompute()
for name,(brep,placement) in unchanged.items():
    o=D.getObject(name);assert o.Shape.cleaned().exportBrepToString()==brep and list(o.Placement.toMatrix().A)==placement,name
D.saveAs(str(P/'prototype.FCStd'))
out={'revision':'CAF-R2','source_native_sha256':hashlib.sha256((S/'prototype.FCStd').read_bytes()).hexdigest(),'changed_part':'UpperShellRetention','other_shapes_unchanged_in_memory':len(unchanged),'passage_diameter_mm':5.5,'passage_z_mm':[4.0,41.5],'driver_z_mm':[4.5,40.5],'whole_tool_checks':rows,'bearing_seats':seats,'valid_connected_closed':True,'added_volume_mm3':upper.cut(old).Volume,'removed_volume_mm3':old.Volume-upper.Volume,'nominal_radial_gap_mm':.25,'nominal_tip_to_cut_start_mm':.5,'tolerance_allocations_not_supplier_qualified':{'radial':{'hole_radius_undersize':.1,'driver_radius_oversize':.05,'axis_error':.05,'remaining':.05},'axial':{'cut_start_error':.1,'head_seating_datum_error':.1,'remaining':.3}},'product_qualified':False}
(P/'patch.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
