"""Editable screening BReps. Run FreeCADCmd; writes only this candidate directory.
FPC BReps are bounded polygon approximations, not supplier tooling surfaces.
"""
import FreeCAD as A, Part, math,json,os
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']); V=A.Vector
D=A.newDocument('ConstantLengthRotaryPrototype');O={};groups={}
poses=json.loads((P/'poses.json').read_text());B=.30/(2*math.pi)
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def ring(ro,ri,l,x):return cyl(ro,l,x).cut(cyl(ri,l+.02,x-.01))
def sector(ri,ro,start,end,x,l):
 pts=[V(x,r*math.cos(a),r*math.sin(a)) for r,seq in [(ro,range(65)),(ri,range(64,-1,-1))] for i in seq for a in [start+(end-start)*i/64]]
 return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(l,0,0))
def add(n,s,g='stationary',note='Engineering prototype; unqualified material/load/tolerance'):
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Qualification');o.Qualification=note;O[n]=o;groups[n]=g;return s
def rot(s,a):s=s.copy();s.rotate(V(),V(1,0,0),a);return s
# Source dimensions and engineering choices stored in editable document.
sheet=D.addObject('Spreadsheet::Sheet','Parameters')
for i,(k,v) in enumerate([('Core OD',48),('Core length',142),('Housing OD',66),('Housing wall',1),('Active x start',47),('Active width',20),('Flex allocated thickness',.16),('Board radius bottom',25.1),('PCB thickness',1),('GCT USB4105 height',3.31),('GCT stake option',.60),('Index radius',28.5),('Index pitch degrees',15),('Index holes',13),('Active constant length',1046.167655992167)],1):sheet.set('A'+str(i),k);sheet.set('B'+str(i),str(v))
add('StationaryCoreEnvelope',cyl(24,142,0),note='Unchanged external envelope only; no mains repack or barrier approval')
# Stationary inner dielectric guide; relief for fixed tail/backing.
inner=ring(24.6,24.1,22,46)
inner=inner.cut(sector(24,26,-.34,.04,45,24))
# Rotating outer dielectric guide; local relief for rotating tail.
outer=ring(31.3,31,22,46).cut(sector(30,32,-.04,.34,45,24))
# Bearings and retention shoulders, deliberate running radial/axial gaps.
add('FrontJournal',ring(24.8,24.1,2,42))
add('RearJournal',ring(24.8,24.1,2,70))
add('FrontRotatingBearing',ring(26,24.95,2,42.2),'rotor')
add('RearRotatingBearing',ring(26,24.95,2,69.8),'rotor')
# Thin axial cheeks have relief for both fixed and swept rotating clamp ears.
for x,name in [(45.5,'FrontCheek'),(67.5,'RearCheek')]:
 s=ring(32,24.8,1,x)
 s=s.cut(sector(24,32,-math.pi/2-.36,math.pi/2+.36,x-.01,1.02))
 add(name,s,'rotor')
# Tail static spans, exact end radius/slope; broaden to24mm only in static clamp.
def tail(r0,a0,a1):
 pts=[]
 for sign,seq in [(1,range(65)),(-1,range(64,-1,-1))]:
  for i in seq:
   a=a0+(a1-a0)*i/64;r=r0+B*a;den=math.hypot(r,B)
   y=r*math.cos(a)+sign*.08*(r*math.cos(a)+B*math.sin(a))/den
   z=r*math.sin(a)+sign*.08*(r*math.sin(a)-B*math.cos(a))/den
   pts.append(V(45,y,z))
 return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(24,0,0))
# Curved shoes have .02 assembly clearance to tail; preload/shimming is unqualified.
# M1 radial screws grip static ears ONLY; .5mm thread engagement is a qualification gate.
for label,r,a0,a1,g in [('Fixed',25,-.30,0,'stationary'),('Moving',30.5,0,.30,'rotor')]:
 t=tail(r,a0,a1);a=(a0+a1)/2
 if label=='Fixed':back=sector(r-.70,r-.10,a0,a1,45,24);clamp_range=(r+.10,r+.50);direction=-1;headr=r+.50
 else:back=sector(r+.10,r+.70,a0,a1,45,24);clamp_range=(r-.50,r-.10);direction=1;headr=r-.50
 clamps=[]
 for j,x in enumerate([45.75,68.25]):
  clamp=sector(*clamp_range,a0,a1,x-.75,1.5)
  # Assembly clearance holes in ears and upper shoe; pilot in back is explicit thread engagement.
  ax=V(0,direction*math.cos(a),direction*math.sin(a));start=V(x,headr*math.cos(a),headr*math.sin(a))
  through=Part.makeCylinder(.55,2,start-ax*.02,ax)
  clamp=clamp.cut(through);t=t.cut(through)
  pilot=Part.makeCylinder(.38,2,start,ax);back=back.cut(pilot)
  # Flat bearing-seat counterbore removes curved-seat contact uncertainty.
  seat=Part.makeCylinder(.95,.16,start-ax*.16,ax);clamp=clamp.cut(seat)
  shaft=Part.makeCylinder(.5,.98,start,ax)
  head=Part.makeCylinder(.9,.30,start-ax*.30,ax)
  add(label+'Screw'+str(j),shaft.fuse(head),g,'M1 prototype envelope; 0.5mm engagement; strip/preload not qualified')
  add(label+'EarShoe'+str(j),clamp,g)
 add(label+'StaticTail',t,g,'Static enlarged-width tail, 0.16mm; no production FPC outline approval')
 add(label+'Backing',back,g)
add('InnerDielectricGuide',inner)
add('OuterDielectricGuide',outer,'rotor')
# Shell; split-part construction and screws outside flex band remain assembly design gates.
add('RotatingShell',ring(33,32,56.8,42),'rotor')
# Index ring at x43..44.5; holes do not enter the active flex bay.
index=ring(32,26.2,1.5,43)
for a in range(-90,91,15):index=index.cut(cyl(1.1,2,42.8,28.5*math.cos(math.radians(a)),28.5*math.sin(math.radians(a))))
add('IndexRing13Positions',index,'rotor')
# Pin withdrawn leftward; locked pin fits ring hole without side loading FPC.
add('IndexPin',cyl(1,7.7,36,28.5,0).fuse(cyl(2,1.5,34.5,28.5,0)),note='Pull4.2mm toward -X to release; spring/retainer qualification pending')
carrier=box(36,26,-2.5,6,5,5).cut(cyl(1.1,6.2,35.9,28.5,0))
add('IndexCarrier',carrier)
# Stationary two hard-stop blocks and rotating peg on negative-y side; +/-90.
# Finite peg tangent contact offsets stop faces by peg radius1, not centre-angle fiction.
stopbase=ring(30.8,24,1.0,72.5)
track=sector(27.35,29.65,math.pi/2-math.asin(1/28.5),3*math.pi/2+math.asin(1/28.5),72.4,1.2)
stopbase=stopbase.cut(track).cut(box(72.4,24.9,-9.2,1.2,9,18.4))
add('StopTrack',stopbase)
add('StopPeg',cyl(1,1,72.5,-28.5,0),'rotor')
# Board and connector are manufacturer-sized envelopes, not Sol's accepted layout.
pcb=box(72,25.1,-9,25,1,18)
for x in [90.82,94.5]:
 for z in [-4.32,4.32]:pcb=pcb.cut(box(x-.3,25,z-.3,.6,1.2,.6))
add('PowerBoard_TARGET',pcb,'rotor','25x18x1 TARGET only; exact source-board fit pending Sol')
add('Components_TARGET',box(72,26.1,-9,17.5,3.2,18),'placeholder','Reserved envelope, not physical component packing')
add('USB4105ShellEnvelope',box(89.65,26.1,-4.47,7.35,3.31,8.94),'rotor','Drawing B4 2023-12-18; envelope, not supplier CAD; GF-A-060 proposed')
for j,(x,z) in enumerate([(x,z) for x in [90.82,94.5] for z in [-4.32,4.32]]):
 add('USBStake'+str(j),box(x-.225,25.35,z-.1,.45,.75,.2),'rotor','Allocated max .60+.15 below PCB; drawing stake longitudinal datums need actual PCB integration')
# Open endface; no stationary annulus in plug approach. Port envelope is finite.
add('USBPlugScreen',box(97,24.58,-6,12,6.5,12),'screen','Engineering max-height 6.5 drawing screen;12mm width/length engineering only, not universal plug')
# Local axial repair: fixed stop plate ends73.5; target board starts73.8.
for name in ['PowerBoard_TARGET','Components_TARGET','USB4105ShellEnvelope','USBPlugScreen']+['USBStake'+str(j) for j in range(4)]:
 shape=O[name].Shape.copy();shape.translate(V(1.8,0,0));O[name].Shape=shape
# Structural prototype: stationary saddles contact the core envelope; actual split-clamp
# preload and barrier-safe attachment remain gates, not a hole through the mains core.
add('FrontCoreSaddle',ring(25,24,2,40).fuse(box(39,24,-2,3,2,4)))
add('RearCoreSaddle',ring(25,24,2,72))
add('FrontGuideLink',ring(24.6,24.1,2,44))
add('RearGuideLink',ring(24.6,24.1,2,68))
add('PegCarrier',box(73.5,-32,-1.5,1,-0.0+3.5,3),'rotor')
# Capture rotor parts in two editable longitudinal halves with four real screw passages.
for x,name,width in [(44,'FrontFrame',2.5),(67.3,'RearFrame',3.2)]:
 add(name,ring(32,26,width,x).cut(sector(29.4,32,-.06,.36,x-.01,width+.02)),'rotor')
rotor_names=['FrontRotatingBearing','RearRotatingBearing','FrontCheek','RearCheek','OuterDielectricGuide','RotatingShell','IndexRing13Positions','PegCarrier','FrontFrame','RearFrame','MovingBacking']
body=O[rotor_names[0]].Shape
for name in rotor_names[1:]:body=body.fuse(O[name].Shape)
for x in [45.25,68.9]:
 for z in [-29.5,29.5]:
  body=body.cut(Part.makeCylinder(.55,3.2,V(x,0,z),V(0,1,0)))
  body=body.cut(Part.makeCylinder(.38,3.2,V(x,-3.2,z),V(0,1,0)))
  bolt=Part.makeCylinder(.5,6,V(x,-3,z),V(0,1,0)).fuse(Part.makeCylinder(.9,.3,V(x,3,z),V(0,1,0)))
  add('FrameBolt_'+str(x).replace('.','_')+'_'+str(z).replace('-','m').replace('.','_'),bolt,'rotor','M1x6 envelope; polymer thread/creep/torque qualification open')
for name in rotor_names:
 D.removeObject(name);del O[name];del groups[name]
add('RotorHalfPositiveY',body.common(box(30,0,-35,70,35,70)),'rotor')
add('RotorHalfNegativeY',body.common(box(30,-35,-35,70,35,70)),'rotor')

# Active flex three poses; sheets touch static tails at ends, no volumetric overlap intended.
for angle,dat in poses.items():
 pts=[V(47,*p) for p in dat['outer']]+[V(47,*p) for p in reversed(dat['inner'])]
 s=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(20,0,0))
 add('Flex_'+angle.replace('-','minus'),s,'pose'+angle,'Normal-offset finite ribbon; polygon chord bound recorded in poses.json')
D.recompute()
# Selected real BRep checks. Do not discard unexpected collisions.
valid={n:dict(valid=o.Shape.isValid(),solids=len(o.Shape.Solids),volume=o.Shape.Volume) for n,o in O.items()}
assert all(v['valid'] and v['solids']>0 for v in valid.values())
checks=[]
for angle in [-90,0,90]:
 flex=O['Flex_'+str(angle).replace('-','minus')].Shape
 for n,o in O.items():
  if groups[n].startswith('pose') or groups[n] in ['placeholder','screen']:continue
  shape=rot(o.Shape,angle) if groups[n]=='rotor' else o.Shape
  common=flex.common(shape).Volume
  checks.append(dict(pose=angle,a='active_flex',b=n,intersection_mm3=common))
# Neutral all actual non-pose objects: report contacts, all overlaps, no blanket support exclusion.
names=[n for n in O if not groups[n].startswith('pose') and groups[n] not in ['screen','placeholder']]
collisions=[]
for i,a in enumerate(names):
 for b in names[i+1:]:
  bb=O[a].Shape.BoundBox;bc=O[b].Shape.BoundBox
  if not bb.intersect(bc):continue
  vol=O[a].Shape.common(O[b].Shape).Volume
  if vol>1e-6:collisions.append(dict(a=a,b=b,volume_mm3=vol))
# Full selected-pose stationary/moving pairs. Locked pin is checked only at three detents;
# between detents it MUST retract4.2mm, and numeric motion uses that released state.
mechanism_checks=[]
for angle in [-90,0,90]:
 for a in names:
  if groups[a]!='stationary':continue
  for b in names:
   if groups[b]!='rotor':continue
   moving=rot(O[b].Shape,angle)
   if not O[a].Shape.BoundBox.intersect(moving.BoundBox):continue
   vol=O[a].Shape.common(moving).Volume
   mechanism_checks.append(dict(pose=angle,a=a,b=b,intersection_mm3=vol))
result={'selected_mechanism_checks':mechanism_checks,'valid_shapes':valid,'active_flex_selected_pose_checks':checks,'neutral_positive_volume_contacts':collisions,'status':'SCREEN RESULTS, inspect every positive contact; no automatic assembly acceptance','outer_OD_mm':66,'collar_axial_extent_mm':[34.5,98.8],'core_extent_mm':[0,142]}
(P/'cad-checks.json').write_text(json.dumps(result,indent=2)+'\n')
D.recompute();D.saveAs(str(P/'mechanism.FCStd'))
for angle in [-90,0,90]:
 parts=[(rot(O[n].Shape,angle) if groups[n]=='rotor' else O[n].Shape) for n in names]
 parts.append(O['Flex_'+str(angle).replace('-','minus')].Shape)
 Part.makeCompound(parts).exportStep(str(P/('pose-'+str(angle)+'.step')))
# Exploded envelope view: deliberate exploded separation, not assembly fit.
expl=[]
for i,n in enumerate(names):
 s=O[n].Shape.copy();s.translate(V((i%5)*8,0,(i//5)*8));expl.append(s)
Part.makeCompound(expl).exportStep(str(P/'exploded.step'))
print('VALID',len(valid),'FLEX CHECKS',len(checks),'NEUTRAL POSITIVE CONTACTS',len(collisions))
print(json.dumps(collisions,indent=2))
A.closeDocument(D.Name)
