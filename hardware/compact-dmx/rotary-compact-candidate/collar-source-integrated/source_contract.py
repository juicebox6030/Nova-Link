import FreeCAD as A,Part,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;D=A.openDocument(str(P/'integrated.FCStd'));S={o.Name:o.Shape.copy() for o in D.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text());old=A.openDocument(str(P.parent/'source-axial-routing/source-axial-envelopes.FCStd'))
rows=[]
for o in old.Objects:
 if not hasattr(o,'Shape'):continue
 s=S['SRC_'+o.Name].copy();s.translate(V(-75,-26.1,-10));s.rotate(V(),V(1,0,0),90)
 delta=s.cut(o.Shape).Volume+o.Shape.cut(s).Volume;assert delta<1e-7,(o.Name,delta)
 rows.append({'name':o.Name,'inverse_transform_symmetric_difference_mm3':delta,'solids':len(s.Solids)})
# Hardware edge supports occupy only the named copper-free edge strip of bottom reserve.
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
checks=[]
for rn in ['SRC_Top_assembly_clearance_proposal','SRC_Bottom_assembly_clearance_proposal']:
 reserve=S[rn]
 if 'Bottom' in rn:
  for z in [-10,9.8]:reserve=reserve.cut(box(75,24.74,z,27,.28,.2))
 for n,s in S.items():
  if G[n] in ['reserve','screen'] or G[n].startswith('pose') or n.startswith('SRC_'):continue
  vol=reserve.common(s).Volume if reserve.BoundBox.intersect(s.BoundBox) else 0
  checks.append({'reserve':rn,'part':n,'intersection_mm3':vol});assert vol<1e-6,(rn,n,vol)
# Finite engineering plug approach, at each of the three representative poses.
plug=S['USBPlugApproach'];plugchecks=[]
for a in [-90,0,90]:
 t=plug.copy();t.rotate(V(),V(1,0,0),a)
 for n,s0 in S.items():
  if G[n] in ['reserve','screen'] or G[n].startswith('pose'):continue
  s=s0.copy()
  if G[n]=='rotor':s.rotate(V(),V(1,0,0),a)
  vol=t.common(s).Volume if t.BoundBox.intersect(s.BoundBox) else 0
  plugchecks.append({'angle':a,'part':n,'intersection_mm3':vol});assert vol<1e-6,(a,n,vol)
# End retainer removed for insertion; edge rails have no axial undercuts along source slide.
# Reserve check uses actual source body/PCB/stake union at finite 1mm increments.
source_names=[n for n in S if n.startswith('SRC_') and G[n]=='rotor'];src=Part.makeCompound([S[n] for n in source_names]);insert=[]
for dx in range(0,33):
 t=src.copy();t.translate(V(dx,0,0))
 for n in ['RotorHalfPositiveY','RotorHalfNegativeY','StationaryCoreEnvelope','StationarySpool']:
  vol=t.common(S[n]).Volume if t.BoundBox.intersect(S[n].BoundBox) else 0
  insert.append({'translation_X_mm':dx,'part':n,'intersection_mm3':vol});assert vol<1e-6,(dx,n,vol)
# Conservative continuous translation sweep: each saved source BRep is contained
# in its bounding-box prism extended32mm along+X. Hole filling is conservative.
continuous=[]
for sn in source_names:
 bb=S[sn].BoundBox;t=box(bb.XMin,bb.YMin,bb.ZMin,bb.XLength+32,bb.YLength,bb.ZLength)
 for n in ['RotorHalfPositiveY','RotorHalfNegativeY','StationaryCoreEnvelope','StationarySpool']:
  vol=t.common(S[n]).Volume if t.BoundBox.intersect(S[n].BoundBox) else 0
  continuous.append({'source_part':sn,'obstacle':n,'intersection_mm3':vol});assert vol<1e-6,(sn,n,'continuous slide',vol)
# Actual finite component-top air-gap to ID32, no pad or conductive heat path assumed.
air=[]
for n in source_names:
 if 'maximum_body' in n:
  rmax=max(math.hypot(v.Point.y,v.Point.z) for v in S[n].Vertexes);air.append({'name':n,'body_vertex_Rmax_mm':rmax,'radial_gap_to_R32_mm':32-rmax})
assert min(x['radial_gap_to_R32_mm'] for x in air)>0
out={'status':'PASS source identity, top/bottom reserves, finite plug and board insertion screens','transform':{'rotation_axis':[1,0,0],'degrees':-90,'translation_mm':[75,26.1,10],'determinant':1},'source_shape_checks':rows,'assembly_reserve_checks':checks,'plug_checks':plugchecks,'insertion_checks':insert,'continuous_insertion_bounds':continuous,'component_airspace':air,'PCB_box_mm':[[75,102],[25.1,26.1],[-10,10]],'body_end_X_mm':104.17,'shell_end_X_mm':102,'locked_span_mm':73.17,'released_span_mm':77.37,'plug_screen_end_X_mm':116.17,'OD_mm':66,'source_board_functional_acceptance':False,'supplier_connector_profile_approved':False,'insertion_limit':'Rigid source board slide, not elastic fanout assembly simulation; source tail soldered through slot after board capture.'}
(P/'source-contract.json').write_text(json.dumps(out,indent=2)+'\n');print('SOURCE CONTRACT PASS',len(rows),'saved shapes;',len(checks),'reserve;',len(plugchecks),'plug;',len(insert),'insertion',flush=True)
