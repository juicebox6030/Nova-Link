"""Independent proposal only; reads frozen GCT solids, never saves source document."""
import FreeCAD as A,Part,json,os
from pathlib import Path
P=Path(os.environ['NOVA_BUFFER_FIT']);V=A.Vector
src=P.parent/'service-footprints/gct-power-candidate/mechanical/flush-prototype.FCStd'
old=A.openDocument(str(src));shapes={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};A.closeDocument(old.Name)
d=A.newDocument('Buffer25FProposal');objects={}
def add(n,s,note):
 o=d.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis');o.Basis=note;objects[n]=o;return s
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cylinder(r=8.25,x=27,length=28.4):return Part.makeCylinder(r,length,V(x,30.65,18.1),V(1,0,0))
for n,s in shapes.items():
 if n not in ['Cap_envelope','PCB_tongue']:add(n,s,'Read-only frozen GCT mechanical input; inherited envelope/qualification caveats')
cut=box(26.5,25.5,9,29.4,10.3,3)
pcb=add('PCB_cutout_proposal',shapes['PCB_tongue'].cut(cut),'NEW internal aperture x26.5..55.9,y25.5..35.8; board z10..11; routing/strength gate')
cap=add('HV1625_max_body',cylinder(),'Eaton max diameter16.5,length28.4; placement x27..55.4 cy30.65 cz18.1; source envelope only')
cradles=[]
for i,x in enumerate([28,50]):
 s=box(x,25.8,7,3,9.7,5.5).cut(cylinder(8.60))
 cradles.append(add('Cradle'+str(i),s,'Design PA12 saddle, radius8.60 plus .35 compliant liner TBD; base contact z7; no retention/strength qualification'))
# Flexible liner and positive retainer require engineering, not fake closed supplier geometry.
checks=[]
for n,o in objects.items():
 if n=='HV1625_max_body':continue
 v=cap.common(o.Shape).Volume
 checks.append({'a':'cell','b':n,'volume_mm3':v,'distance_mm':cap.distToShape(o.Shape)[0]})
 assert v<1e-7,(n,v)
for i,s in enumerate(cradles):
 for n,o in objects.items():
  if n.startswith('Cradle'):continue
  v=s.common(o.Shape).Volume;assert v<1e-7,(i,n,v)
# Conservative isotropic .15 positional envelope, already using supplier max body.
worst=Part.makeCylinder(8.40,28.7,V(26.85,30.65,18.1),V(1,0,0))
# PCB process allocation .10 per edge and +.10 top; no components hidden by cutout.
worstpcb=box(4,23,10,90,28,1.1).cut(box(26.6,25.6,9,29.2,10.1,4))
worstchecks={}
for n,s in [('PCB_allocated',worstpcb),('lid',shapes['Lid']),('case',shapes['Base_with_bridge'])]:
 worstchecks[n]={'volume_mm3':worst.common(s).Volume,'distance_mm':worst.distToShape(s)[0]};assert worst.common(s).Volume<1e-7
parts=json.loads((P/'placement-boxes.json').read_text())['parts'];hits=[];partchecks=[]
for q in parts:
 x,y,x2,y2=q['bounds']
 if x2<=x or y2<=y:continue
 # All top courtyards conservatively 2.23 high; bottom1.45. This is a screening allocation, not source package CAD.
 z,h=(11,2.23) if q['side']=='top' else (8.55,1.45)
 if q['ref'] in ['U24','U26','R15']:h=1.45 # DBV supplier max; deliberately loose resistor allocation
 s=box(x,y,z,x2-x,y2-y,h)
 v=worst.common(s).Volume
 cv=sum(a.common(s).Volume for a in cradles)
 aperture_overlap=max(0,min(x2,55.9)-max(x,26.5))*max(0,min(y2,35.8)-max(y,25.5))
 row={'ref':q['ref'],'cell_volume_mm3':v,'cradle_volume_mm3':cv,'cutout_projected_overlap_mm2':aperture_overlap}
 partchecks.append(row)
 if v>1e-7 or cv>1e-7 or aperture_overlap>1e-7:hits.append(row)
assert not hits, hits
valid={n:o.Shape.isValid() and all(s.isClosed() for s in o.Shape.Solids) and len(o.Shape.Solids)>0 for n,o in objects.items()};assert all(valid.values())
d.recompute();d.saveAs(str(P/'buffer25-proposal.FCStd'));Part.export(list(objects.values()),str(P/'buffer25-proposal.step'))
(P/'geometry-check.json').write_text(json.dumps({'valid':valid,'cell_pairs':checks,'allocated':worstchecks,'component_screen':partchecks,'interferences':hits,'allocation':'Top courtyard extrusion2.23mm, U24/U26/R15=1.45mm, bottom1.45; source maxima not independently established for every part. Existing C23 explicitly removed/requires new formed leads.','cradle_liner_retention':'Unimplemented .35 radial compliant liner and nonmetal retention; process/strength/vent clearance gates'},indent=2)+'\n')
print('VALID',len(valid),'CELL_PAIRS',len(checks),'COMPONENTS',len(partchecks),'HITS',hits)
