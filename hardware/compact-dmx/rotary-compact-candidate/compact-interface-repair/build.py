"""Copied mechanical interface prototype. No change to either frozen electricalboard."""
from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;D=A.newDocument('CompactInterfaceRepair');O={};G={};notes={};contacts=[]
def box(x,y,z,a,b,c):return Part.makeBox(a,b,c,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def add(n,s,g,note=''):
 print("ADD",n,"null",s.isNull(),flush=True);assert (n.startswith('COL_Flex_') or s.isValid()) and s.isClosed() and len(s.Solids)==1,(n,'not one validclosedsolid',len(s.Solids))
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis').Basis=note;O[n]=o;G[n]=g;notes[n]=note;return s
old=A.openDocument(str(P.parent/'combined-compact-allocation/allocation.FCStd'));og=json.loads((P.parent/'combined-compact-allocation/groups.json').read_text());oldS={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')};A.closeDocument(old.Name)
# Keep actual mechanism and mainscomparison allocations; removeold5Vsource entirely.
skip=['COL_SRC_','COL_BoardRetainer','COL_BoardEndRetainer','COL_TailClamp','COL_StaticDevelopedFanout','COL_StaticFanoutChannelReserve','S12_','LV_']
for n,s in oldS.items():
 if any(n.startswith(x) for x in skip) or n in ['StationaryCoreTube','Carrier61x32PlanningPlate','L_FuseToCarrier','N_TrunkToCarrier','COL_RotorHalfPositiveY','COL_RotorHalfNegativeY','COL_USBPlugApproach','USBRelief','USBCable','LVExitPassageReserve']:continue
 if n.startswith('OutputJoint_') or n=='OutputEndcapBlank':s.translate(V(5,0,0))
 if n.startswith('Trunk_') or n.startswith('TrunkTolerance_'):
  r=2.75 if n.startswith('TrunkTolerance_') else 2.25
  yy={'L':-8,'N':0,'PE':8}[n.rsplit('_',1)[-1]];s=s.fuse(cyl(r,5,90,yy,-16))
 add(n,s,og[n],notes.get(n,'Frozen comparison part; sourceconstruction/endcap qualification unchanged'))
exec(compile((P/'tail-copper.py').read_text(),str(P/'tail-copper.py'),'exec'))
prim=A.openDocument(str(P/'primary-repair.FCStd'))
for n in ['Carrier61x32PlanningPlate','L_FuseToCarrier','N_TrunkToCarrier']:add(n,prim.getObject(n).Shape.copy(),'carrier' if n.startswith('Carrier') else'branch','Copied primaryrepair; fouractualØ2pinpassages; unrouted pads/insulation/retention UNMET')
A.closeDocument(prim.Name)
core=cyl(24,87,0).cut(cyl(21.5,87,0))
# Ruledstatic extension: parallelX generators, no materialtwist. Sourcepath endsunchanged.
f=json.loads((P/'fanout-probe.json').read_text());ss=f['samples'];ss=ss[::16]+[ss[-1]]
def ruled(samples,lo,hi,x0=24.2,width=20):
 wires=[]
 for y,z,ny,nz in samples:
  pts=[V(x0+dx,y+off*ny,z+off*nz) for dx,off in [(0,lo),(width,lo),(width,hi),(0,hi)]];wires.append(Part.makePolygon(pts+[pts[0]]))
 return Part.makeLoft(wires,True,True)
fan=ruled(ss,-.08,.08);channel=ruled(ss,-.30,.30,23.9,20.6)
core=core.cut(channel)
# Exactboundedcut in copied stationaryspool; preserveone connectedpart.
O['COL_StationarySpool'].Shape=O['COL_StationarySpool'].Shape.cut(channel)
assert len(O['COL_StationarySpool'].Shape.Solids)==1 and O['COL_StationarySpool'].Shape.isValid()
notes['COL_StationarySpool']='Localstaticfanoutclearance cut only; activepath/stop/index untouched; guide-load/elastic qualification UNMET'
# Two8mm copperlanes at70um;25/65um dielectric proposed, not supplier stack acceptance.
cu=[]
for pin,x0 in [('1',25.7),('2',34.7)]:
 s=ruled(ss,-.055,.015,x0,8);cu.append(s);add('FixedFanoutCopper'+pin,s,'stationary','Singlelayer RA70um; pin1positive,pin2return; no vias/active platedfeatures')
# Remove copper from laminate and back-accesswindows only atstaticpads.
diel=fan
for s in cu:diel=diel.cut(s)
# Backsidewindows exposeoppositecopperface atstationarypad withouttracecrossover.
for x0 in [25.7,34.7]:diel=diel.cut(box(x0-.05,14.4,-6.85,8.1,.5,2.1))
# Splitdielectric layers if necessary, eachactualsolid getsnamedandvalidated.
for i,s in enumerate(diel.Solids):add('FixedFanoutDielectric'+str(i),s,'stationary','Proposed25umcover/65umsubstrate; two-sidedaccess perMinco p10 capability, stack/adhesiveprocess UNMET')
# Core support webs belowstationaryboard; avoidmainsbypass atZ-16,Y<=8.
webs=[]
for x in [21.2,46.2]:
 for z in [-22,8]:webs.append(box(x,12.5,z,2,1,14).common(cyl(24,87,0)))
for s in webs:core=core.fuse(s)
# Loweredge seats touchPCBbottomY13.5; outboardcorner caps receiveaxialM1screws.
for x in [21.2,45.2]:
 for z in [-10,7.8]:core=core.fuse(box(x,12.5,z,2,1,2.2))
for x in [23.2,44.2]:
 for z in [-10,8]:core=core.fuse(box(x,12.5,z,1,2.26 if z<0 else 2.7,2))
core=core.fuse(box(23.2,13.6,-10,22,1,2))
add('StationaryCoreWithSupports',core,'housing','Ø48x87; boundedfanoutslot andPCBedge supports; coreinsulation/mechanicalapproval UNMET')
# Actualsourcepad extraction; copperthickness35um is engineeringnominal, board unchanged.
boards=json.loads((P/'actual-boards.json').read_text());pads={};bodies=[]
def rounded(w,h,r,z,t):
 if r<1e-8:return box(-w/2,-h/2,z,w,h,t)
 r=min(r,w/2,h/2);s=box(-w/2+r,-h/2,z,w-2*r,h,t) if w>2*r else None
 q=box(-w/2,-h/2+r,z,w,h-2*r,t) if h>2*r else None
 if s is None:s=q
 elif q is not None:s=s.fuse(q)
 for x in [-w/2+r,w/2-r]:
  for y in [-h/2+r,h/2-r]:
   q=Part.makeCylinder(r,t,V(x,y,z));s=q if s is None else s.fuse(q)
 return s
transforms={'stationary':(22.2,14.5,8),'rotating':(52.2,26.1,13)}
def tr(s,zone):
 s=s.copy();s.rotate(V(0,0,0),V(1,0,0),-90);s.translate(V(*transforms[zone]));return s
for zone,b in boards.items():
 W,H,T=b['size'];pcb=box(0,0,-1,W,H,1)
 for comp in b['components']:
  for p in comp['pads']:
   dw,dh=p['drill']
   if dw:
    hole=rounded(dw,dh,min(dw,dh)/2,-1.2,1.4);hole.rotate(V(0,0,0),V(0,0,1),-p['angle']);hole.translate(V(p['x'],p['y'],0));pcb=pcb.cut(hole)
    if p['number'].startswith('S'):
     stake=rounded(dw,dh,min(dw,dh)/2,-1.2,1.2);stake.rotate(V(0,0,0),V(0,0,1),-p['angle']);stake.translate(V(p['x'],p['y'],0));add(zone+'_'+comp['ref']+'_'+p['number']+'_StakeReserve',tr(stake,zone),zone+'_stake','Hole-sizedstake sweep; supplierprofile unqualified,<=.2underside')
 add(zone+'_PCB',tr(pcb,zone),zone,'ByteforbytefrozenS12 PCB geometry; holes fromactualpads, copper/netlist unchanged')
 for comp in b['components']:
  ref=comp['ref'];info=comp['body'];w,h=info['body_allocation_mm'];ht=info['height_allocation_mm']
  if ht>0:
   s=box(-w/2,-h/2,0,w,h,ht)
   if ref=='J1':s.translate(V(0,(-5.48+2.17)/2,0))
   s.rotate(V(0,0,0),V(0,0,1),-comp['angle']);s.translate(V(comp['x'],comp['y'],0))
   group=zone+'_landing_reserve' if ref in ['J0','J2','J3'] else zone
   add(zone+'_'+ref+'_Body',tr(s,zone),group,'Actualsavedplacement/bodyheightallocation; fabricatedlandbody isonlysolder/leadreserve')
  for j,p in enumerate(comp['pads']):
   if not p['number']:continue
   w,h=p['size'];s=rounded(w,h,min(w,h)/2 if p['shape']==2 else p['round_radius'],0,.035);s.rotate(V(0,0,0),V(0,0,1),-p['angle']);s.translate(V(p['x'],p['y'],0))
   if p['drill'][0]:
    q=rounded(*p['drill'],min(p['drill'])/2,-.1,.3);q.rotate(V(0,0,0),V(0,0,1),-p['angle']);q.translate(V(p['x'],p['y'],0));s=s.cut(q)
   if s.Volume>1e-10:
    name=zone+'_'+ref+'_Pad'+p['number']+'_'+str(j);add(name,tr(s,zone),zone+'_pad',p['net']+'; actualnumber/size/angle;35umcopper engineeringnominal');pads[(zone,ref,p['number'])]=name
# Actualsolderpreforms connectback-accesscopper tosame two frozen J2lands.
for pin in ['1','2']:
 pad=O[pads['stationary','J2',pin]].Shape;s=pad.copy();s.scale(1) # no footprint alteration
 # Extrudeactualpadbottomoutline alongnormalY tofill0.13 gap, preservingroundedoutline.
 face=min(s.Faces,key=lambda x:abs(x.CenterOfMass.y-14.535))
 # Useexplicitroundrectmatchingactual8x2,r.2, transformed fromlocalZ=.035..
 x=7.5 if pin=='1' else 16.5
 solder=rounded(8,2,.2,.035,.13);solder.translate(V(x,13.8,0));add('J2_Solder'+pin,tr(solder,'stationary'),'stationary','Namedunsolderedpreform8x2x.13, matchedroundedland; wetting/process/alignment unqualified')
# Fixedfanoutshoe onstraightoutsideboardend, pluscoreconnectedside supports.
shoe=box(23.2,14.76,-10,22,1.0,2)

# This explicitretainer cannot be assumed attached until its screws/support clear allinterfaces.
add('FixedFanoutShoe',shoe,'stationary','PEEKshoe22x2x1 inclretentionears; twoM1; sourceclamp20.5wide extendedonlyatstationaryears')
# Sourceboardupperretainers atfourcorners; no holes drilled inactualPCB.
for side,x in [('Front',21.2),('Rear',45.2)]:
 for sign,z in [('m',-10),('p',7.85)]:
  cap=box(x,13.5,z,2,2.26 if sign=='m' else 1.5,2.15).cut(box(22.2,13.49,-8,24,1.16,16))
  # ActualM1clearance; axisX, outsideboard atZ+/-9.
  zz=-9 if sign=='m' else 9;hole=cyl(.6,2.2,x-.1,14.1,zz);cap=cap.cut(hole)
  add('StationaryCornerCap'+side+sign,cap,'stationary','PEEKcapturelip .15topplay; M1clearanceoutsideactualPCB; sourcecopper untouched')
# Sourcewire guide atZ8.5..10.1 lies beyond PCBedgeZ8.0; same retained upper cap.
wirebase=box(23.2,13.5,8.5,8.3,1.535,1.6)
wirecap=box(23.2,15.035,8.5,8.3,1.465,1.6)
for x in [25.2,29.2]:
 bore=Part.makeCylinder(1.0,1.8,V(x,15.035,8.4),V(0,0,1));wirebase=wirebase.cut(bore);wirecap=wirecap.cut(bore)
O['StationaryCoreWithSupports'].Shape=O['StationaryCoreWithSupports'].Shape.fuse(wirebase)
# Positivecorner cap's outsideedge web reaches its guide; no screw through PCB/copper.
join=box(21.2,14.9,8.5,2.1,1.6,1.6)
O['StationaryCornerCapFrontp'].Shape=O['StationaryCornerCapFrontp'].Shape.fuse(join).fuse(wirecap)
notes['StationaryCornerCapFrontp']='AxialM1-retained wireguide upperhalf; nominalOD2 channels, strainrelief pull/creep NOT qualified'
# Fused lower bridge retained by two existing axial M1 cap screws; no radial tool through flex.
bridge=O['FixedFanoutShoe'].Shape
for n in ['StationaryCornerCapFrontm','StationaryCornerCapRearm']:
 bridge=bridge.fuse(O[n].Shape);D.removeObject(n);del O[n];del G[n]
O['FixedFanoutShoe'].Shape=bridge
exec(compile((P/'attachments.py').read_text(),str(P/'attachments.py'),'exec'))
# Enlargedouterrotor only. Preserveoldfront/index/stop/ear geometry, deleteoldsourcebay.
for sign,n in [(1,'PositiveY'),(-1,'NegativeY')]:
 oldhalf=oldS['COL_RotorHalf'+n].common(box(-10,-50,-50,61.2,100,100))
 half=box(-10,0 if sign==1 else -50,-50,110,50,100)
 shell=cyl(35,65,19.2).cut(cyl(33.75,65.02,19.19)).common(half)
 bridge=cyl(35,4,19.2).cut(cyl(32,4.02,19.19)).common(half)
 s=oldhalf.fuse(shell).fuse(bridge).fuse(cyl(35,2,45.2).cut(cyl(31.9,2.02,45.19)).common(half))
 if sign==-1:s=s.cut(box(50.7,-33,-2,1,6,4)).fuse(box(51.0,-31.5,-2.5,13,3,5)).fuse(box(62,-34.5,-2.5,2,6,5)).fuse(cyl(1,1.3,49.7,-28.5,0))
 if sign==1:
  s=s.fuse(cyl(35,.7,51.2).cut(cyl(24.3,.72,51.19)).common(half))
  for z in [-13,12.2]:s=s.fuse(box(51.9,24.3,z,32.5,.8,.8))
  # FullUSBbody+assemblyclearance, no assumed matingplane.
  s=s.cut(box(78.47,25.85,-4.795,8.15,3.96,9.59))
  # ExternalFPCclampreserve andactualnewbodyclearance.
  s=s.cut(box(52.7,25.85,-18.25,21,2.5,5.5))
  for x in [22.45,46.1]:
   for z in [-29.5,29.5]:s=s.cut(Part.makeCylinder(.95,38,V(x,0,z),V(0,1,0)))
 add('RotorHalf'+n,s,'rotating','OuterR35 inner33.75 drivenbyS12clamp; oldlock/stopregion retained; strength/thermalgate')
exec(compile((P/'moving.py').read_text(),str(P/'moving.py'),'exec'))
# EngineeringUSBapproach frombodyend86.37, notmanufacturer matingplane.
add('USBPlugApproach',box(86.37,24.58,-6,12,6.5,12),'screen','Engineering12x6.5x12 plug, not universalfit')
add('USBRelief',box(98.37,24.58,-6,18,6.5,12),'screen','Engineering18mmrelief')
add('USBCable',cyl(3,80,116.37,27.83,0),'screen','EngineeringØ6x80 axialcable')
APPLY_TO_GENERATOR=True
exec(compile((P/'seat-repair.py').read_text(),str(P/'seat-repair.py'),'exec'))
D.recompute();D.saveAs(str(P/'interface-prototype.FCStd'))
Part.export([o for n,o in O.items() if not G[n].endswith('_pad') and G[n] not in ['collar_pose-90','collar_pose90','UNMET_INTERFACE','screen','collar_reserve','insulation','tolerance','trunk_tolerance','support','access']],str(P/'interface-prototype.step'))
(P/'groups.json').write_text(json.dumps(G,indent=2)+'\n');(P/'notes.json').write_text(json.dumps(notes,indent=2)+'\n');(P/'pad-objects.json').write_text(json.dumps({'|'.join(k):v for k,v in pads.items()},indent=2)+'\n');print('SAVED',len(O),flush=True)
