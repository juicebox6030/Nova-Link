# Explicit copper in the copied static tail envelopes; active laminate path untouched.
for label,r,a0,a1,group in [('Fixed',25,-.3,0,'stationary'),('Moving',30.5,0,.3,'rotating')]:
 laminate=O['COL_'+label+'StaticTail'].Shape
 for pin,x in [('1',25.7),('2',34.7)]:
  pp=[]
  for off,seq in [(.015,range(65)),(-.055,range(64,-1,-1))]:
   for i in seq:
    a=a0+(a1-a0)*i/64;rr=r+.3/(2*math.pi)*a;den=math.hypot(rr,.3/(2*math.pi));ny=(rr*math.cos(a)+.3/(2*math.pi)*math.sin(a))/den;nz=(rr*math.sin(a)-.3/(2*math.pi)*math.cos(a))/den;pp.append(V(x,rr*math.cos(a)+off*ny,rr*math.sin(a)+off*nz))
  copper=Part.Face(Part.makePolygon(pp+[pp[0]])).extrude(V(8,0,0));add(label+'TailCopper'+pin,copper,group,'Explicit static70umRA lane; same active-circuit lane order, no vias; qualificationopen');laminate=laminate.cut(copper)
 O['COL_'+label+'StaticTail'].Shape=laminate
