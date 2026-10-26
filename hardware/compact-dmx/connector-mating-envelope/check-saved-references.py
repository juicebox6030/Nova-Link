"""Independent read-only comparison of saved UNPLACED references to frozen originals.
Plane coincidence probes are diagnostics, never assembled poses or collision acceptance.
"""
from pathlib import Path
import json,hashlib,math
import FreeCAD as App
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'connector-interface-candidate'
src=App.openDocument(str(OLD/'sources/manufacturer-models.FCStd'))
saved=App.openDocument(str(ROOT/'sources/unplaced-references.FCStd'))
contracts=json.loads((ROOT/'contracts.json').read_text())
inspection=json.loads((ROOT/'datum-inspection.json').read_text())
results=[]
def bounds(s):
 b=s.BoundBox;return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def eq(a,b,tol=1e-7):
 assert len(a)==len(b) and max(abs(x-y) for x,y in zip(a,b))<tol,(a,b)
for key,d in inspection['items'].items():
 a=src.getObject(key.replace('-','_'));b=saved.getObject(key.replace('-','_'))
 raw=(OLD/'sources'/(key+'.step')).read_bytes();sha=hashlib.sha256(raw).hexdigest()
 assert sha==a.SourceSHA256==b.OriginalSHA256==d['source_sha256']
 txt=raw.decode('latin1');assert "SI_UNIT(.MILLI.,.METRE.)" in txt.replace(' ','').replace('\n','')
 assert b.Placement.isIdentity() and a.Placement.isIdentity()
 sa,sb=a.Shape,b.Shape
 assert len(sa.Faces)==len(sb.Faces) and len(sa.Edges)==len(sb.Edges) and len(sa.Solids)==len(sb.Solids)
 eq(bounds(sa),bounds(sb));eq([sa.Area,sa.Volume],[sb.Area,sb.Volume],1e-5)
 assert sa.isValid()==sb.isValid()==d['valid']
 for face in d['selected_planes']:
  n=int(face['id'][4:]);fa=sa.Faces[n-1];fb=sb.Faces[n-1]
  assert type(fa.Surface).__name__==type(fb.Surface).__name__==face['surface']
  eq(list(fb.Surface.Position),face['surface_position_mm']);eq(list(fb.Surface.Axis),face['surface_axis'])
  eq(bounds(fa),bounds(fb));eq([fb.Area],[face['area_mm2']])
 results.append({'model':key,'source_sha256':sha,'millimetre_STEP_unit':True,'saved_placement_identity':True,'same_topology_and_geometry_invariants':True,'valid_whole_shape':sb.isValid(),'closed_solids':len(sb.Solids),'faces':len(sb.Faces),'face_planes_checked':len(d['selected_planes'])})
# Reproduce specified axial plane probes from saved geometry, including other pairs.
probes=[]
for c in contracts['pairs']:
 ax=c['expected_chassis_mating_axis']['source_axis_index'];a=saved.getObject(c['chassis_model_key'].replace('-','_')).Shape
 b=saved.getObject(c['mate_model_key'].replace('-','_')).Shape
 for p in c['surface_probes']:
  f=a.Faces[int(p['chassis_face'][4:])-1].copy();g=b.Faces[int(p['mate_face'][4:])-1].copy()
  if c['pair']=='true1-out':g.rotate(App.Vector(),App.Vector(0,1,0),90)
  # Axis-only alignment of an isolated plane: no spin choice or full pair placement.
  delta=f.Surface.Position[ax]-g.Surface.Position[ax];v=[0,0,0];v[ax]=delta;g.translate(App.Vector(*v))
  fa=f.Surface.Axis;ga=g.Surface.Axis;cross=fa.cross(ga).Length
  common=f.common(g)
  probes.append({'pair':c['pair'],'chassis_face':p['chassis_face'],'mate_face':p['mate_face'],'valid_isolated_faces':[f.isValid(),g.isValid()],'axis_only_analytical_plane_translation_mm':delta,'normal_parallel_cross_residual':cross,'face_common_area_mm2':common.Area,'whole_model_boolean_performed':False,'accepted_pose':False})
assert len(saved.Objects)==8
out={'revision':'CME-R1','models_checked':results,'isolated_face_probes':probes,'accepted_installed_poses':0,'full_assembly_or_continuous_motion_verified':False,'warning':'Identity placements retain unrelated raw supplier coordinate systems. No mated assembly is represented. Invalid whole-shapes and open surface models remain reference-only.'}
(ROOT/'saved-reference-check.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS: eight saved unplaced references preserve units, source hashes, topology and geometry; eight isolated plane probes recorded. Zero installed poses accepted.')
