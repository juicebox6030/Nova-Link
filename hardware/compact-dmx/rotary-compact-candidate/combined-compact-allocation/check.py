from pathlib import Path
import FreeCAD as A,Part,json,hashlib,math
P=Path(__file__).resolve().parent;root=P.parents[3];V=A.Vector
protected={}
for f in ['protected-inputs.json','source12-frozen-inputs.json']:
 for p,h in json.loads((P/f).read_text()).items():
  assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p;protected[p]=h
d=A.openDocument(str(P/'allocation.FCStd'));S={o.Name:o.Shape for o in d.Objects if hasattr(o,'Shape')};G=json.loads((P/'groups.json').read_text())
valid={n:s.isValid() and s.isClosed() and len(s.Solids)==1 for n,s in S.items()};assert all(valid.values())
print('NATIVE VALID',len(valid),flush=True)
rows=[]
def check(a,b,kind):
 s,t=S[a],S[b];basis='actual solids'
 if b=='COL_Flex_0':
  # Deliberately stronger annular envelope. FrozenpathR25..30.5 +/-.08thickness;
  # expand another.12mm radial. No newshape gets a clearance exemption.
  bb=t.BoundBox;t=Part.makeCylinder(30.7,bb.XLength,V(bb.XMin,0,0),V(1,0,0)).cut(Part.makeCylinder(24.8,bb.XLength,V(bb.XMin,0,0),V(1,0,0)));basis='conservative annular activeFPC envelopeR24.8..30.7; frozen numericpath proof'
 sb,tb=s.BoundBox,t.BoundBox
 hit=sb.intersect(tb);v=s.common(t).Volume if hit else 0
 if hit:gap=s.distToShape(t)[0];gb='exact shape distance'
 else:
  gap=math.sqrt(sum(max(0,getattr(sb,k+'Min')-getattr(tb,k+'Max'),getattr(tb,k+'Min')-getattr(sb,k+'Max'))**2 for k in ['X','Y','Z']));gb='conservative AABB lower bound'
 row={'a':a,'b':b,'kind':kind,'volume':v,'gap':gap,'geometry_basis':basis,'gap_basis':gb};rows.append(row);return row
housing=[n for n in S if G[n]=='housing'];newphys=[n for n in S if G[n] in ['housing','module','film','carrier','pin','trunk','joint','branch','secondary_wire']]
for i,a in enumerate(newphys):
 for b in newphys[i+1:]:check(a,b,'newphysical')
print('NEW PAIRS',len(rows),flush=True)
# No blanketcollar exclusion: everynewphysical shape againstactualall frozenneutralparts.
collar=[n for n in S if G[n] in ['collar_stationary','collar_rotor','collar_pin','collar_spring','collar_pose0']]
for a in newphys:
 for b in collar:check(a,b,'new_vs_actual_collar')
print('COLLAR PAIRS',len(rows),flush=True)
for a in [n for n in S if G[n] in ['trunk','trunk_tolerance','joint','housing','support']]:check(a,'ReservationToleranceEnvelope','source_external_distance')
# Explicitsourcelead intersections are recorded, not acceptedas insulationclearance.
for a in [n for n in S if G[n] in ['branch','secondary_wire']]:check(a,'ReservationToleranceEnvelope','electrical_interface_crossing_UNQUALIFIED')
for h in housing:check('LockAccess',h,'lock_access')
for n in ['S12_StationaryPCBConstraint','S12_StationaryTopUpperBound','S12_StationaryClampConstraint','S12_StationarySolderTool']:
 for h in housing+['ReservationToleranceEnvelope']:check(n,h,'S12_stationary_dimension_screen')
# Source distances retained independently fromactual bounds.
r=S['WholeCarrierInsulationReservation'].BoundBox;b=S['IRM20_12_maxbody'].BoundBox;c=S['Carrier61x32PlanningPlate'].BoundBox;pin=S['MaximumPinProjectionReservation'].BoundBox
spacing={'carrier_left':c.XMin-r.XMin,'carrier_right':r.XMax-c.XMax,'carrier_front':c.YMin-r.YMin,'carrier_back':r.YMax-c.YMax,'below_max_pin':pin.ZMin-r.ZMin,'above_max_body':r.ZMax-b.ZMax}
assert all(abs(spacing[k]-v)<1e-7 for k,v in [('carrier_left',10),('carrier_right',10),('carrier_front',10),('carrier_back',10),('below_max_pin',5),('above_max_body',10)])
# Frozenpartidentity: geometry descriptors and transformedbbox, not justsame labels.
old=A.openDocument(str(P.parent/'collar-source-integrated/integrated.FCStd'));identity=[]
for o in old.Objects:
 n=o.Name
 if n=='StationaryCoreEnvelope' or 'COL_'+n not in S:continue
 q=o.Shape.copy();q.translate(V(-22.8,0,0));s=S['COL_'+n];a=q.BoundBox;b=s.BoundBox
 error=max(abs(getattr(a,k)-getattr(b,k)) for k in ['XMin','XMax','YMin','YMax','ZMin','ZMax'])
 ok=error<1e-7 and abs(q.Volume-s.Volume)<1e-6 and abs(q.Area-s.Area)<1e-5 and len(q.Faces)==len(s.Faces)
 assert ok,n;identity.append(n)
A.closeDocument(old.Name)
print('IDENTITY',len(identity),flush=True)
motion=[];offset=[]
for ang in range(-90,91):
 for n in ['COL_SRC_J1_maximum_body_allocation','COL_USBPlugApproach','USBRelief','USBCable']:
  t=S[n].copy();t.rotate(V(0,0,0),V(1,0,0),ang)
  for h in housing:
   q=S[h];v=t.common(q).Volume if t.BoundBox.intersect(q.BoundBox) else 0
   motion.append({'angle':ang,'screen':n,'housing':h,'volume':v,'gap':t.distToShape(q)[0]})
  for h in ['PodShell_allocation','PodLid_allocation','InputEndcapBlank']:
   q=S[h].copy();q.translate(V(128,-86,0));v=t.common(q).Volume if t.BoundBox.intersect(q.BoundBox) else 0
   offset.append({'angle':ang,'screen':n,'housing':h,'volume':v,'gap':t.distToShape(q)[0]})
# Terminalgraph is explicit, including internalfusegate, unimplemented lands and fixedtailcontacts.
contacts=[]
for a,b in [('L_TrunkToFuse','Trunk_L'),('L_TrunkToFuse','PrimaryFuseBranchBay'),('L_FuseToCarrier','PrimaryFuseBranchBay'),('L_FuseToCarrier','Pin_L'),('N_TrunkToCarrier','Trunk_N'),('N_TrunkToCarrier','Pin_N')]:contacts.append(check(a,b,'wire_contact'))
for n in ['minus','plus']:
 for a,b in [('Pin_LV'+n,'LV_'+n+'_underCarrier'),('LV_'+n+'_underCarrier','LV_'+n+'_toCore'),('LV_'+n+'_toCore','LV_'+n+'_toClamp'),('LV_'+n+'_toClamp','COL_FixedStaticTail')]:contacts.append(check(a,b,'wire_contact'))
for n in ['L','N','PE']:
 for end in ['Input','Output']:contacts.append(check('Trunk_'+n,end+'Joint_'+n,'wire_contact'))
print('MOTION',len(motion),flush=True)
steps={}
for f in ['inline-assembly.step','allocation-detail.step']:
 s=Part.Shape();s.read(str(P/f));steps[f]={'solids':len(s.Solids),'valid':all(q.isValid() and q.isClosed() for q in s.Solids)};assert steps[f]['valid']
env=Part.makeCompound([S[n] for n in housing]+[S[n] for n in collar]).BoundBox
# S12 outerclampcorner is a real allocation, notuniformcomponentheight guess.
q=S['S12_ExternalClampConstraint'].BoundBox;rad=max(math.hypot(y,z) for y in [q.YMin,q.YMax] for z in [q.ZMin,q.ZMax])
positives=[r for r in rows if r['volume']>1e-7 and r['kind']!='wire_contact']
failmotion=[r for r in motion if r['volume']>1e-7]
out={'status':'BOUNDED ALLOCATION; residual interfaces and S12 collar fit NOT ACCEPTED','protected_hashes':len(protected),'valid_solids':len(valid),'source_spacing':spacing,'identity_shapes':len(identity),'pair_checks':len(rows),'positive_intersections':positives,'rows':rows,'wire_contacts':contacts,'disconnected_wire_contacts':[r for r in contacts if r['gap']>1e-6],'USB_positions':181,'USB_checks':len(motion),'USB_failures':failmotion,'USB_min_gap':min(r['gap'] for r in motion),'offset_USB_checks':len(offset),'offset_USB_failures':[r for r in offset if r['volume']>1e-7],'offset_USB_min_gap':min(r['gap'] for r in offset),'actual_comparison_envelope':[env.XLength,env.YLength,env.ZLength],'STEP':steps,'S12_external_clamp_outer_radius':rad,'S12_bare_clamp_min_OD':2*rad,'S12_with_1mm_wall_and_0p25_assembly_allocation_OD':2*(rad+1.25),'S12_axial_growth_mm':5,'S12_inline_length_if_endcap_shifted_5mm':275,'source12_actual_integration':False}
(P/'checks.json').write_text(json.dumps(out,indent=2)+'\n');(P/'motion.json').write_text(json.dumps({'inline':motion,'offset':offset},indent=2)+'\n')
print('CHECKS',len(rows),'POSITIVE',len(positives),'WIREGAPS',len(out['disconnected_wire_contacts']),'USBFAIL',len(failmotion),'S12R',rad,'ENVELOPE',out['actual_comparison_envelope'],flush=True)
for r in positives:print('INTERSECTION',r,flush=True)
for r in out['disconnected_wire_contacts']:print('DISCONNECTED',r,flush=True)
