# Explicit corner-cap fasteners, never through source PCB.
for side,x,direction in [('Front',21.2,1),('Rear',47.2,-1)]:
 for sign,z in [('m',-9),('p',9)]:
  axis=V(direction,0,0);shaft=Part.makeCylinder(.5,3,V(x,14.1,z),axis);head=Part.makeCylinder(.9,.3,V(x-.3*direction,14.1,z),axis)
  # M1 pilot through copied support only; 1mm nominal threaded engagement.
  core=O['StationaryCoreWithSupports'].Shape
  core=core.cut(Part.makeCylinder(.38,3.2,V(x-.1*direction,14.1,z),axis));O['StationaryCoreWithSupports'].Shape=core
  add('StationaryCapScrew'+side+sign,shaft.fuse(head),'stationary','M1 envelope,1mm intended thread engagement only; screw/material/strength supplier gate')
# Rear cap heads and axial driver clear the lower supporting web.
for z in [-9,9]:O['StationaryCoreWithSupports'].Shape=O['StationaryCoreWithSupports'].Shape.cut(cyl(1.05,1.2,47.19,14.1,z))
# Real source wires: engineering solid-copper-equivalentØ1, insulatedOD2; not ampacity qualified.
wireinfo={}
for pin,sy,ex,midz in [('1',-2.4,25.2,11),('2',-10.4,29.2,14)]:
 ystart=-5.0 if pin=='1' else -10.0;yend=6.0 if pin=='1' else 10.0;rr=(yend-ystart)/2;xx=ex+8;zc=13.5 if pin=='1' else 16.0;zend=zc-3;yc=(ystart+yend)/2
 controls=[[-53.3,sy,-15],[-40,sy,-24],[xx-8,ystart,zc],[xx,ystart,zc]]
 c=Part.BezierCurve();c.setPoles([V(*q) for q in controls]);e=c.toShape()
 arc=Part.Arc(V(xx,ystart,zc),V(xx+rr,yc,zc),V(xx,yend,zc)).toShape()
 yt=6. if pin=='1' else 10.
 q=[[xx,yend,zc],[ex+6,yend,zc],[ex+5,yt,zc],[ex+3,yt,zc]];d=Part.BezierCurve();d.setPoles([V(*v) for v in q]);edge=d.toShape()
 bend=Part.Arc(V(ex+3,15.035,zc),V(ex+3-3/math.sqrt(2),15.035,zend+3/math.sqrt(2)),V(ex,15.035,zend)).toShape()
 if pin in ['1','2']:
  bc=Part.BezierCurve()
  if pin=='1':
   edge=Part.makeLine(V(xx,yt,zc),V(ex+7,yt,zc));bc.setPoles([V(ex+7,yt,zc),V(ex+3,yt,zc),V(ex,15.035,zend+2),V(ex,15.035,zend)])
  else:bc.setPoles([V(ex+3,yt,zc),V(ex+1,yt,zc),V(ex,15.035,zend+2),V(ex,15.035,zend)])
  bend=bc.toShape()
 path=Part.Wire([e,arc,edge,bend,Part.makeLine(V(ex,15.035,zend),V(ex,15.035,3))])
 cu=path.makePipeShell([Part.Wire(Part.makeCircle(.5,V(*controls[0]),c.tangent(0)[0]))],True,False)
 uu=e.getParameterByLength(3);ie=[c.toShape(uu,1),arc,edge,bend]
 if zend>8.2:ie.append(Part.makeLine(V(ex,15.035,zend),V(ex,15.035,8.2)))
 ip=Part.Wire(ie);insulated=ip.makePipeShell([Part.Wire(Part.makeCircle(1,c.value(uu),c.tangent(uu)[0]))],True,False).cut(cu)
 add('SourceWireCopper'+pin,cu,'stationary_wire','Ø1 copper equivalent; actualsourcepin to correctJ0 land; solder attachment unqualified')
 for j,s in enumerate(insulated.Solids):add('SourceWireInsulation'+pin+'_'+str(j),s,'stationary_wire','OD2 engineeringwireenvelope; insulation/temperature/faultgate')
 # Solid solder fillet fills a finite connection to PCB pad; not just intersecting gapboxes.
 xlocal=3 if pin=='1' else 7;solder=rounded(2.5,3,.25,.035,.3);solder.translate(V(xlocal,3.5,0));solder=tr(solder,'stationary').cut(cu);
 for j,solid in enumerate(solder.Solids):add('J0_Solder'+pin+'_'+str(j),solid,'stationary','Named proposedfillet; electricalcontactandwetting require assembly validation')
 wireinfo[pin]={'controls':[controls,q],'length':path.Length,'radius_min':min([3,rr]+[1/cc.curvature(i/1000) for cc in [c,d,bc] for i in range(1001) if cc.curvature(i/1000)>1e-8]),'Uturn_radius':rr,'terminal_bend_radius':min(1/bc.curvature(i/1000) for i in range(1001) if bc.curvature(i/1000)>1e-8),'diameter_copper':1,'diameter_insulated':2,'samples':[[v.x,v.y,v.z] for v in path.discretize(Number=1001)]}
(P/'source-wire-paths.json').write_text(json.dumps(wireinfo,indent=2)+'\n')
