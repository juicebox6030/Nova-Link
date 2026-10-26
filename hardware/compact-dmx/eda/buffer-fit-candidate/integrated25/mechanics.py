import FreeCAD as A,Part,json,os,math
from pathlib import Path
P=Path(os.environ['NOVA_BUFFER25']);V=A.Vector
old=A.openDocument(str(P.parent/'buffer25-proposal.FCStd'));S={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};A.closeDocument(old.Name)
d=A.newDocument('Integrated25');O={}
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cyl(r,x=27,l=28.4):return Part.makeCylinder(r,l,V(x,30.65,18.1),V(1,0,0))
def add(n,s,note):
 o=d.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis');o.Basis=note;O[n]=o;return s
def roundrect(x0,y0,x1,y1,r,z,h):
 s=box(x0,y0+r,z,x1-x0,y1-y0-2*r,h)
 if x1-x0-2*r>1e-7:s=s.fuse(box(x0+r,y0,z,x1-x0-2*r,y1-y0,h))
 for x in [x0+r,x1-r]:
  for y in [y0+r,y1-r]:s=s.fuse(Part.makeCylinder(r,h,V(x,y,z)))
 return s.removeSplitter()
# Reconstruct filled old aperture before cutting routed radius. Other holes/tongue retained.
pcb=S['PCB_cutout_proposal'].fuse(box(26.5,25.5,10,29.4,10.3,1)).cut(roundrect(26.5,25.5,55.9,35.8,.5,9,3))
for y in [26.9,34.4]:pcb=pcb.cut(roundrect(57.35,y-1.05,58.45,y+1.05,.55,9,3))
base=S['Base_with_bridge'].fuse(S['Cradle0']).fuse(S['Cradle1']).removeSplitter()
lid=S['Lid']
# Lid-supported upper saddles: rigid boss plus separate compliant contact pad.
for i,x in enumerate([28,50]):
 region=box(x,27.65,24,3,6,3)
 lid=lid.fuse(region.cut(cyl(8.6)))
 add('Top_liner'+str(i),cyl(8.6).cut(cyl(8.25)).common(region),'Engineering silicone35-50A, nominal .35 radial, curved contact; compression/adhesive/temperature qualification open')
 lower=box(x,25.8,7,3,9.7,5.5)
 add('Bottom_liner'+str(i),cyl(8.6).cut(cyl(8.25)).common(lower),'Engineering silicone saddle liner .35 radial; intended cell contact, not bonded to sleeve')
# Positive axial capture at peripheral upper rim. Central endface radius6.4 remains free geometrically.
for i,x in enumerate([26.3,55.8]):lid=lid.fuse(box(x,29,24.5,.3,3.3,2.5))
for i,x in enumerate([26.6,55.4]):add('End_pad'+str(i),box(x,29,24.5,.4,3.3,1.7),'Engineering compliant .4 axial pad; .25 combined position/process allocation; vent approval open')
# Four flush countersunk screw envelopes, same mounting axes. Thread engagement represented by deliberate boss overlap only.
for i,(x,y) in enumerate([(7,26),(73,26),(7,48),(73,48)]):
 hole=Part.makeCylinder(1.1,3,V(x,y,26.5)).fuse(Part.makeCone(1,2,1,V(x,y,28)))
 lid=lid.cut(hole)
 screw=Part.makeCylinder(1,21,V(x,y,7)).fuse(Part.makeCone(1,2,1,V(x,y,28)))
 add('M2x22_screw'+str(i),screw,'Engineering flush M2x22 countersunk fastener envelope:head4x1,shaft2; pilot1.7 existing,3mm nominal thread engagement; screw supplier/thread stripping not qualified')
add('Base_integral_cradles',base,'Local additive PA12 base with integral saddles; no adhesive-only cradle attachment. Baseline external shape retained.')
add('Lid_positive_retainer',lid.removeSplitter(),'Local lid has upper saddles and axial stops, fixed by4flush M2 screws; strength/creep/thread gates')
add('PCB_rounded_aperture',pcb.removeSplitter(),'R0.5 internal toolpath,1mm PCB; C23 PTH slots1.1x2.1; manufacturing tolerances unqualified')
for n,s in S.items():
 if n not in ['Base_with_bridge','Lid','Cradle0','Cradle1','PCB_cutout_proposal']:add(n,s,'Retained immutable proposal geometry/envelope; inherited caveats')
for i,y in enumerate([26.9,34.4]):
 a=V(55.4,y,18.1);b=V(56.7,y,18.1);m=V(56.7+1.2/math.sqrt(2),y,16.9+1.2/math.sqrt(2));e=V(57.9,y,16.9);f=V(57.9,y,9)
 wire=Part.Wire([Part.makeLine(a,b),Part.Arc(b,m,e).toShape(),Part.makeLine(e,f)])
 profile=Part.Wire([Part.makeCircle(.41,a,V(1,0,0))]);lead=wire.makePipeShell([profile],True,False)
 add('Lead_'+('positive' if i==0 else 'negative'),lead,'Maxwire.82; seal reference=maxbodyface55.4,straight1.3,R1.2centreline; engineering proposed NOT Eaton forming limit; pin1CAP_POS y26.9, pin2GND_USB y34.4;trim9')
checks=[];allowed=[]
for i,(n,a) in enumerate(O.items()):
 for m,b in list(O.items())[i+1:]:
  vol=a.Shape.common(b.Shape).Volume
  if vol>1e-7:
   # Only thread envelope into existing pilot is intentional. Verify confined to boss z7..10.
   screw=n if n.startswith('M2x22') else m if m.startswith('M2x22') else None
   if screw and 'Base_integral_cradles' in [n,m]:
    common=a.Shape.common(b.Shape);assert common.BoundBox.ZMin>=7-1e-6 and common.BoundBox.ZMax<=10+1e-6
    allowed.append({'a':n,'b':m,'volume_mm3':vol,'basis':'Intentional nominal thread engagement envelope, not a cut thread model'});continue
  checks.append({'a':n,'b':m,'volume_mm3':vol});assert vol<1e-7,(n,m,vol)
worst=Part.makeCylinder(8.4,28.7,V(26.85,30.65,18.1),V(1,0,0))
wp=box(4,23,10,90,28,1.1).cut(roundrect(26.6,25.6,55.8,35.7,.5,9,4))
assert worst.common(wp).Volume<1e-7
rigid_worst={}
for name in ['Base_integral_cradles','Lid_positive_retainer']:
 shape=O[name].Shape;vol=worst.common(shape).Volume;assert vol<1e-7,(name,vol)
 rigid_worst[name]={'volume_mm3':vol,'clearance_mm':worst.distToShape(shape)[0]}
# Liner compression is intentional; quantify overlap instead of hiding it.
compression={n:worst.common(o.Shape).Volume for n,o in O.items() if 'liner' in n or n.startswith('End_pad')}
component_checks=[]
for q in json.loads((P.parent/'placement-boxes.json').read_text())['parts']:
 if q['ref']=='J1':continue # USB courtyard intentionally crosses case; actual connector/stakes are checked in all-solid pairs.
 x,y,x2,y2=q['bounds']
 if x2<=x or y2<=y:continue
 z,h=(11,2.23) if q['side']=='top' else (8.55,1.45)
 if q['ref'] in ['U24','U26','R15']:h=1.45
 envelope=box(x,y,z,x2-x,y2-y,h)
 for n,o in O.items():
  if n in ['PCB_rounded_aperture','NOR_envelope','Connector_external_envelope','Stake0','Stake1','Stake2','Stake3']:continue
  vol=envelope.common(o.Shape).Volume
  assert vol<1e-7,(q['ref'],n,vol)
  component_checks.append({'ref':q['ref'],'solid':n,'volume_mm3':vol})
valid={n:o.Shape.isValid() and all(s.isClosed() for s in o.Shape.Solids) and len(o.Shape.Solids)>0 for n,o in O.items()};assert all(valid.values())
d.recompute();d.saveAs(str(P/'integrated25.FCStd'));Part.export(list(O.values()),str(P/'integrated25.step'))
(P/'mechanics-check.json').write_text(json.dumps({'valid':valid,'pairs':checks,'intended_thread_contacts':allowed,'worst_rounded_aperture_clearance_mm':worst.distToShape(wp)[0],'rigid_worst':rigid_worst,'allocated_liner_compression_mm3':compression,'component_checks':component_checks,'closed_solids':len(valid),'release':False},indent=2)+'\n');print('VALID',len(valid),'PAIRS',len(checks),'THREAD CONTACTS',len(allowed),'APERTURE GAP',worst.distToShape(wp)[0])
