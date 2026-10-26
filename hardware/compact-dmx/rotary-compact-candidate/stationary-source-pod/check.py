"""Independent saved-solid/domain/access checks; allocations are not safety distances."""
import FreeCAD as A,Part,math,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[3];V=A.Vector
for path,h in json.loads((P/'protected-inputs.json').read_text()).items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h,path
d=A.openDocument(str(P/'stationary-source-pod.FCStd'));S={o.Name:o.Shape.copy() for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text())
valid={n:s.isValid() and s.isClosed() and len(s.Solids)==1 for n,s in S.items()};assert all(valid.values()),valid
physical=[n for n in S if G[n]['group'] in ['housing','film','module','carrier']];housing=[n for n in S if G[n]['group']=='housing'];rows=[]
def pair(a,b,kind):
 s,t=S[a],S[b];v=s.common(t).Volume if s.BoundBox.intersect(t.BoundBox) else 0
 rows.append({'a':a,'b':b,'kind':kind,'volume':v,'gap':s.distToShape(t)[0]});return v
for i,a in enumerate(physical):
 for b in physical[i+1:]:pair(a,b,'physical_allocation_pair')
external=[n for n in S if G[n]['group'] in ['trunk','trunk_tolerance','joint','primary_bay','primary_path','primary_bend','terminal_gap','secondary_gap','secondary_path','support']]
for n in external:
 pair(n,'WholeCarrierInsulationReservation','external_vs_insulation')
 pair(n,'ReservationToleranceEnvelope','external_vs_tolerance')
 for h in housing:pair(n,h,'external_vs_housing')
for n in ['L','N','PE']:
 for m in ['L','N','PE']:
  if n<m:pair('TrunkTolerance_'+n,'TrunkTolerance_'+m,'separate_trunk_envelopes')
# Do not suppress failures: preserve complete table and diagnostics before asserting.
fail=[r for r in rows if r['volume']>1e-7]
(P/'spacing-check.json').write_text(json.dumps({'rows':rows,'failures':fail},indent=2)+'\n')
print('SPACING',len(rows),'FAIL',fail,flush=True)
# Independently reproduce numeric source reservation, not a CAD-volume-only claim.
b=S['IRM20_12_maxbody'].BoundBox;r=S['WholeCarrierInsulationReservation'].BoundBox;c=S['Carrier61x32PlanningPlate'].BoundBox;pin=S['MaximumPinProjectionReservation'].BoundBox;film=S['FilmAllocation'].BoundBox
spacing={'box':[r.XLength,r.YLength,r.ZLength],'carrier_left':c.XMin-r.XMin,'carrier_right':r.XMax-c.XMax,'carrier_front':c.YMin-r.YMin,'carrier_back':r.YMax-c.YMax,'bottom_below_max_pin':pin.ZMin-r.ZMin,'above_maxbody':r.ZMax-b.ZMax,'film_top_below_reserved_bottom':r.ZMin-film.ZMax,'film_thickness':film.ZLength}
assert all(abs(spacing[k]-v)<1e-6 for k,v in [('carrier_left',10),('carrier_right',10),('carrier_front',10),('carrier_back',10),('bottom_below_max_pin',5),('above_maxbody',10)])
assert all(abs(a-b)<1e-6 for a,b in zip(spacing['box'],[81,52,44]))
# Frozen collar source identity and placement: exact maximum body is not a mating-plane assertion.
old=A.openDocument(str(P.parent/'collar-source-integrated/integrated.FCStd'))
for src,dst in [('USBPlugApproach','USBPlugScreenNeutral'),('SRC_J1_maximum_body_allocation','USBBodyComparisonNeutral')]:
 q=old.getObject(src).Shape;assert q.cut(S[dst]).Volume<1e-7 and S[dst].cut(q).Volume<1e-7
A.closeDocument(old.Name)
# All181 positions, actual saved source USB allocation plus explicitly engineering relief/cable screens.
motion=[];usbs=['USBBodyComparisonNeutral','USBPlugScreenNeutral','USBReliefScreenNeutral','USBCableScreenNeutral']
for angle in range(-90,91):
 for n in usbs:
  t=S[n].copy();t.rotate(V(0,0,0),V(1,0,0),angle)
  for h in housing:
   q=S[h];v=t.common(q).Volume if t.BoundBox.intersect(q.BoundBox) else 0
   motion.append({'angle':angle,'screen':n,'stationary':h,'intersection':v,'gap':t.distToShape(q)[0]})
assert not any(x['intersection']>1e-7 for x in motion)
# Full collar sweep including released axial projection cannot reach source pod. Conservative cylinder stronger than13positions.
newpod=['PodShell_allocation','PodLid_allocation','InputEndcapBlank','StationaryNeck_allocation']+external
sweep=[]
for n in newpod:
 q=S[n];v=q.common(S['CollarComparisonSweep']).Volume if q.BoundBox.intersect(S['CollarComparisonSweep'].BoundBox) else 0
 # LV route is intentionally INSIDE stationary core. Sweep cylinder is filled comparison; it is not rotor material.
 if G[n]['group'] in ['secondary_gap','secondary_path'] and q.BoundBox.XMax>26.8:
  maxr=max(math.hypot(y,z) for y in [q.BoundBox.YMin,q.BoundBox.YMax] for z in [q.BoundBox.ZMin,q.BoundBox.ZMax]);assert maxr<21.5
  sweep.append({'part':n,'filled_envelope_overlap':v,'basis':'Within fixed core bore; final radial handoff NOT integrated','max_radius':maxr});continue
 # Continuous trunk likewise stays inside fixed bore in collar X interval, checked throughactual tube wall above.
 if G[n]['group'] in ['trunk','trunk_tolerance']:
  section=q.common(Part.makeBox(77.37,100,100,V(26.8,-50,-50)));bb=section.BoundBox
  bore=Part.makeCylinder(21.5,77.37,V(26.8,0,0),V(1,0,0));assert section.cut(bore).Volume<1e-7,(n,'outside actual circular bore')
  maxr=math.hypot((bb.YMin+bb.YMax)/2,(bb.ZMin+bb.ZMax)/2)+max(bb.YLength,bb.ZLength)/2
  assert maxr<21.5,(n,maxr)
  sweep.append({'part':n,'filled_envelope_overlap':v,'basis':'Trunk fixed inside bore; actual wall checked','max_radius':maxr});continue
 assert v<1e-7,(n,v)
 sweep.append({'part':n,'volume':v})
# Lid-off vertical access is an explicit allocation, not an energized service instruction.
access=[]
for n in physical:
 if n=='PodLid_allocation':continue
 t=S['CarrierLiftAccess'];q=S[n];v=t.common(q).Volume if t.BoundBox.intersect(q.BoundBox) else 0;access.append({'part':n,'volume':v});assert v<1e-7
# Reopen every STEP and report actual valid solids. Nested reserve overlap is intentional and not structural material.
steps={}
for name in ['pod-shell-module-allocation.step','complete-allocation.step','reservations.step']:
 q=Part.Shape();q.read(str(P/name));steps[name]={'solids':len(q.Solids),'valid':all(x.isValid() and x.isClosed() for x in q.Solids)};assert steps[name]['valid']
mainenv=Part.makeCompound([S[n] for n in housing]+[S['CollarComparisonSweep']]).BoundBox
out={'status':'PASS allocation screens' if not fail else 'FAIL allocation spacing','native_valid':valid,'physical_pairs':sum(x['kind']=='physical_allocation_pair' for x in rows),'spacing_checks':len(rows),'spacing_failures':fail,'source_spacing':spacing,'motion_positions':181,'detents':list(range(-90,91,15)),'USB_motion_checks':len(motion),'USB_min_stationary_gap':min(x['gap'] for x in motion),'motion':motion,'sweep':sweep,'lid_removed_access':access,'STEP':steps,'whole_product_planning_bounds':[mainenv.XMin,mainenv.XMax,mainenv.YMin,mainenv.YMax,mainenv.ZMin,mainenv.ZMax],'whole_product_planning_dimensions':[mainenv.XLength,mainenv.YLength,mainenv.ZLength],'not_complete_construction':['Carrier/support retention and terminal transitions through reserved zone NOT designed','Final radial fixed-clamp interface NOT integrated','Variant connector/strain relief/power-plug/cable actual profiles unknown','No source12board consumed; no oldboard12V approval','Thermal/fire/mains/PE/creepage/clearance/film construction not released']}
(P/'checks.json').write_text(json.dumps(out,indent=2)+'\n');print('MOTION',len(motion),'ENVELOPE',out['whole_product_planning_dimensions'],'STEPS',steps,flush=True)
assert not fail,'See spacing-check.json; no failure excluded'
