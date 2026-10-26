# Executed in build.py namespace: fixed routing attached solely to rotor.
b=.3/(2*math.pi);t0=.3;t1=.9;r0=30.5+b*t0;r1=33.;rb=2.5;endY=26.32
te=2*math.pi-math.acos((endY-rb)/(r1-rb));ms=[]
for i in range(301):
 t=t0+(te-t0)*i/300
 if t<t1:
  u=(t-t0)/(t1-t0);h=t1-t0;r=(2*u**3-3*u*u+1)*r0+(u**3-2*u*u+u)*h*b+(-2*u**3+3*u*u)*r1;dr=((6*u*u-6*u)*r0+(3*u*u-4*u+1)*h*b+(-6*u*u+6*u)*r1)/h
 else:r,dr=r1,0
 y,z=r*math.cos(t),r*math.sin(t);dy,dz=dr*math.cos(t)-r*math.sin(t),dr*math.sin(t)+r*math.cos(t);nn=math.hypot(dy,dz);u=(t-t0)/(te-t0);xc=34.2+29*(10*u**3-15*u**4+6*u**5);ms.append([xc,y,z,dz/nn,-dy/nn])
y0,z0=ms[-1][1:3];beta=te+math.pi/2-2*math.pi;cy=y0-rb*math.sin(beta);cz=z0+rb*math.cos(beta)
for i in range(1,49):
 a=beta+(math.pi/2-beta)*i/48;ms.append([63.2,cy+rb*math.sin(a),cz-rb*math.cos(a),math.sin(a),-math.cos(a)])
for z in [-15,-14,-13,-12,-11.5,-9.5]:
 if z>ms[-1][2]:ms.append([63.2,endY,z,1,0])
def mloft(lo,hi,width=20,offset=0):
 ww=[]
 for x,y,z,ny,nz in ms:
  pp=[V(x+dx+offset,y+o*ny,z+o*nz) for dx,o in [(-width/2,lo),(width/2,lo),(width/2,hi),(-width/2,hi)]];ww.append(Part.makePolygon(pp+[pp[0]]))
 return Part.makeLoft(ww,True,True)
fan=mloft(-.08,.08);channel=mloft(-.28,.28,20.4)
for n in ['RotorHalfPositiveY','RotorHalfNegativeY']:
 O[n].Shape=O[n].Shape.cut(channel)
 assert O[n].Shape.isValid() and len(O[n].Shape.Solids)==1,n
# Copper presents inner face to top PCB pads; stack deliberately same as fixed fanout.
cus=[]
for pin,off in [('1',-4.5),('2',4.5)]:
 s=mloft(-.055,.015,8,off);cus.append(s);add('MovingFanoutCopper'+pin,s,'rotating','RA70um proposed same singlelayer; exact J3 pad1positive/pad2return')
for s in cus:fan=fan.cut(s)
# Remove inner substrate at two static windows; copper inner faceY26.125.
for x in [54.7,63.7]:fan=fan.cut(box(x-.05,26.1,-11.55,8.1,.5,2.1))
for i,s in enumerate(fan.Solids):add('MovingFanoutDielectric'+str(i),s,'rotating','Static developed fanout; supplier bend/stack and formation unqualified')
for pin,x in [('1',6.5),('2',15.5)]:
 solder=rounded(8,2,.2,.035,.13);solder.translate(V(x,23.5,0));add('J3_Solder'+pin,tr(solder,'rotating'),'rotating','Named0.13mm solderpreform; process approval UNMET')
(P/'moving-path.json').write_text(json.dumps({'samples':ms,'status':'static routing candidate; supplier qualification UNMET','min_terminal_bend_radius':rb},indent=2)+'\n')
# Three integral edge-capture clips: PCB retained without new drilled holes.
for i,(x,z,sgn) in enumerate([(55,13,1),(79,13,1),(79,-13,-1)]):
 z0=13.25 if sgn==1 else -14.45
 leg=box(x,24.3,z0,2,3.0,1.2).fuse(box(x,24.3,12.2 if sgn==1 else -14.45,2,.8,2.25))
 lip=box(x,26.45,12.75 if sgn==1 else -14.45,2,.75,1.70)
 O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.fuse(leg).fuse(lip)
# Static FPC underside saddle and removable shoe; outboard M1 screws avoid copper.
base=box(51.2,25.1,-16,24,1.14,2)
for x in [51.2,74.7]:base=base.fuse(box(x,25.1,-22,.5,1.14,8))
shoe=box(51.2,26.4,-16,24,.7,2)
for x in [51.7,74.7]:
 base=base.cut(Part.makeCylinder(.38,2,V(x,24.8,-15),V(0,1,0)))
 shoe=shoe.cut(Part.makeCylinder(.55,1,V(x,26.3,-15),V(0,1,0)))
 screw=Part.makeCylinder(.5,1.6,V(x,25.5,-15),V(0,1,0)).fuse(Part.makeCylinder(.9,.3,V(x,27.1,-15),V(0,1,0)))
 add('MovingClampScrew'+str(x).replace('.','_'),screw,'rotating','M1proposed .74mm thread; load/materialgate')
O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.fuse(base)
add('MovingFanoutShoe',shoe,'rotating','0.16mm ribbon captured between25? geometrychecked; removable2M1; supplier preloadgate')

# Dedicated driver and axial solder-tool passages outside active ribbon.
s=O['RotorHalfPositiveY'].Shape
for x in [51.7,74.7]:s=s.cut(Part.makeCylinder(1.2,10,V(x,27.4,-15),V(0,1,0)))
s=s.cut(cyl(1.2,1.4,84.1,29,-10.5))
O['RotorHalfPositiveY'].Shape=s

# Removable axial end gate permits real PCB insertion along X onto existing rails.
gate=cyl(35,1,84.2).cut(cyl(24.3,1.02,84.19)).common(box(84.19,0,-35,1.02,35,70))
gate=gate.cut(box(78.47,25.85,-4.795,8.15,3.96,9.59)).cut(cyl(1.2,1.4,84.1,29,-10.5))
for z in [-17,17]:
 boss=box(81.2,28,z-1,3,2,2).common(cyl(35,3,81.2));boss=boss.cut(cyl(.38,3.2,81.1,29,z));O['RotorHalfPositiveY'].Shape=O['RotorHalfPositiveY'].Shape.fuse(boss)
 gate=gate.cut(cyl(.55,1.2,84.1,29,z));bolt=cyl(.5,3,82.2,29,z).fuse(cyl(.9,.3,85.2,29,z));add('SourceEndGateScrew'+str(z).replace('-','m'),bolt,'rotating','M1x3 envelope,2mm pilot engagement; strength/sourcing gate')
add('SourceEndGate',gate,'rotating','Removable gate; PCB slides axially before gate, .3 nominal axial play; no board holes')
