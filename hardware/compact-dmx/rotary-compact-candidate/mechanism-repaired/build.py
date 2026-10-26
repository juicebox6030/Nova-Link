"""Editable screening BReps. Run FreeCADCmd; writes only this candidate directory.
FPC BReps are bounded polygon approximations, not supplier tooling surfaces.
"""
import FreeCAD as A, Part, math,json,os
from pathlib import Path
P=Path(os.environ['NOVA_ROTARY_CANDIDATE']); V=A.Vector
D=A.newDocument('RepairedRotaryPrototype');O={};groups={}
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
for i,(k,v) in enumerate([('Core OD',48),('Core length',142),('Housing OD',66),('Housing wall',1),('Active x start',47),('Active width',20),('Flex allocated thickness',.16),('Board radius bottom',25.1),('PCB thickness',1),('GCT USB4105 maximum height',3.46),('GCT nominal stake',.95),('Index radius',28.5),('Index pitch degrees',15),('Index holes',13),('Active constant length',1046.167655992167)],1):sheet.set('A'+str(i),k);sheet.set('B'+str(i),str(v))
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
def layer(r0,a0,a1,lo,hi,x=45,width=24):
 pts=[]
 for fn,seq in [(hi,range(65)),(lo,range(64,-1,-1))]:
  for i in seq:
   a=a0+(a1-a0)*i/64;r=r0+B*a;den=math.hypot(r,B);off=fn(a)
   pts.append(V(x,r*math.cos(a)+off*(r*math.cos(a)+B*math.sin(a))/den,r*math.sin(a)+off*(r*math.sin(a)-B*math.cos(a))/den))
 return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(width,0,0))
# Contoured shoes and fitted compliant pads; final preload requires qualification.
# M1 radial screws grip static ears ONLY; nominal .4mm thread engagement is unqualified.
for label,r,a0,a1,g in [('Fixed',25,-.30,0,'stationary'),('Moving',30.5,0,.30,'rotor')]:
 t=tail(r,a0,a1);a=(a0+a1)/2
 if label=='Fixed':back=sector(r-.90,r-.40,a0,a1,45,24);clamp_range=(r+.10,r+.50);direction=-1;headr=r+.50
 else:back=sector(r+.40,r+1.00,a0,a1,45,24);clamp_range=(r-.50,r-.10);direction=1;headr=r-.50
 side=-1 if label=='Fixed' else 1
 f=lambda a:min(1.,abs(a)/.08)
 off0=lambda a:side*.08
 off1=lambda a:side*(.08+.05*f(a))
 off2=lambda a:side*(.08+.25*f(a))
 adhesive=layer(r,a0,a1,off0,off1) if side>0 else layer(r,a0,a1,off1,off0)
 stiff=layer(r,a0,a1,off1,off2) if side>0 else layer(r,a0,a1,off2,off1)
 # Ear compression pads bridge the clearance to the tapered stiffener. Outside active width.
 pads=[]
 clamps=[]
 for j,x in enumerate([45.75,68.25]):
  clamp=layer(r,a0,a1,lambda a:.08,lambda a:.50,x-.75,1.5) if side<0 else layer(r,a0,a1,lambda a:-.50,lambda a:-.08,x-.75,1.5)
  # Pad lower boundary is constant-radius backing surface; normal approximation is
  # avoided by constructing it from the same exact stiffener contour and cutting the backing.
  pad=sector(r-.40,r+.40,a0,a1,x-.75,1.5)
  occupied=layer(r,a0,a1,lambda a:-.08-.25*f(a),lambda a:.08+.25*f(a),x-.76,1.52)
  pad=pad.cut(occupied)
  pad=pad.common(sector(r-.40,r,a0,a1,x-.75,1.5) if side<0 else sector(r,r+.40,a0,a1,x-.75,1.5))
  # Assembly clearance holes in ears and upper shoe; pilot in back is explicit thread engagement.
  ax=V(0,direction*math.cos(a),direction*math.sin(a));start=V(x,headr*math.cos(a),headr*math.sin(a))
  through=Part.makeCylinder(.55,2,start-ax*.02,ax)
  clamp=clamp.cut(through);t=t.cut(through);adhesive=adhesive.cut(through);stiff=stiff.cut(through);pad=pad.cut(through)
  pilot=Part.makeCylinder(.38,2,start,ax);back=back.cut(pilot)
  # Flat bearing-seat counterbore removes curved-seat contact uncertainty.
  seat=Part.makeCylinder(.95,.16,start-ax*.16,ax);clamp=clamp.cut(seat)
  shaft=Part.makeCylinder(.5,1.30,start,ax)
  head=Part.makeCylinder(.9,.30,start-ax*.30,ax)
  clamp=clamp.cut(Part.makeCylinder(.95,.31,start-ax*.30,ax))
  add(label+'EarPad'+str(j),pad,g,'Engineered compliant shim; exact unloaded contact envelope; preload/material pending')
  add(label+'Screw'+str(j),shaft.fuse(head),g,'M1 prototype envelope; 0.4mm nominal engagement; strip/preload not qualified')
  add(label+'EarShoe'+str(j),clamp,g)
 add(label+'Adhesive',adhesive,g,'0.05mm static adhesive tapered over last0.08rad; supplier qualification pending')
 add(label+'Stiffener',stiff,g,'0.20mm static polyimide stiffener tapered over last0.08rad, outside active bend')
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
pin=cyl(1,11.8,32.5,28.5,0).fuse(cyl(.6,.8,31.7,28.5,0)).fuse(cyl(1.8,.6,40.8,28.5,0))
knob=cyl(2,1.5,31,28.5,0).cut(cyl(.5,.81,31.69,28.5,0)).cut(box(30.99,26.4,-.3,.31,4.2,.6))
add('IndexKnob',knob,'pin','Removable M1.2 threaded knob with0.6wide face slot; required assembly order; thread-lock qualification open')
pin=pin.cut(box(40.79,26.6,1.5,.62,3.8,.4))
add('IndexPin',pin,'pin','Locked engagement1.3mm; captive flange; pull4.2mm; no hold-open bypass')
carrier=cyl(3,8.8,34,28.5,0).cut(cyl(2.4,1.01,33.99,28.5,0)).cut(cyl(2.2,6.4,35,28.5,0)).cut(cyl(1.1,1.5,41.4,28.5,0))
# Rear travel stop is on removable cap, so the flange can enter the carrier bore.
carrier=carrier.cut(cyl(3.1,.71,42.1,28.5,0).cut(cyl(2.3,.73,42.09,28.5,0)))
carrier=carrier.fuse(box(36.6,28,1.65,4.8,1,.65))
carrier=carrier.fuse(box(39,24,-2,3,2,4))
add('IndexCarrier',carrier)
cap=cyl(2.6,1,34,28.5,0).fuse(cyl(3.2,.6,33.4,28.5,0)).cut(cyl(1.1,1.62,33.39,28.5,0))
cap=cap.fuse(cyl(2.15,1.6,35,28.5,0).cut(cyl(1.7,1.62,34.99,28.5,0)))
for z in [-2.6,2.6]:cap=cap.cut(cyl(.3,.41,33.39,28.5,z))
add('IndexRearCap',cap,note='Explicit0.2mm radial thread envelope in carrier; removable only with tool; safety retention gate')
add('IndexSpring',cyl(1.6,5.8,35,28.5,0).cut(cyl(1.4,5.82,34.99,28.5,0)),'spring','Engineering spring envelope: wire0.20,7total coils,solid1.4,free7.0,k0.114N/mm target; installed5.8/released1.6; preload0.137N/release0.616N; wire0.20 active5,total7')
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
add('Components_TARGET',box(72,26.1,-9,17.2,3.61,18),'placeholder','Reserved envelope, not physical component packing')
add('USB4105ShellEnvelope',box(89.35,26.1,-4.545,7.65,3.46,9.09),'rotor','Drawing B4 2023-12-18; envelope, not supplier CAD; GF-A placeholder, maximum body envelope; source axial layout pending')
for j,(x,z) in enumerate([(x,z) for x in [90.82,94.5] for z in [-4.32,4.32]]):
 add('USBStake'+str(j),box(x-.225,24.9,z-.1,.45,1.2,.2),'rotor','Placeholder <=0.2mm below board; datum/footprint pending axial source layout')
# Open endface; no stationary annulus in plug approach. Port envelope is finite.
add('USBPlugScreen',box(97,24.58,-6,12,6.5,12),'screen','Engineering max-height 6.5 drawing screen;12mm width/length engineering only, not universal plug')
# Local axial repair: fixed stop plate ends73.5; target board starts73.8.
for name in ['PowerBoard_TARGET','Components_TARGET','USB4105ShellEnvelope','USBPlugScreen']+['USBStake'+str(j) for j in range(4)]:
 shape=O[name].Shape.copy();shape.translate(V(1.8,0,0));O[name].Shape=shape
# Structural prototype: stationary saddles contact the core envelope; actual split-clamp
# preload and barrier-safe attachment remain gates, not a hole through the mains core.
add('FrontCoreSaddle',ring(25,24,2,40).fuse(box(39,24,-2,3,2,4)))
add('RearCoreSaddle',ring(25,24,2,72))
for name,x,bolt_x in [('FrontGuideLink',44,45.75),('RearGuideLink',68,68.25)]:
 link=ring(24.6,24.1,2,x)
 a=-.15;axis=V(0,-math.cos(a),-math.sin(a));start=V(bolt_x,25.5*math.cos(a),25.5*math.sin(a))
 link=link.cut(Part.makeCylinder(.55,2,start,axis))
 add(name,link)
# All former overlapping stationary pieces form one machinable bonded/split-spool prototype.
stationary_names=['FrontJournal','RearJournal','InnerDielectricGuide','FrontCoreSaddle','RearCoreSaddle','FrontGuideLink','RearGuideLink','FixedBacking','StopTrack','IndexCarrier']
spool=O[stationary_names[0]].Shape
for name in stationary_names[1:]:
 print('FUSE',name,O[name].Shape.isValid(),O[name].Shape.Volume,flush=True)
 spool=spool.fuse(O[name].Shape)
 print('RESULT',spool.isNull(),len(spool.Solids),flush=True)
for name in stationary_names:
 D.removeObject(name);del O[name];del groups[name]
spool=spool.cut(cyl(24.1,142,0))
add('StationarySpool',spool)
for name in ['FixedEarPad0','FixedEarPad1']:O[name].Shape=O[name].Shape.cut(spool)
add('CoreBondFront',ring(24.1,24,2,40),note='0.10mm insulating structural bondline prototype; adhesion/creep/safety qualification open')
add('CoreBondRear',ring(24.1,24,2,72),note='0.10mm insulating structural bondline prototype; adhesion/creep/safety qualification open')
add('PegCarrier',box(73.5,-32,-1.5,1,-0.0+3.5,3),'rotor')
# Capture rotor parts in two editable longitudinal halves with four real screw passages.
for x,name,width in [(44,'FrontFrame',2.5),(67.3,'RearFrame',3.2)]:
 add(name,ring(32,26,width,x).cut(sector(29.4,32,-.06,.36,x-.01,width+.02)),'rotor')
rotor_names=['FrontRotatingBearing','RearRotatingBearing','FrontCheek','RearCheek','OuterDielectricGuide','RotatingShell','IndexRing13Positions','StopPeg','PegCarrier','FrontFrame','RearFrame','MovingBacking']
body=O[rotor_names[0]].Shape
# Two real outer radial bridges join backing to shell, only outside active bend.
for x in [45,68]:body=body.fuse(sector(31.35,32.15,.08,.22,x,1))
for name in rotor_names[1:]:body=body.fuse(O[name].Shape)
for angle in range(-90,91,15):
 a=math.radians(angle);body=body.cut(cyl(1.1,1.9,42.8,28.5*math.cos(a),28.5*math.sin(a)))
for x in [45.75,68.25]:
 a=.15;body=body.cut(Part.makeCylinder(.70,7,V(x,24*math.cos(a),24*math.sin(a)),V(0,math.cos(a),math.sin(a))))
for x in [45.25,68.9]:
 for z in [-29.5,29.5]:
  body=body.cut(Part.makeCylinder(.95,35,V(x,3,z),V(0,1,0)))
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
valid={n:dict(valid=o.Shape.isValid(),solids=len(o.Shape.Solids),closed=all(q.isClosed() for q in o.Shape.Solids),volume=o.Shape.Volume) for n,o in O.items()}
(P/'validity.json').write_text(json.dumps(valid,indent=2)+'\n')
assert all(v['valid'] and v['closed'] and v['solids']==1 for v in valid.values()),str({n:v for n,v in valid.items() if not v['valid'] or v['solids']!=1})
D.saveAs(str(P/'mechanism.FCStd'))
(P/'groups.json').write_text(json.dumps(groups,indent=2)+'\n')
# All physical pieces, without simultaneous alternative poses or nonphysical bay/plug reservations.
names=[n for n in O if not groups[n].startswith('pose') and groups[n] not in ['placeholder','screen']]
def state(n,angle,released):
 s=O[n].Shape.copy()
 if groups[n]=='rotor':s=rot(s,angle)
 if groups[n]=='pin' and released:s.translate(V(-4.2,0,0))
 if groups[n]=='spring' and released:s=cyl(1.6,1.6,35,28.5,0).cut(cyl(1.4,1.62,34.99,28.5,0))
 return s
# Component-specific permitted thread volumes; bounds independently checked by verifier.
allowed={tuple(sorted((n,'StationarySpool'))):.20 for n in ['FixedScrew0','FixedScrew1']}
for n in ['MovingScrew0','MovingScrew1']:allowed[tuple(sorted((n,'RotorHalfPositiveY')))]=.20
for n in names:
 if n.startswith('FrameBolt'):allowed[tuple(sorted((n,'RotorHalfNegativeY')))]=1.05
allowed[tuple(sorted(('IndexRearCap','StationarySpool')))]=3.2
allowed[tuple(sorted(('IndexKnob','IndexPin')))]=.30
results=[];residual=[];cache={}
for angle in [-90,0,90]:
 for released in [False,True]:
  shapes={n:state(n,angle,released) for n in names};shapes['ActiveFlex']=O['Flex_'+str(angle).replace('-','minus')].Shape
  keys=list(shapes)
  for i,a in enumerate(keys):
   for b in keys[i+1:]:
    sa,sb=shapes[a],shapes[b];vol=0.
    ga=groups.get(a,'flex');gb=groups.get(b,'flex')
    ka=angle;kr=released
    if ga==gb=='rotor':ka=None;kr=None
    elif ga==gb=='stationary':ka=None;kr=None
    elif ga in ['stationary','pin','spring'] and gb in ['stationary','pin','spring']:ka=None
    key=(a,b,ka,kr)
    if key in cache:vol=cache[key]
    else:
     if sa.BoundBox.intersect(sb.BoundBox):vol=sa.common(sb).Volume
     cache[key]=vol
    permit=allowed.get(tuple(sorted((a,b))),0)
    row=dict(angle=angle,released=released,a=a,b=b,intersection_mm3=vol,thread_limit_mm3=permit)
    results.append(row)
    if vol>max(permit,1e-6):residual.append(row)
  Part.makeCompound(list(shapes.values())).exportStep(str(P/('released' if released else 'locked')/('pose-'+str(angle)+'.step')))
checks={'valid_shapes':valid,'pairs':results,'residual':residual,'status':'PASS' if not residual else 'FAIL','allowed_thread_pairs':[{'parts':list(k),'max_mm3':v} for k,v in allowed.items()]}
(P/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
# Explode in meaningful axial groups; inspection geometry, no hidden intersection acceptance.
parts=[]
for n in names:
 s=O[n].Shape.copy();dx=0;dy=0
 if n=='RotorHalfPositiveY':dy=18
 elif n=='RotorHalfNegativeY':dy=-18
 elif groups[n] in ['pin','spring'] or n=='IndexRearCap':dx=-15
 elif 'Moving' in n:dx=12
 elif 'Fixed' in n:dx=-8
 s.translate(V(dx,dy,0));parts.append(s)
Part.makeCompound(parts).exportStep(str(P/'exploded.step'))
print('OBJECTS',len(valid),'PAIRS',len(results),'RESIDUAL',len(residual),flush=True)
print(json.dumps(residual,indent=2),flush=True)
A.closeDocument(D.Name)
