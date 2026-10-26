from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;D=A.newDocument('CYL_R2');O={};G={};C={};notes={}
def box(x,y,z,a,b,c):return Part.makeBox(a,b,c,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def vert(r,l,x,y,z):return Part.makeCylinder(r,l,V(x,y,z))
def add(n,s,g,note=''):
 n=n.replace('-','m').replace('.','p')
 assert s.isValid() and s.isClosed() and len(s.Solids)==1,(n,len(s.Solids))
 o=D.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis').Basis=note;O[n]=o;G[n]=g;notes[n]=note;return s
old=A.openDocument(str(P.parent/'compact-interface-repair/interface-prototype.FCStd'));og=json.loads((P.parent/'compact-interface-repair/groups.json').read_text());original={o.Name:o.Shape.copy() for o in old.Objects if hasattr(o,'Shape')}
keepgroups={'collar_stationary','collar_rotor','collar_pin','collar_spring','collar_pose-90','collar_pose0','collar_pose90','stationary','rotating','stationary_pad','rotating_pad','rotating_stake','rotating_landing_reserve','stationary_landing_reserve'}
kept=[]
for n,s in original.items():
 if (og[n] in keepgroups or n in ['StationaryCoreWithSupports','LockAccess']) and not n.startswith('SourceWire'):
  add(n,s,og[n],'Frozen CIR geometry unchanged');kept.append(n)
# Source +4.5X/-2Z, retained source body dimensions unchanged.
shift=V(4.5,0,-2)
for n in ['IRM20_12_maxbody','Pin_L','Pin_N','Pin_LVplus','Pin_LVminus']:
 s=original[n].copy();s.translate(shift);add(n,s,'source','Frozen source shape translated(+4.5,0,-2); pins nominal, construction unqualified')
reserve=box(-111.5,-26,-22,81,52,44);add('InstallationReservation',reserve,'reserve','Inherited81x52x44; manufacturer 10mm around/5mm bottom +Mylar')
add('ReservationTolerance',box(-112,-26.5,-22.5,82,53,45),'reserve','Engineering0.5 each face')
# Source shell ends -115..-27; split horizontal through axis. Independent neck27mm.
outer=cyl(38.5,88,-115);bore=cyl(35.5,89,-115.5);shell=outer.cut(bore)
# End rings are open annuli; no hidden source insertion obstruction.
for x in [-115,-30]:shell=shell.fuse(cyl(35.5,3,x).cut(cyl(33.5,3,x)))
lo=shell.common(box(-116,-40,-40,90,80,40));hi=shell.common(box(-116,-40,0,90,80,40))
# Four connected lower carrier posts, no floating supports. Cross reservation explicitly.
postpoints=[(x,y) for x in [-99.5,-42.5] for y in [-20,20]]
for x,y in postpoints:
 post=vert(3,20,x,y,-35.1).common(outer);post=post.fuse(vert(4,.5,x,y,-23.25));post=post.cut(vert(.8,6,x,y,-21.1));lo=lo.fuse(post)
# Shell closure bosses outside full reservation Y +/-26.5. Vertical M2 holes.
closure=[(x,y) for x in [-110,-32] for y in [-32,32]]
for x,y in closure:
 bb=box(x-3,29 if y>0 else -38.5,-5,6,9.5,8)
 bb=bb.common(outer)
 lo=lo.fuse(bb.common(box(-116,-40,-40,90,80,40)));hi=hi.fuse(bb.common(box(-116,-40,0,90,80,40)))
 lo=lo.cut(vert(.8,5,x,y,-5));hi=hi.cut(vert(1.2,5,x,y,0))
 add('ClosureScrew_'+str(x)+'_'+str(y),vert(1,7,x,y,-4).fuse(vert(2,1.5,x,y,3)),'fastener','M2 engineering screw; bounded lower pilot engagement only')
 add('ClosureTool_'+str(x)+'_'+str(y),vert(2.5,36,x,y,4.5),'tool','Engineering driver approach; upper shell removed before source access')
# Carrier with ears and source-pin holes. No PCB circuit is added.
carrier=box(-101.5,-16,-15.1,61,32,1.6)
for x,y in postpoints:
 carrier=carrier.fuse(box(x-3.5,min(0,y),-15.1,7,abs(y),1.6)).fuse(vert(3.5,1.6,x,y,-15.1)).cut(vert(1.2,2,x,y,-15.2))
for x,y in [(-93.8,10.4),(-93.8,-10.4),(-48.8,-2.4),(-48.8,-10.4)]:carrier=carrier.cut(vert(1,3,x,y,-16))
# Four module seats and stops; .25 lateral/axial float, lid ribs .25 top clearance.
for x in [-96,-46]:
 for y in [-12,12]:carrier=carrier.fuse(box(x-1,y-1,-13.5,2,2,1))
for x in [-98,-44.3]:carrier=carrier.fuse(box(x,-14.1,-13.5,.3,28.2,5))
for y in [-14.4,14.1]:carrier=carrier.fuse(box(-97.7,y,-13.5,53.4,.3,5))
for x in [-94,-48]:hi=hi.fuse(box(x-1.5,-14,12.25,3,28,30).common(outer))
add('LowerShellPosts',lo,'newphysical','Proposed dielectric shell/posts; crossings of source reservation UNQUALIFIED')
add('UpperShellRetention',hi,'newphysical','Removable upper half; two ribs prevent cell lift with.25mm play; material/creep UNMET')
add('RetainedCarrier',carrier,'newphysical','Engineering insulating carrier with real ears/holes/seats; no new electrical PCB')
for i,(x,y) in enumerate(postpoints):add('CarrierScrew'+str(i),vert(1,6,x,y,-19.5).fuse(vert(2,1.5,x,y,-13.5)),'fastener','M2 threaded lower post; carrier clearancehole2.4')
film=box(-112,-26.5,-22.75,82,53,.25)
for x,y in postpoints:film=film.cut(vert(3.3,1,x,y,-23))
add('SupportedFilm',film,'newphysical','0.25 proposedMylar; supported on post collars. Holes outside modulefootprint; not approved insulationconstruction')
# Neck full 3D cone; minbore -.2 used separately.3mm nominal wall.
neck=Part.makeCone(38.5,24.5,27,V(-27,0,0),V(1,0,0)).cut(Part.makeCone(35.5,21.5,27,V(-27,0,0),V(1,0,0)))
bb=original['LockAccess'].BoundBox;neck=neck.cut(box(bb.XMin-.3,bb.YMin-.3,bb.ZMin-.3,bb.XLength+.6,bb.YLength+.6,bb.ZLength+.6))
add('Neck',neck,'newphysical','27mm transition, nominal3mm wall; attachment to shell/core still unbuilt')
# Exact tangent R12 double arcs; extended straight through source and core.
rr=12;th=math.acos(11/24);run=24*math.sin(th);join=-27+run
paths={}
for name,y in [('L',-8),('N',0),('PE',8)]:
 def p1(t):return V(-27+rr*math.sin(t),y,-29+rr*(1-math.cos(t)))
 def p2(t):return V(join-rr*math.sin(t),y,-16-rr*(1-math.cos(t)))
 edges=[Part.makeLine(V(-135,y,-29),p1(0)),Part.Arc(p1(0),p1(th/2),p1(th)).toShape(),Part.Arc(p2(th),p2(th/2),p2(0)).toShape(),Part.makeLine(p2(0),V(107,y,-16))];w=Part.Wire(edges)
 for radius,suffix,group in [(2.25,'','newphysical'),(2.75,'Corridor','corridor')]:
  add('Trunk'+name+suffix,w.makePipeShell([Part.Wire(Part.makeCircle(radius,V(-135,y,-29),V(1,0,0)))],True,False),group,'Continuous stationary source/core route; endpoints in unqualified terminal regions, not connected to invented connector')
 paths[name]={'length':w.Length,'bend_radius':12,'endpoints':[[-135,y,-29],[107,y,-16]]}
# Continuous primary branch allocation with named source-pin endpoints; L fuse remains explicit open interface.
def bez(name,points,r,g):
 cc=Part.BezierCurve();cc.setPoles([V(*p) for p in points]);ee=cc.toShape();ss=Part.Wire([ee]).makePipeShell([Part.Wire(Part.makeCircle(r,V(*points[0]),cc.tangent(0)[0]))],True,False);add(name,ss,g,'Engineering finite branch; no qualified terminal/insulation/fuse');paths[name]={'controls':points,'length':ee.Length,'min_radius':min(1/cc.curvature(i/1000) for i in range(1001) if cc.curvature(i/1000)>1e-9)}
bez('NeutralBranch',[[-107,0,-29],[-107,0,-24],[-103,-10.4,-20],[-93.8,-10.4,-17]],1.5,'newphysical')
bez('LineToFuse',[[-110,-8,-29],[-110,-8,-23],[-112,15,-20],[-112,20,-17]],1.5,'newphysical')
bez('FuseToLinePin',[[-108,20,-17],[-108,10.4,-20],[-99,10.4,-17],[-93.8,10.4,-17]],1.5,'newphysical')
# Actual film lead passages outside module footprint; spacing exception stays explicit.
for n in ['NeutralBranch','LineToFuse']:
 cc=Part.BezierCurve();cc.setPoles([V(*p) for p in paths[n]['controls']]);ww=Part.Wire([cc.toShape()]);hole=ww.makePipeShell([Part.Wire(Part.makeCircle(1.8,cc.value(0),cc.tangent(0)[0]))],True,False)
 O['SupportedFilm'].Shape=O['SupportedFilm'].Shape.cut(hole)
assert O['SupportedFilm'].Shape.isValid() and len(O['SupportedFilm'].Shape.Solids)==1
add('FuseMissingInterface',box(-113,17,-19,6,6,5),'unbuilt','NO selectedfuse or contactconstruction;4mm endpointgap is explicitly not connected')
add('FuseServiceTool',vert(4,50,-110,20,-14),'tool','Unselectedfuse serviceaccess only; upper halfremoved, no approvedterminal/fuse')
# Actual CIR secondary routes reconstructed with firstcontrolpoints at new sourcepins.
# Reuse original downstream geometry and actual J0 solder shapes, without running baseline scripts.
fragment=(P.parent/'compact-interface-repair/attachments.py').read_text().split('# Real source wires:')[1]
fragment=fragment[:fragment.index(' # Solid solder fillet')]+"\n wireinfo[pin]={'length':path.Length,'start':controls[0],'end':[ex,15.035,3]}\n"
fragment=fragment.replace(' engineering solid-copper-equivalentØ1, insulatedOD2; not ampacity qualified.','')
fragment=fragment.replace('[[-53.3,sy,-15],[-40,sy,-24]','[[-48.8,sy,-17],[-35.5,sy,-24]')
exec(compile(fragment,str(P/'secondary-fragment'),'exec'))
# No changed S12 pads or boardgeometry; secondary copper ends at existing solder.
(P/'paths.json').write_text(json.dumps({'primary_trunk':paths,'secondary':wireinfo},indent=2)+'\n')
(P/'groups.json').write_text(json.dumps(G,indent=2)+'\n');(P/'preserved-names.json').write_text(json.dumps(kept,indent=2)+'\n');(P/'notes.json').write_text(json.dumps(notes,indent=2)+'\n')
D.recompute();D.saveAs(str(P/'prototype.FCStd'));print('SAVED',len(O),'SHAPES',len(kept),'PRESERVED',flush=True)
