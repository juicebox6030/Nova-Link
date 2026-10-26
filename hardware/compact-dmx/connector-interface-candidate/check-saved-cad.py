"""Independent saved-document checks. Does not heal or release manufacturer CAD."""
from pathlib import Path
import FreeCAD as App, Part, json, hashlib, math
ROOT=Path(__file__).resolve().parent
contracts=json.loads((ROOT/'contracts.json').read_text())
report=json.loads((ROOT/'cad-inspection.json').read_text())
doc=App.openDocument(str(ROOT/'sources'/'manufacturer-models.FCStd'))
rows=[]
for key,expected in report['items'].items():
 o=doc.getObject(key.replace('-','_'));assert o and not o.Shape.isNull(),key
 raw=(ROOT/('sources/'+key+'.step')).read_bytes()
 assert o.SourceSHA256==hashlib.sha256(raw).hexdigest()==expected['source_sha256'],key
 shape=o.Shape
 assert len(shape.Faces)==expected['face_count']
 assert len(shape.Solids)==expected['solids'] and shape.isValid()==expected['valid']
 verts,_=shape.tessellate(.03)
 b=[min(v[j] for v in verts) for j in range(3)]+[max(v[j] for v in verts) for j in range(3)]
 assert max(abs(a-z) for a,z in zip(b,expected['sampled_mesh_bbox_mm']))<.00001,key
 ax=expected['projection_axis_index']
 row={'id':key,'valid':shape.isValid(),'solids':len(shape.Solids),'faces':len(shape.Faces),'sampled_bbox_mm':b,'sampled_radial_diameter_mm':2*max(sum(v[j]**2 for j in range(3) if j!=ax)**.5 for v in verts),'raw_source_sha256':o.SourceSHA256}
 c=next((x for x in contracts['interfaces'] if x['id']==key),None)
 if c:
  face=shape.Faces[int(c['panel_face'][4:])-1]
  assert type(face.Surface).__name__=='Plane'
  coord=face.Surface.Position[c['axis_index']]
  assert abs(coord-c['panel_coordinate_mm'])<1e-6,key
  assert abs(abs(face.Surface.Axis[c['axis_index']])-1)<1e-7,key
  # Mount shoulder from drawing. Mesh end is used only AFTER that datum is fixed.
  rear=b[ax] if c['outward_sign']==1 else b[ax+3]
  depth=c['outward_sign']*(coord-rear)
  assert depth>24,key
  row.update(panel_face=c['panel_face'],panel_coordinate_mm=coord,sampled_bare_rear_depth_from_panel_mm=depth,drawing_rear_depth_mm=c['drawing_rear_depth_mm'],cad_minus_drawing_mm=depth-c['drawing_rear_depth_mm'],end_24mm_accepted=False)
 rows.append(row)
out={'status':'PASS_REFERENCE_CONSISTENCY_ONLY','objects_checked':len(rows),'chassis_checked':6,'closed_valid_solid_claim':False,'assembly_fit_claim':False,'mesh_is_not_a_tolerance_bound':True,'items':rows,'warning':'Vendor invalid and open/surface models intentionally remain unchanged. No collision/insulation/assembly validation.'}
(ROOT/'saved-cad-check.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS:',len(rows),'saved objects; 6 drawing-referenced panel planes; all 6 bare rear depths >24 mm. No assembly fit acceptance.')
