"""Simple editable package allocations, not vendor detailedSTEP or collar acceptance."""
import FreeCAD as A,Part,json,csv,math
from pathlib import Path
P=Path(__file__).resolve().parent;V=A.Vector;lands=json.loads((P/'land-sources.json').read_text());rows=list(csv.DictReader((P/'placement-ledger.csv').open()))
d=A.newDocument('Regulated_rotating_source');solids=[]
def obj(doc,name,shape,color):
 o=doc.addObject('PartDesign::Feature',name);o.Shape=shape
 if A.GuiUp:o.ViewObject.ShapeColor=color
 assert shape.isValid() and shape.Volume>0;return o
o=obj(d,'PCB_25x18x1_unrouted',Part.makeBox(25,18,1),(.15,.5,.2));solids.append(o)
for row in rows:
 ref=row['ref'];info=lands[row['footprint']];w,h=info['body_max_mm'];z=info['height_max_mm'];x,y,angle=map(float,[row['x'],row['y'],row['degrees']])
 if z==0:continue
 s=Part.makeBox(w,h,z,V(-w/2,-h/2,1))
 if ref=='J1':s.translate(V(0,(-5.48+2.17)/2,0))
 s.rotate(V(0,0,0),V(0,0,1),angle);s.translate(V(x,y,0));solids.append(obj(d,ref+'_maximum_body_allocation',s,(.5,.5,.55)))
pairs=[]
for i,a in enumerate(solids):
 for b in solids[i+1:]:
  vol=a.Shape.common(b.Shape).Volume;assert vol<1e-8,(a.Name,b.Name,vol);pairs.append([a.Name,b.Name,vol])
d.recompute();d.saveAs(str(P/'rotating-source-envelopes.FCStd'));Part.export(solids,str(P/'rotating-source-envelopes.step'))
# Separate stationary geometry, actual baseline core bore/carrier/mains keepout.
m=A.newDocument('IRM20_stationary_envelope');core=Part.makeCylinder(24,138,V(2,0,0),V(1,0,0)).cut(Part.makeCylinder(21.5,138,V(2,0,0),V(1,0,0)))
a=obj(m,'Baseline_core_OD48_ID43',core,(.5,.5,.5));mod=obj(m,'IRM20_max_body',Part.makeBox(52.9,27.7,24.5,V(45,-13.85,-10.75)),(.4,.4,.4))
board=obj(m,'Existing_stationary_carrier_allocation',Part.makeBox(61,32,1.6,V(39,-16,-13)),(.15,.5,.2))
trunk=obj(m,'Existing_stationary_mains_harness_keepout',Part.makeBox(130,16,5,V(6,-8,-19.5)),(.9,.4,.2))
assert a.Shape.common(mod.Shape).Volume<1e-8 and board.Shape.common(mod.Shape).Volume<1e-8
pins=[]
for no,x,y in [('AC_N',48.4,-10.4),('AC_L',48.4,10.4),('V_MINUS',93.4,-10.4),('V_PLUS',93.4,-2.4)]:pins.append(obj(m,'Module_'+no+'_maxlength_nominaldiameter',Part.makeCylinder(.5,4.5,V(x,y,-10.75),V(0,0,-1)),(.8,.8,.8)))
overlap=[{'pin':pin.Name,'mains_keepout_overlap_mm3':pin.Shape.common(trunk.Shape).Volume} for pin in pins]
assert sum(x['mains_keepout_overlap_mm3']>0 for x in overlap)==1
m.recompute();m.saveAs(str(P/'stationary-module-envelopes.FCStd'));Part.export([a,mod,board,trunk]+pins,str(P/'stationary-module-envelopes.step'))
result={'status':'Valid simpleenvelopes; no collar/mechanism/thermal/safetyrelease','rotating_valid_solids':len(solids),'zero_volume_pair_checks':len(pairs),'module_body_core_collision_volume_mm3':a.Shape.common(mod.Shape).Volume,'module_lead_mains_keepout_checks':overlap,'known_gate':'V_PLUS lead4.5max overlaps originalmainskeepout. Do not use as an approvedharness or silentlytrimlead.','USB_body_allocation':'Derived7.65mm long envelope aligned with12x1.15lands/4.18toPCBedge; confirm actualsupplierSTEP/matingprofile beforecollarcutout.','module_full_fit':False,'vendor_detailed_models':False}
(P/'envelope-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
