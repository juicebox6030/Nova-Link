"""Actual axial saved-placement package allocations. LocalX axial, localY tangential, localZ board normal.
No parent collar transform or stationary/mains changes. Supplier body/stake profile acceptance still open.
"""
import FreeCAD as A,Part,json,csv,math
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;lands=json.loads((P/'land-sources.json').read_text());rows=list(csv.DictReader((P/'placement-ledger.csv').open()));holes=json.loads((P/'physical-geometry.json').read_text())['holes'];doc=A.newDocument('Axial_source_27x20');solids=[]
def add(name,shape):
 assert shape.isValid() and shape.Volume>0,name
 o=doc.addObject('PartDesign::Feature',name);o.Shape=shape;return o
def slot(x,y,w,h,z,height):
 if abs(w-h)<1e-6:return Part.makeCylinder(w/2,height,V(x,y,z))
 if w>h:
  r=h/2;s=Part.makeBox(w-h,h,height,V(x-(w-h)/2,y-h/2,z));return s.fuse(Part.makeCylinder(r,height,V(x-(w-h)/2,y,z))).fuse(Part.makeCylinder(r,height,V(x+(w-h)/2,y,z)))
 r=w/2;s=Part.makeBox(w,h-w,height,V(x-w/2,y-(h-w)/2,z));return s.fuse(Part.makeCylinder(r,height,V(x,y-(h-w)/2,z))).fuse(Part.makeCylinder(r,height,V(x,y+(h-w)/2,z)))
pcb=Part.makeBox(27,20,1,V(0,0,-1))
for h in holes:
 x,y=h['xy'];w,d=h['size_mm'];pcb=pcb.cut(slot(x,y,w,d,-1.1,1.2))
solids.append(add('PCB_27x20x1_actual_holes_nominal',pcb))
for row in rows:
 ref=row['ref'];info=lands[row['footprint']];w,h=info['body_max_mm'];z=info['height_max_mm'];x,y,angle=[float(row[k]) for k in ['x','y','degrees']]
 if z==0:continue
 s=Part.makeBox(w,h,z,V(-w/2,-h/2,0))
 if ref=='J1':s.translate(V(0,(-5.48+2.17)/2,0))
 # KiCadpositiveangle is clockwise in its screen XY; use negativeangle in CAD coordinates.
 s.rotate(V(0,0,0),V(0,0,1),-angle);s.translate(V(x,y,0));solids.append(add(ref+'_maximum_body_allocation',s))
pairs=0
for i,a in enumerate(solids):
 for c in solids[i+1:]:
  overlap=a.Shape.common(c.Shape).Volume;assert overlap<1e-8,(a.Name,c.Name,overlap);pairs+=1
stakes=[]
for h in holes:
 if h['ref']=='J1' and h['number'].startswith('S'):
  x,y=h['xy'];w,d=h['size_mm'];stakes.append(add('J1_'+h['number']+'_stake_swept_slot_allocation_not_vendor_profile',slot(x,y,w,d,-1.1,1.1)))
# Separate named assembly reserves, intentionally not counted as component bodies or approved collar fit.
reserve=[add('FPC_external_clamp_reserved_not_designed',Part.makeBox(20.55,4,2,V(.225,20,0))),add('FPC_solder_access_volume',Part.makeBox(20.55,2.6,3.16,V(.225,17.4,.3))),add('Top_assembly_clearance_proposal',Part.makeBox(27,20,.25,V(0,0,3.46))),add('Bottom_assembly_clearance_proposal',Part.makeBox(27,20,.25,V(0,0,-1.35)))]
doc.recompute();doc.saveAs(str(P/'source-axial-envelopes.FCStd'));Part.export(solids+stakes,str(P/'source-axial-envelopes.step'));Part.export(reserve,str(P/'assembly-reserves.step'))
r={'valid_body_solids':len(solids),'zero_volume_body_pair_checks':pairs,'actual_holes':len(holes),'stakes':4,'PCB_local_mm':{'X':[0,27],'Y':[0,20],'Z':[-1,0]},'parent_transform':'NOT selected; parent/Astra owns collar. LocalX axial+; localY tangential; localZ componentnormal. Centered tangentialT=Y-10.','port':{'PCB_edge_origin_mm':[27,10,0],'mate_vector':[1,0,0],'solder_row_X_mm':22.245,'conservative_body_X_max_mm':29.17,'body_Y_mm':[5.455,14.545],'body_height_max_mm':3.46,'front_body_alignment':'Conservative derivedbody envelope inherited fromprimaryland+bodydims; supplier matingface/profile alignment remainsgate, not an invented exactface coordinate.'},'PCB_thickness_proposal_mm':[.9,1.1],'stake_length_source_mm':[.8,1.1],'stake_below_min_thickness_max_mm':.2,'body_to_lowest_PCB_or_stake_max_mm':4.56,'assembly_normal_reserve_mm':[-1.35,3.71],'FPC_external_reserve_mm':{'X':[.225,20.775],'Y':[20,24],'Z':[0,2]},'supplier_stake_cross_section':'STEPuses PCBslot sweptallocation, not invented vendorstake profile. Retention/fillet/tolerance/process notqualified.','whole_collar_fit':False,'top_only_components':True,'fit_25x18_target':False,'manufacturing_release':False}
(P/'envelope-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
