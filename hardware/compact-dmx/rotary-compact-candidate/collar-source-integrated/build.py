"""Local integration only. Immutable source BReps; engineering support/fanout solids."""
import FreeCAD as A,Part,math,json
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parent;V=A.Vector
D=A.newDocument('CollarSourceIntegrated');O={};G={}
def box(x,y,z,l,w,h):return Part.makeBox(l,w,h,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def ring(ro,ri,l,x):return cyl(ro,l,x).cut(cyl(ri,l+.02,x-.01))
def add(n,s,g,note='Engineering prototype allocation; not manufacturing qualified'):
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Qualification');o.Qualification=note;O[n]=o;G[n]=g;return o
def transform(s):
 s=s.copy();s.rotate(V(),V(1,0,0),-90);s.translate(V(75,26.1,10));return s
old=A.openDocument(str(B/'mechanism-repaired/mechanism.FCStd'));oldg=json.loads((B/'mechanism-repaired/groups.json').read_text())
removed={'PowerBoard_TARGET','Components_TARGET','USB4105ShellEnvelope','USBPlugScreen'}|{'USBStake'+str(i) for i in range(4)}
for o in old.Objects:
 if hasattr(o,'Shape') and o.Name not in removed:add(o.Name,o.Shape.copy(),oldg[o.Name],o.Qualification)
A.closeDocument(old.Name)
src=A.openDocument(str(B/'source-axial-routing/source-axial-envelopes.FCStd'));source=[];reserves=[]
for o in src.Objects:
 if hasattr(o,'Shape'):
  reserve=any(t in o.Name for t in ['reserved','access_volume','clearance_proposal'])
  add('SRC_'+o.Name,transform(o.Shape),'reserve' if reserve else 'rotor','Immutable source saved allocation transformed X=75+x,Y=26.1+z,Z=10-y; supplier profile/assembly gates retained')
  (reserves if reserve else source).append('SRC_'+o.Name)
A.closeDocument(src.Name)
# Extend the two shell halves axially only; unchanged ID/OD.
for name,ys in [('RotorHalfPositiveY',0),('RotorHalfNegativeY',-35)]:
 ext=ring(33,32,3.2,98.8).common(box(98,ys,-35,5,35,70))
 O[name].Shape=O[name].Shape.fuse(ext).removeSplitter()
# Copper-free 0.20mm edge capture. Wide supporting webs remain outside PCB.
railparts=[]
for z in [-10.6,9.8]:
 railparts.append(box(75,24.75,z,27,.35,.8))
 # sidewall and upper capture lip; nominal .15mm axial-normal play allows +.1 board thickness.
 zw=-10.5 if z<0 else 10.1
 railparts.append(box(75,24.75,zw,27,1.6,.4))
 railparts.append(box(96 if z<0 else 75,26.34,z,6 if z<0 else 27,.50,.8))
 # Leave the negative-Z FPC exit unobstructed; retain the last6mm of that edge.
 # connect to shell via web below edge, leaving source bottom central region open
 wz=-21 if z<0 else 10.6
 railparts.append(box(75,24.75,wz,27,.5,10.4))
# insertion rear stops, touch board X75 only within copper-free edge strip
for z in [-10.6,9.8]:railparts.append(box(74.7,24.75,z,.3,1.6,.8))
# Separate end retainer, below component region and clear of core.
gate=box(102,24.5,-11.3,1,.6,22.6)
for z in [-11.3,9.8]:gate=gate.fuse(box(102,25.1,z,1,1.25,1.5))
# screw seats in supporting webs; no PCB holes or contacts drilled
for z in [-11,11]:
 railparts.append(box(99.5,24.6,z-.8,2.5,2.1,1.6))
 gate=gate.fuse(box(102,24.6,z-.8,1,2.1,1.6))
 gate=gate.cut(cyl(.55,1.1,101.95,25.65,z))
 shaft=cyl(.5,2.5,100.5,25.65,z);head=cyl(.9,.4,103,25.65,z)
 add('BoardRetainerScrew_'+str(z).replace('-','m'),shaft.fuse(head),'rotor','M1 screw envelope;1.5mm pilot engagement; preload/creep gate')
add('BoardEndRetainer',gate,'rotor')
# External FPC clamp: supported solder tongue, no force into component tops.
base=box(73.7,25.8,-14,23.6,.6,2)
shoe=box(73.7,26.56,-14,23.6,.94,2)
for x in [74.4,96.6]:
 base=base.fuse(box(x-.7,25.0,-14,.0+1.4,1.4,2))
 axis=V(0,1,0)
 base=base.cut(Part.makeCylinder(.38,2,V(x,25,-13),axis))
 shoe=shoe.cut(Part.makeCylinder(.55,1,V(x,26.55,-13),axis))
 bolt=Part.makeCylinder(.5,1.7,V(x,25.8,-13),axis).fuse(Part.makeCylinder(.9,.3,V(x,27.5,-13),axis))
 add('TailClampScrew_'+str(x).replace('.','_'),bolt,'rotor','M1 .6mm nominal thread engagement; engineering preload envelope')
railparts.append(base);add('TailClampShoe',shoe,'rotor')
# Static developable fanout: all cross-section generators parallel to X.
# radius Hermite blend then circular path, R2.5 terminal bend, straight solder tongue.
b=.3/(2*math.pi);t0=.3;t1=.9;r0=30.5+b*t0;r1=31.6;rb=2.5;endY=26.48
te=2*math.pi-math.acos((endY-rb)/(r1-rb));samples=[]
def radial(t):
 if t>=t1:return r1,0.
 u=(t-t0)/(t1-t0);h=t1-t0
 r=(2*u**3-3*u*u+1)*r0+(u**3-2*u*u+u)*h*b+(-2*u**3+3*u*u)*r1
 dr=((6*u*u-6*u)*r0+(3*u*u-4*u+1)*h*b+(-6*u*u+6*u)*r1)/h
 return r,dr
for i in range(241):
 t=t0+(te-t0)*i/240;r,dr=radial(t);y=r*math.cos(t);z=r*math.sin(t);dy=dr*math.cos(t)-r*math.sin(t);dz=dr*math.sin(t)+r*math.cos(t);norm=math.hypot(dy,dz)
 u=min(1,(t-t0)/(te-t0));xc=57+28.5*(10*u**3-15*u**4+6*u**5)
 samples.append([xc,y,z,dz/norm,-dy/norm])
y0,z0=samples[-1][1:3];beta=te+math.pi/2-2*math.pi;cy=y0-rb*math.sin(beta);cz=z0+rb*math.cos(beta)
for i in range(1,33):
 a=beta+(math.pi/2-beta)*i/32;samples.append([85.5,cy+rb*math.sin(a),cz-rb*math.cos(a),math.sin(a),-math.cos(a)])
zstart=samples[-1][2]
for z in [-14,-12,-10,-9.4,-7.4]:
 if z>zstart:samples.append([85.5,endY,z,1,0])
def loft(offset0,offset1,width=20):
 wires=[]
 for x,y,z,ny,nz in samples:
  pts=[V(x+dx,y+off*ny,z+off*nz) for dx,off in [(-width/2,offset0),(width/2,offset0),(width/2,offset1),(-width/2,offset1)]]
  wires.append(Part.makePolygon(pts+[pts[0]]))
 return Part.makeLoft(wires,True,True)
fan=loft(-.08,.08);add('StaticDevelopedFanout',fan,'rotor','0.16 single-layer RA70um proposed flex; parallel-X rulings;20mm width;R2.5 terminal bend; supplier formation/termination not approved')
# Forming saddle supports terminal bend from its inside, with .10mm unloaded gap.
bend_samples=samples[240:]
orig=samples;samples=bend_samples
saddle=loft(-.70,-.18).common(box(40,-34,-34,70,68,23.7))
samples=orig
# Saddle connects to the negative-Z mounting web under its straight clamped section.
railparts.append(saddle)
# Controlled channel clearance cut only in rotor/supports; no modification to active guide inner radius.
channel=loft(-.23,.23,20.4)
positive=O['RotorHalfPositiveY'].Shape
for i,s in enumerate(railparts):
 positive=positive.fuse(s)
 assert not positive.isNull(),('rail fuse',i)

# pilot holes for front retainer are outside board outline
for z in [-11,11]:positive=positive.cut(cyl(.38,1.51,100.49,25.65,z))
for name in ['RotorHalfPositiveY','RotorHalfNegativeY']:
 s=positive if name.endswith('PositiveY') else O[name].Shape.fuse(box(73.5,-30,-1.5,12,1.5,3)).fuse(box(84.5,-32.2,-1.5,1,3.7,3))
 O[name].Shape=s.cut(channel).removeSplitter()
# Retainer base touches tail only in clamped region; channel clearance deliberately omitted there.
# Restore clamp's contact base after channel subtraction.
O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.fuse(base).removeSplitter()
assert not O['RotorHalfPositiveY'].Shape.isNull(),'base restore'
for x in [74.4,96.6]:
 O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.cut(Part.makeCylinder(.7,12,V(x,27.8,-13),V(0,1,0)))
# Solder-tip access slot through LV shell; sealing/guard qualification remains open.
O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.cut(box(75.1,29.5,-10.1,20.8,10.5,2.8))
add('StaticFanoutChannelReserve',channel,'reserve','0.15mm each side +.2mm each lateral side; engineering placement/tolerance allocation')
# finite plug approach remains a screening box, not an exact plug or mating plane.
add('USBPlugApproach',box(104.17,24.58,-6,12,6.5,12),'screen','12x6.5x12 engineering screen; starts at allocation end, not sourced mating plane')
D.recompute();valid={n:{'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'closed':all(s.isClosed() for s in o.Shape.Solids),'volume_mm3':o.Shape.Volume} for n,o in O.items()}
(P/'validity.json').write_text(json.dumps(valid,indent=2)+'\n');(P/'groups.json').write_text(json.dumps(G,indent=2)+'\n')
(P/'fanout-path.json').write_text(json.dumps({'samples':samples,'terminal_bend_R_mm':rb,'thickness_mm':.16,'width_mm':20,'plane_Y_mm':endY,'source_X_mm':75,'source_parts':source,'reserves':reserves,'det_transform':1},indent=2)+'\n')
D.saveAs(str(P/'integrated.FCStd'))
print('INVALID',[(n,v) for n,v in valid.items() if not v['valid'] or v['solids']!=1 or not v['closed']],flush=True)
# First static diagnostic; final full poses/export separate.
keys=[n for n in O if G[n] not in ['reserve','screen'] and not G[n].startswith('pose')];rows=[]
for i,a in enumerate(keys):
 for bname in keys[i+1:]:
  aS,bS=O[a].Shape,O[bname].Shape
  if aS.BoundBox.intersect(bS.BoundBox):
   vol=aS.common(bS).Volume
   if vol>1e-6:rows.append({'a':a,'b':bname,'volume':vol})
(P/'static-overlaps.json').write_text(json.dumps(rows,indent=2)+'\n');print('OVERLAPS',json.dumps(rows),flush=True)
A.closeDocument(D.Name)
