"""Independently reopen saved CAD and STEP; no generator import or live-doc acceptance."""
from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;d=A.openDocument(str(P/'source-axial-envelopes.FCStd'))
bodies=[o for o in d.Objects if o.Name=='PCB_27x20x1_actual_holes_nominal' or o.Name.endswith('_maximum_body_allocation')];assert len(bodies)==34
assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in bodies)
pairs=0
for i,o in enumerate(bodies):
 for q in bodies[i+1:]:assert o.Shape.common(q.Shape).Volume<1e-8,(o.Name,q.Name);pairs+=1
b=d.getObject('PCB_27x20x1_actual_holes_nominal').Shape.BoundBox
assert (b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax)==(0,0,-1,27,20,0)
j=d.getObject('J1_maximum_body_allocation').Shape.BoundBox
assert all(abs(a-c)<1e-7 for a,c in zip([j.XMin,j.XMax,j.YMin,j.YMax,j.ZMin,j.ZMax],[21.52,29.17,5.455,14.545,0,3.46]))
r=d.getObject('R13_maximum_body_allocation').Shape.BoundBox
assert abs((r.XMin+r.XMax)/2-4.75)<1e-7 and abs((r.YMin+r.YMax)/2-14.8)<1e-7 and abs(r.ZMax-.4)<1e-7
stakes=[o for o in d.Objects if '_stake_swept_slot_allocation' in o.Name];assert len(stakes)==4
assert all(o.Shape.isValid() and abs(o.Shape.BoundBox.ZMin+1.1)<1e-8 and abs(o.Shape.BoundBox.ZMax)<1e-8 for o in stakes)
step=Part.read(str(P/'source-axial-envelopes.step'));assert step.isValid() and len(step.Solids)==38
assert abs(sum(o.Shape.Volume for o in bodies+stakes)-sum(s.Volume for s in step.Solids))<1e-5
reserve=Part.read(str(P/'assembly-reserves.step'));assert reserve.isValid() and len(reserve.Solids)==4
r=d.getObject('FPC_external_clamp_reserved_not_designed').Shape.BoundBox
assert all(abs(a-c)<1e-7 for a,c in zip([r.XMin,r.XMax,r.YMin,r.YMax,r.ZMin,r.ZMax],[.225,20.775,20,24,0,2]))
r={'status':'PASS reopened actual savedFCStd and bothSTEP exports; package allocations only','saved_body_and_PCB_solids':len(bodies),'saved_zero_overlap_body_pairs':pairs,'STEP_solids_including_stake_allocations':len(step.Solids),'STEP_volume_agreement':True,'assembly_reserve_solids':4,'R13_actual_body_present':True,'port_and_FPC_allocation_coordinates_match':True,'full_fit_or_supplier_profile_accepted':False}
(P/'saved-CAD-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
