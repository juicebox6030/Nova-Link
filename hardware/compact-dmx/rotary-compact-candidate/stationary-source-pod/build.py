"""One stationary allocation. No released carrier, mains joint, connector or12V rotor PCB."""
from pathlib import Path
import FreeCAD as A,Part,math,json
P=Path(__file__).resolve().parent;V=A.Vector;d=A.newDocument('StationarySourcePod');O={};M={}
def box(x,y,z,a,b,c):return Part.makeBox(a,b,c,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def add(n,s,group,note):
 assert s.isValid() and s.Volume>0,(n,'invalid')
 o=d.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Scope').Scope=group;o.addProperty('App::PropertyString','Basis').Basis=note;O[o.Name]=o;M[o.Name]={'group':group,'note':note};return s
# Outer pod128x82x62; nominal3mm walls. No holes/fasteners implied by blank walls.
outer=box(-140,-31,-33,128,82,59)
inner=box(-137,-28,-30,122,76,60)
base=outer.cut(inner).cut(cyl(21.5,5,-141,32,-15)).cut(box(-16,-14.5,-28.5,5,29,50))
add('PodShell_allocation',base,'housing','Engineering3mm nominal shell; split/fasteners/flame/strength/ventilation not designed')
add('PodLid_allocation',box(-140,-31,26,128,82,3),'housing','Closed thermal allocation, not demonstrated sealed operation; attachment unresolved')
add('InputEndcapBlank',cyl(24,24,-164,32,-15).cut(cyl(21.5,24,-164,32,-15)),'housing','Offset axisY32 Z-15; Ø48x24 planning blank only, none of3 connector variants approved')
add('OutputEndcapBlank',cyl(24,24,142).cut(cyl(21.5,24,142)),'housing','CoaxialØ48x24 planning blank; actual keying, latch, connector/plug/strain-relief geometry remains open')
def rectwire(x,y0,y1,z0,z1):return Part.makePolygon([V(x,y0,z0),V(x,y1,z0),V(x,y1,z1),V(x,y0,z1),V(x,y0,z0)])
wo=Part.Wire(Part.makeCircle(24,V(0,0,0),V(1,0,0)));wi=Part.Wire(Part.makeCircle(21.5,V(0,0,0),V(1,0,0)))
neck=Part.makeLoft([rectwire(-12,-17,17,-31,24),wo],True).cut(Part.makeLoft([rectwire(-12,-14.5,14.5,-28.5,21.5),wi],True))
add('StationaryNeck_allocation',neck,'housing','One loft allocation; continuous terminal passage, shell joins not a released molding')
add('StationaryCoreTube',cyl(24,142,0).cut(cyl(21.5,142,0)),'housing','Module removed; only fixed trunk/LV route. RetainsØ48x142 comparison datum; not restored blocked module architecture')
# Exact planning dimensions from frozen construction screen, maximum module shape.
add('WholeCarrierInsulationReservation',box(-116,-26,-20,81,52,44),'insulation','81x52x44 planning reservation:10mm about61x32 carrier;5mm below maximum pin; conservative10mm above maxbody')
add('ReservationToleranceEnvelope',box(-116.5,-26.5,-20.5,82,53,45),'tolerance','Engineering+/-0.5mm assembly/enclosure allocation beyond planning reservation; not vendor waiver')
add('FilmAllocation',box(-116.5,-26.5,-20.75,82,53,.25),'film','Mylar required by source;0.25mm thickness and footprint proposed only; grade/flame/retention approval OPEN')
add('IRM20_12_maxbody',box(-101.95,-13.85,-10.5,52.9,27.7,24.5),'module','IRM20 family2025-11-21 maximum body from±.5;12V selection by parent, not powered')
add('MaximumPinProjectionReservation',box(-101.95,-13.85,-15,52.9,27.7,4.5),'pin_reserve','Worst4.5mm projection bounding prism, NOT actual pins or solder construction')
add('Carrier61x32PlanningPlate',box(-106,-16,-13.1,61,32,1.6),'carrier','Old61x32 carrier planning datum only; no pads/traces/holes released; module1mm above proposed top-11.5')
for x in [-123,-33]:
 for y in [-23,19]:add('SupportZone_'+str(x)+'_'+str(y),box(x,y,-25,6,4,3),'support','Outside insulation/tolerance/film; support and carrier bridging/retention not designed, no clearance waiver')
# Finite smooth trunk reservations. Engineering Ø4.5 insulated-wire envelope and R12 centreline, not wire approval.
def line(a,b):return Part.makeLine(V(*a),V(*b))
def arc(a,m,b):return Part.Arc(V(*a),V(*m),V(*b)).toShape()
def tube(edges,r):
 w=Part.Wire(edges);start=edges[0].Vertexes[0].Point;t=edges[0].tangentAt(edges[0].FirstParameter);return w.makePipeShell([Part.Wire(Part.makeCircle(r,start,t))],True,False)
paths={};q=math.sqrt(.5);theta=math.acos(1-9/24);dx=24*math.sin(theta)
for name,y,target,end in [('L',32,-8,-44),('N',38,0,-34),('PE',44,8,-24)]:
 x=end-24
 a=(-145,y,-25);b=(x,y,-25);c=(x+12,y-12,-25);e=(x+12,target+12,-25);f=(end,target,-25)
 ed=[line(a,b),arc(b,(x+12*q,y-12+12*q,-25),c)]
 if V(*c).distanceToPoint(V(*e))>1e-8:ed.append(line(c,e))
 ed.append(arc(e,(end-12*q,target+12-12*q,-25),f))
 if end< -24:ed.append(line(f,(-24,target,-25)))
 # Matched S curves, radius12, dz9; no tight U bend or fictitious zero-radius corner.
 a=(-24,target,-25);mid=(-24+12*math.sin(theta),target,-25+12*(1-math.cos(theta)));last=(-24+dx,target,-16)
 ed += [arc(a,(-24+12*math.sin(theta/2),target,-25+12*(1-math.cos(theta/2))),mid),arc(mid,(last[0]-12*math.sin(theta/2),target,-16-12*(1-math.cos(theta/2))),last),line(last,(150,target,-16))]
 shape=tube(ed,2.25);add('Trunk_'+name,shape,'trunk','Stationary continuous insulated envelopeØ4.5,R12; ampacity/PE construction, stripping/terminals and strain relief unqualified')
 add('TrunkTolerance_'+name,tube(ed,2.75),'trunk_tolerance','Engineering+0.5 radial installation allowance beyondØ4.5 wire envelope; no supplier limit')
 paths[name]={'length_mm':sum(z.Length for z in ed),'radius_mm':12,'wire_envelope_diameter':4.5,'start':[-145,y,-25],'end':[150,target,-16]}
 add('InputJoint_'+name,box(-151,y-2.5,-27.5,6,5,5),'joint','Finite unselected input terminal/joint reserve; wire meets face atX-145; no pin-map/connector construction claimed')
 add('OutputJoint_'+name,box(150,target-2.5,-18.5,6,5,5),'joint','Finite unselected output joint reserve; not a released mains termination')
# All trunk joint/branch allocations stay outside the whole-carrier insulation volume.
add('PrimaryFuseBranchBay',box(-129,29,-10,10,16,20),'primary_bay','Unselected local primary fuse/holder and two-pole branch interface reserve; no rating or coordinated fuse invented')
add('PrimaryBranchEntryL',box(-129,29,-25,5,6,15),'primary_path','Finite15mm branch/joint approach from L trunk to fuse bay; branching hardware and bend/strain relief require design')
add('PrimaryBranchEntryN',box(-122,35,-25,5,6,15),'primary_path','Finite15mm N local branch approach; trunk remains stationary and uninterrupted PE')
# Two R8 elbow-space allocations are separate from the module reservation, not actual copper traces.
add('PrimaryBendBayL',box(-136,-20,-18,19,48,32),'primary_bend','Bounds reserve R8 branch bends withØ3 engineering wire space and solder/tool approach; no released wire route, finite terminal gap explicitly recorded')
add('PrimaryTerminalInterface',box(-118,-18,-16,1.5,36,8),'terminal_gap','Ends atX-116.5 tolerance boundary.10.5mm to carrier edgeX-106 remains unimplemented/approval-gated; do not bridge insulation by assumption')
add('SecondaryTerminalInterface',box(-34.5,-21,-5,4,8,10),'secondary_gap','Starts at outer tolerance face;10.5mm from carrier edgeX-45 to-34.5 remains unimplemented carrier/terminal construction')
# Static secondary leadout is a corridor only; not permission to apply12V to old AXIAL-R1.
add('SecondaryLeadoutBendBay',box(-30.5,-22,-8,15,24,20),'secondary_path','R8 static isolated lead bend/access allocation; no selected insulation or actual solder joint')
add('SecondaryCoreRouteReserve',box(-14.5,8,2,53.5,6,6),'secondary_path','Only isolatedLV inside fixed core; endsX39, proposed final6mm plus radial interface to fixed clamp not designed')
add('SecondaryClampInterfaceGap',box(39,8,2,6,6,6),'secondary_gap','Finite unimplemented fixed-clamp handoff; actual clamp nearY24,Z-7 requires separate radial exit/retention design; not connected wire')
add('CarrierLiftAccess',box(-117,-27,29,83,54,45),'access','Lid removed: vertical service/lift volume; support attachments and hot-mains service not authorized')
# Comparison only: do not claim old5V board accepts12V or newSol board fits.
add('CollarComparisonSweep',cyl(33,77.37,26.8),'comparison','ConservativeØ66 x26.8..104.17 locked/released comparison; preserves13detents/±90, no new mechanism or circuit acceptance')
old=A.openDocument(str(P.parent/'collar-source-integrated/integrated.FCStd'))
for n,new in [('USBPlugApproach','USBPlugScreenNeutral'),('SRC_J1_maximum_body_allocation','USBBodyComparisonNeutral')]:add(new,old.getObject(n).Shape.copy(),'usb_comparison','Frozen actual source allocation; bodyX104.17 is not exact mating plane; no12V board fit claim')
A.closeDocument(old.Name)
add('USBReliefScreenNeutral',box(116.17,24.58,-6,18,6.5,12),'usb_screen','Engineering finite18mm overmold/relief reservation; not a universal cable')
add('USBCableScreenNeutral',cyl(3,80,134.17,27.83,0),'usb_screen','EngineeringØ6 cable,80mm axial approach, no supplier min bend or cable qualification')
d.recompute();d.saveAs(str(P/'stationary-source-pod.FCStd'))
physical=[o for n,o in O.items() if M[n]['group'] in ['housing','film','module','carrier']]
Part.export(physical,str(P/'pod-shell-module-allocation.step'))
Part.export([o for n,o in O.items() if M[n]['group'] not in ['access']],str(P/'complete-allocation.step'))
Part.export([o for n,o in O.items() if M[n]['group'] in ['insulation','tolerance','trunk','trunk_tolerance','primary_bay','primary_path','primary_bend','terminal_gap','secondary_gap','secondary_path','support','joint']],str(P/'reservations.step'))
(P/'groups.json').write_text(json.dumps(M,indent=2)+'\n');(P/'wire-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
print('OBJECTS',len(O),'PATHS',paths)
