"""One shorter allocation. Copy frozen solids; never execute upstream generators."""
from pathlib import Path
import FreeCAD as A,Part,json,math
P=Path(__file__).resolve().parent;V=A.Vector;d=A.newDocument('CombinedCompactAllocation');O={};G={}
def box(x,y,z,a,b,c):return Part.makeBox(a,b,c,V(x,y,z))
def cyl(r,l,x,y=0,z=0):return Part.makeCylinder(r,l,V(x,y,z),V(1,0,0))
def add(n,s,g,note=''):
 assert s.isValid() and s.isClosed() and len(s.Solids)==1,n
 o=d.addObject('PartDesign::Feature',n);o.Shape=s;o.addProperty('App::PropertyString','Basis').Basis=note;O[n]=o;G[n]=g
old=A.openDocument(str(P.parent/'stationary-source-pod/stationary-source-pod.FCStd'));og=json.loads((P.parent/'stationary-source-pod/groups.json').read_text())
keep=['PodShell_allocation','PodLid_allocation','InputEndcapBlank','StationaryNeck_allocation','WholeCarrierInsulationReservation','ReservationToleranceEnvelope','FilmAllocation','IRM20_12_maxbody','MaximumPinProjectionReservation','Carrier61x32PlanningPlate','PrimaryFuseBranchBay','CarrierLiftAccess']
keep += [n for n in og if n.startswith('SupportZone_') or n.startswith('InputJoint_')]
for n in keep:add(n,old.getObject(n).Shape.copy(),og[n]['group'],og[n]['note'])
# Keep source-clearances, generic connectors and original trunk bend geometry.
add('StationaryCoreTube',cyl(24,82,0).cut(cyl(21.5,82,0)),'housing','Shortened engineering allocation142 ->82; radial LV exit added below. Not mains approval.')
s=old.getObject('OutputEndcapBlank').Shape.copy();s.translate(V(-60,0,0));add('OutputEndcapBlank',s,'housing','UnqualifiedØ48x24 blank retained in full, X82..106')
for n in ['L','N','PE']:
 for prefix in ['Trunk_','TrunkTolerance_']:
  s=old.getObject(prefix+n).Shape.common(box(-170,-100,-100,260,200,200));add(prefix+n,s,'trunk' if prefix=='Trunk_' else 'trunk_tolerance','Existing continuous R12 path truncated atX90; no wire material/ampacity claim')
 s=old.getObject('OutputJoint_'+n).Shape.copy();s.translate(V(-60,0,0));add('OutputJoint_'+n,s,'joint','Unqualified6x5x5 terminal allocationX90..96; connected to trunk')
A.closeDocument(old.Name)
old=A.openDocument(str(P.parent/'collar-source-integrated/integrated.FCStd'));cg=json.loads((P.parent/'collar-source-integrated/groups.json').read_text())
for n,g in cg.items():
 if n=='StationaryCoreEnvelope':continue
 s=old.getObject(n).Shape.copy();s.translate(V(-22.8,0,0));add('COL_'+n,s,'collar_'+g,'Exact frozen shape translatedX-22.8; old5V source is spatial comparison ONLY, no12V fit or electrical acceptance')
A.closeDocument(old.Name)
add('USBRelief',box(93.37,24.58,-6,18,6.5,12),'usb_screen','Engineering18mm relief; not universal cable')
add('USBCable',cyl(3,80,111.37,27.83,0),'usb_screen','EngineeringØ6x80 axial cable; no supplier bend qualification')
# Smooth continuous route reservations using cubic Bezier with explicit tangent handles.
# These are finite insulated-wire allocations, not released mains construction.
paths={}
def bez(n,points,r,g,note):
 c=Part.BezierCurve();c.setPoles([V(*p) for p in points]);e=c.toShape();w=Part.Wire([e]);s=w.makePipeShell([Part.Wire(Part.makeCircle(r,V(*points[0]),c.tangent(0)[0]))],True,False)
 add(n,s,g,note);curv=[]
 for i in range(1001):
  t=i/1000
  try:k=c.curvature(t)
  except:k=0
  if k>1e-10:curv.append(1/k)
 paths[n]={'points':points,'length':e.Length,'radius':r,'sampled_min_bend_radius':min(curv) if curv else None,'note':note}
# Complete input branch chains: L through a finite fuse allocation, N direct.
# The source drawing does not authorize the conductor/carrier crossing of reserved space;
# retain it as a specific construction gate, NEVER report those crossings as distancePASS.
bez('L_TrunkToFuse',[[-126,32,-25],[-126,32,-19],[-126,32,-16],[-126,32,-10]],1.5,'branch','Connected trunk -> fuse bay bottom; selected fuse/holder and terminal truth UNMET')
bez('L_FuseToCarrier',[[-124,29,-7],[-124,7,-18],[-112,10.4,-18],[-98.3,10.4,-14.7]],1.5,'branch','Finite continuous source-pin approach; crosses insulation reservation as electrical connection, approval UNMET')
bez('N_TrunkToCarrier',[[-132,38,-25],[-132,38,-8],[-115,-10.4,-14.7],[-98.3,-10.4,-14.7]],1.5,'branch','Finite continuous source-pin approach; N remains continuous on bypass trunk; approval UNMET')
# Source pins themselves, nominalpin1.0 diameter; maxprojection envelope remains separate.
for n,x,y in [('N',-98.3,-10.4),('L',-98.3,10.4),('LVminus',-53.3,-10.4),('LVplus',-53.3,-2.4)]:
 s=Part.makeCylinder(.5,4.5,V(x,y,-15),V(0,0,1));add('Pin_'+n,s,'pin','Nominal diameter1mm, max4.5 projection. Pin numbering follows primary bottom-view drawing; carrier pads/holes NOT designed.')
# Static isolated LV route, source to fixedtail, no wiretorsion. Keep individual finitepaths.
for n,y,z in [('minus',-10.4,-5.8),('plus',-2.4,-3.0)]:
 bez('LV_'+n+'_underCarrier',[[-53.3,y,-14.2],[-45,y,-14.2],[-38,y,-14.2],[-30,y,-14.2]],1,'secondary_wire','Under-carrier solder approach; terminal insulation and carrier construction UNMET')
 bez('LV_'+n+'_toCore',[[-30,y,-14.2],[-12,y,-14.2],[-9,10,z],[4,10,z]],1,'secondary_wire','Routed isolatedLV only; finite bend radius reported, supplierwire unselected')
 bez('LV_'+n+'_toClamp',[[4,10,z],[15,10,z],[22.2,15,z],[22.2,24,z]],1,'secondary_wire','Finite static handoff to fixedtail; solder lands/strain relief not designed; no claim wire/copper termination')
# Explicit local radial passage for finiteLV envelopes, no hidden wall interference.
# Proposed4x7mm slot; source-approved insulating bushing/retention not provided.
passage=box(20.2,18,-7.8,4,9,6.8)
O['StationaryCoreTube'].Shape=O['StationaryCoreTube'].Shape.cut(passage)
add('LVExitPassageReserve',passage,'interface','Core slot4axial x6.8tangential; bushing/retention/safety unfinished. Must check actual collarparts.')
# Finger/tool access at released knob; this is engineering access, not universal hand fit.
add('LockAccess',box(-4,25,-5,12,12,10),'access','8mm front approach to releasedknobX4; finger/tool envelope, no ergonomic qualification')
# S12 dimensions ONLY, not integrated electricalgeometry. Bothboards explicitlycounted.
add('S12_RotatingPCBConstraint',box(52.2,25.1,-13,32,1,26),'s12_constraint','32x26x1, oldpropertransform. DoesNOTreplaceactual5Vcomparisonparts.')
add('S12_RotatingTopUpperBound',box(52.2,26.1,-13,32,3.46,26),'s12_constraint','Uniformupperbound, not allparts are3.46high. Actualcomponent-specificfit NOT claimed.')
add('S12_ExternalClampConstraint',box(52.95,26.1,-18,20.5,2,5),'s12_constraint','ExactS12 provisionalclampreserve. OuterR33.3708 exceedsØ66 beforewall/tolerance.')
add('S12_USBBodyConstraint',box(78.72,26.1,-4.545,7.65,3.46,9.09),'s12_constraint','Bodyends86.37, NOT matingplane; source12originlocal32,13.')
add('S12_StationaryPCBConstraint',box(-90,26.75,0,24,16,1),'s12_constraint','Secondaryonly24x16 board allocation outside sourcebox; support/route unimplemented.')
add('S12_StationaryTopUpperBound',box(-90,26.75,1,24,16,2.5),'s12_constraint','2.5 maxcomponent height; .25nominal transverse clearance tosource tolerancebox.')
add('S12_StationaryClampConstraint',box(-88.25,42.75,1,20.5,5,2),'s12_constraint','Externalclamp reserve .25 frompodinnerwall; no retention/assembly acceptance.')
add('S12_StationarySolderTool',box(-88.25,40.75,3.5,20.5,7,20),'s12_constraint','Engineering20mm aboveboard solderapproach, lidremoved; exacttool unspecified.')
d.recompute();d.saveAs(str(P/'allocation.FCStd'))
# Keep alternative flex poses/reserves out of assemblySTEP; preserve all in native file.
physical=[o for n,o in O.items() if G[n] in ['housing','film','module','carrier','pin','branch','secondary_wire','trunk','joint'] or G[n] in ['collar_stationary','collar_rotor','collar_pin','collar_spring','collar_pose0']]
Part.export(physical,str(P/'inline-assembly.step'))
Part.export([o for n,o in O.items() if G[n] in ['housing','module','film','carrier','branch','secondary_wire','trunk','joint']],str(P/'allocation-detail.step'))
(P/'groups.json').write_text(json.dumps(G,indent=2)+'\n');(P/'wire-paths.json').write_text(json.dumps(paths,indent=2)+'\n');print('SAVED',len(O),flush=True)
