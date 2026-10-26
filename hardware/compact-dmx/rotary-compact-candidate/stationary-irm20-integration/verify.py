import traceback
try:
 """Independent saved-CAD/source-tolerance/connection checks; no build import.
 PASS means enumerated mechanical screens only; electrical/insulation/process gates remain UNMET.
 """
 from pathlib import Path
 from itertools import product
 import FreeCAD as A,Part,json,math,hashlib
 P=Path(__file__).resolve().parent;root=P.parents[3];V=A.Vector;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 m=json.loads((P/'protected-inputs.json').read_text());assert all(sha(root/n)==h for n,h in m.items())
 sources=json.loads((P/'sources.json').read_text());assert all(sha(P/s['path'])==s['sha256'] for s in sources)
 d=A.openDocument(str(P/'stationary-integration.FCStd'));fs={o.Name:o for o in d.Objects};assert len(fs)==54,('count',len(fs));assert all(o.Shape.isValid() and o.Shape.Volume>0 and len(o.Shape.Solids)==1 for o in fs.values()),[(o.Name,o.Shape.isValid(),o.Shape.Volume,len(o.Shape.Solids)) for o in fs.values() if not o.Shape.isValid() or o.Shape.Volume<=0]
 # Compare exact saved old core/endcap/trunk shapes after removing their old display translation.
 b=A.openDocument(str(root/'hardware/compact-dmx/exports/compact-dmx-revb.FCStd'))
 for here,old in [('Protected_core_OD48_ID43_x2_140','B01_Stationary_core'),('Protected_input_endcap_x0_2','B02_Input_endcap_blank'),('Protected_output_endcap_x140_142','B03_Output_endcap_blank'),('Protected_L_N_PE_trunk','B15_Mains_trunk_keepout')]:
  s=b.getObject(old).Shape.copy();s.translate(V(0,-180,0));n=fs[here].Shape;assert s.cut(n).Volume+n.cut(s).Volume<1e-7,(here,'protected geometry differs')
 A.closeDocument(b.Name)
 # Only these exact same-net joints may intersect. Cross-net copper, pins/trunk/core or support collisions never exempted.
 allowed={frozenset(x) for x in [('Land_V_PLUS_top','Trace_PLUS'),('Trace_PLUS','Secondary_PLUS_via_barrel'),('Pigtail_land_PLUS','Secondary_PLUS_via_barrel'),('Pigtail_land_PLUS','Wire_PLUS_conductor'),('Trace_MINUS','Pigtail_land_MINUS'),('Trace_MINUS','Wire_MINUS_conductor'),('Pigtail_land_MINUS','Wire_MINUS_conductor'),('Secondary_PLUS_via_barrel','Wire_PLUS_conductor')]}
 pairs=[];joints=[];graph={n:set() for n in fs}
 for i,a in enumerate(fs.values()):
  for c in list(fs.values())[i+1:]:
   # All pairs counted; disjoint boxes prove disjoint volume without boolean construction.
   ba,bc=a.Shape.BoundBox,c.Shape.BoundBox;overlap=ba.intersect(bc)
   vol=a.Shape.common(c.Shape).Volume if overlap else 0
   if vol>1e-7:
    assert frozenset((a.Name,c.Name)) in allowed,(a.Name,c.Name,vol,'UNEXPECTED INTERSECTION')
    joints.append([a.Name,c.Name,vol])
   dist=a.Shape.distToShape(c.Shape)[0] if ba.intersect(bc) else None
   if dist is not None and dist<1e-6:graph[a.Name].add(c.Name);graph[c.Name].add(a.Name)
   pairs.append([a.Name,c.Name,vol])
 # Every non-reference body is attached/contacting at least one actual assembly body.
 # Small intended clearances are documented separately: source pins do not touch lands (unqualified solder process).
 floaters=[n for n,v in graph.items() if not v and not n.startswith('Protected_')];assert not floaters,('Floating parts',floaters)
 # Mechanical contact graph must join every new part back to the unchanged core, not just an isolated pair.
 reachable={'Protected_core_OD48_ID43_x2_140'}
 while True:
  nxt=reachable|set().union(*(graph[n] for n in reachable))
  if nxt==reachable:break
  reachable=nxt
 assert not [n for n in fs if not n.startswith('Protected_') and n not in reachable],('Disconnected mechanical groups',sorted(set(fs)-reachable))
 # No encoded all-single-fault/electrical proof: deliberately check and report the four still-open pin-to-land joints.
 pintable={'AC_N':(48.4,-10.4,.65,.90),'AC_L':(48.4,10.4,.65,1.40),'V_MINUS':(93.4,-10.4,1.15,.90),'V_PLUS':(93.4,-2.4,1.15,1.40)}
 for n,(x,y,tx,ty) in pintable.items():
  pin=fs['Pin_'+n].Shape;bb=pin.BoundBox;assert abs((bb.XMin+bb.XMax)/2-x)<1e-7 and abs((bb.YMin+bb.YMax)/2-y)<1e-7
  assert abs(bb.ZMax+9)<1e-7 and abs(bb.ZMin+12.5)<1e-7
  assert pin.common(fs['Carrier_PCB_61x32x1p6'].Shape).Volume<1e-7
 # Exhaustive source/process vertical corners, coupled correctly through the same PCB datum.
 corners=[]
 for pb,t,st,L,H in product([-11.05,-10.95],[1.5,1.7],[.35,.45],[2.5,4.5],[23.5,24.5]):
  mb=pb+t+st;tip=mb-L;top=mb+H;projection=pb-.07-tip
  corners.append({'PCB_bottom':pb,'PCB_thickness':t,'standoff':st,'lead_length':L,'module_height':H,'module_bottom':mb,'lead_tip':tip,'module_top':top,'projection_below_bottom_copper':projection})
 projection=min(c['projection_below_bottom_copper'] for c in corners);mintip=min(c['lead_tip'] for c in corners);maxtop=max(c['module_top'] for c in corners)
 assert projection>=.28-1e-7 and mintip>=-13.7-1e-7 and maxtop<=15.7+1e-7
 # Literal old-placement negative case: the V+ maximum lead actually crosses the fixed trunk.
 oldpin=Part.makeCylinder(.5,4.5,V(93.4,-2.4,-10.75),V(0,0,-1))
 oldclash=oldpin.common(fs['Protected_L_N_PE_trunk'].Shape).Volume
 assert oldclash>0 and abs((-10.75-4.5)-(-15.25))<1e-9
 parent_projection=2.5-1.7-.65-.07 # +1.25 shift cannot fix short engagement with this nominal standoff
 assert parent_projection<.28
 # Deck .375 + film .125 total.5 +/- .025; position +/- .025 -> worst top-13.85/bottom-14.425.
 assert mintip-(-13.85)>=.15-1e-7;assert -14.425-(-14.5)>=.075-1e-7
 radial=21.5-math.hypot(14,maxtop);assert radial>.46
 # Source drawing position stack and diameter1.0+/- .5 conservatively applied; pad aperture envelope is not a solder approval.
 fitchecks=0
 for n,(x,y,tx,ty) in pintable.items():
  for dx,dy,D in product([-tx,tx],[-ty,ty],[.5,1.5]):
   pin=Part.makeCylinder(D/2,1.8,V(x+dx,y+dy,-11.1))
   assert pin.common(fs['Carrier_PCB_61x32x1p6'].Shape).Volume<1e-7,(n,dx,dy,D,'aperture does not cover source bounds');fitchecks+=1
 # Independent source-radius and maximum-OD path/sleeve screen. Native nominal all-pair checks cover actual saved pipes.
 def sample(R,y):
  delta=R-9;pts=[]
  for i in range(801):
   q=i/800
   for a,z,t in [(100.5+delta,-11.45+R,-math.pi/2+q*math.pi/2),(100.5+delta,7.55-delta,q*math.pi/2),(100.5+delta,25.55+delta,-math.pi/2-q*math.pi/2)]:pts.append((a+R*math.cos(t),y,z+R*math.sin(t)))
  for i in range(801):pts.append((91.5,y,25.55+delta+(27.5-25.55-delta)*i/800))
  return pts
 mingap=1e9;wirebodygap=1e9;wirechecks=0
 for R,y,dx,dy in product([9,9.1],[-.8,.8],[-.02,.02],[-.02,.02]):
  for x,yy,z in sample(R,y):
   bodydistance=math.sqrt(max(44.85-x-dx,0,x+dx-98.05)**2+max(abs(yy+dy)-14,0)**2+max(-9.2-z,0,z-15.7)**2)-.8
   wirebodygap=min(wirebodygap,bodydistance);assert bodydistance>0,('bounded wire/body',R,y,x,z,bodydistance)
   if 20.2<=z<=24.5:
    inner=2.7+(1.85-2.7)*(z-20.2)/1.15 if z<21.35 else 1.85
    gap=inner-.025-math.hypot(x+dx-92,yy+dy)-.8;mingap=min(mingap,gap);assert gap>=0,(R,y,z,gap)
   if z<20.2:assert math.hypot(abs(yy+dy)+.8,abs(z)+.8)<21.5
   wirechecks+=1
 assert mingap>0
 # Circular surface radii from saved native shape, not the builder path ledger.
 radii=[]
 for n in ['Wire_PLUS_conductor','Wire_MINUS_conductor']:
  for f in fs[n].Shape.Faces:
   if hasattr(f.Surface,'MajorRadius'):radii.append(f.Surface.MajorRadius)
 assert radii and min(radii)>=9-1e-7
 # Saved STEP assembly contains exactly the same solids and volume, including declared same-net overlaps.
 s=Part.read(str(P/'stationary-integration.step'));assert s.isValid() and len(s.Solids)==54 and all(q.isValid() for q in s.Solids);transfer=json.loads((P/'step-parts.json').read_text());assert len(transfer)==54 and {x['part'] for x in transfer}==set(fs)
 # STEP cylinder-intersection mass integration is not identical to native; verify each part with bounded mass and bidirectional edge samples.
 for x in transfer:
  assert abs(x['difference_mm3'])<max(.001,x['native_volume_mm3']*1e-5),(x['part'],'STEP mass transfer screen')
  assert x['bidirectional_edge_sample_max_surface_gap_mm']<1e-6,(x['part'],'STEP sampled surface transfer')
 step_delta=sum(o.Volume for o in s.Solids)-sum(o.Shape.Volume for o in fs.values())
 maxstepgap=max(x['bidirectional_edge_sample_max_surface_gap_mm'] for x in transfer)
 ext=A.openDocument(str(P/'source-lead-extremes.FCStd'));assert len(ext.Objects)==9 and all(o.Shape.isValid() for o in ext.Objects)
 extremebody=ext.getObject('Worst_body_placement_envelope').Shape
 for n in ['Protected_core_OD48_ID43_x2_140','Protected_L_N_PE_trunk','Carrier_PCB_61x32x1p6','Custom_dielectric_sled_and_clamp_brackets']:
  assert extremebody.common(fs[n].Shape.copy()).Volume<1e-7,('worst body envelope',n)
 for o in ext.Objects:
  if o.Name!='Worst_body_placement_envelope':
   bb=o.Shape.BoundBox
   assert abs(bb.XLength-1.5)<1e-7 and abs(bb.YLength-1.5)<1e-7
   assert abs(bb.ZLength-(2.5 if o.Name.endswith('_MIN') else 4.5))<1e-7
   assert abs(bb.ZMax-(-8.8 if o.Name.endswith('_MIN') else -9.2))<1e-7
   assert o.Shape.common(fs['Protected_L_N_PE_trunk'].Shape.copy()).Volume<1e-7
 # Nominal physical clearance independent of analytical bounds.
 clear={n:fs[n].Shape.distToShape(fs['Protected_L_N_PE_trunk'].Shape)[0] for n in ['Pin_V_PLUS','Pin_V_MINUS','IRM20_nominal_body','Polyester_film_allocation','Custom_dielectric_sled_and_clamp_brackets']}
 wirelen=.1+3*9*math.pi/2+10+1.95+2.6
 assert abs(wirelen-(json.loads((P/'build-geometry.json').read_text())['wire_path_length_mm']+2.6))<1e-7
 for n in ['Wire_PLUS_conductor','Wire_MINUS_conductor']:
  assert abs(fs[n].Shape.Volume/(math.pi*.4065**2)-wirelen)<.005,(n,'independent conductor volume / length')
 R20=2*wirelen*.001*35.2/1000;R80=R20*(1+.00393*60)
 # Assembly sweep counterexample: the preformed complete wire/sleeve assembly cannot slide axially through an intact tube.
 a=fs['Wire_PLUS_maximum_OD_insulation'].Shape.copy();a.translate(V(10,0,0));insert_collision=a.common(fs['Protected_core_OD48_ID43_x2_140'].Shape).Volume;assert insert_collision>0
 result={'status':'PASS enumerated saved geometry/source-bound screens; mains/process/assembly qualification UNMET','valid_assembly_objects':len(fs),'STEP_solid_count':len(s.Solids),'STEP_native_mass_integration_delta_mm3':step_delta,'STEP_bidirectional_edge_sample_max_surface_gap_mm':maxstepgap,'STEP_screen_limit':'Each part volume delta < max(.001mm3,10ppm native volume); bidirectional edge-to-surface samples <1e-6mm, not a Hausdorff proof','all_pair_checks':len(pairs),'explicit_same_net_volume_joints':joints,'unexpected_volume_intersections':0,'floating_parts':floaters,'mechanical_contact_graph_all_new_parts_reach_core':True,'original_VPLUS_maxlead_trunk_intersection_mm3':oldclash,'parent_lift_with_065_standoff_min_projection_mm':parent_projection,'protected_saved_core_trunk_endcaps_equal':True,'protected_hashes_verified':len(m),'source_hashes_verified':len(sources),'nominal_clearance_to_trunk_mm':clear,'vertical_corner_cases':len(corners),'minimum_projection_below70um_bottom_copper_mm':projection,'worst_maxlead_tip_Z_mm':mintip,'worst_module_top_Z_mm':maxtop,'bounded_lead_to_deck_gap_mm':mintip+13.85,'bounded_film_to_trunk_gap_mm':.075,'bounded_body_to_nominal_bore_gap_mm':radial,'conservative_pin_aperture_fit_cases':fitchecks,'pin_nominal_diameter_mm':1,'conservative_diameter_range_mm':[.5,1.5],'pin_to_land_solder_or_PTH_process':'UNMET; broad source drawing tolerance forces large mechanical apertures, no validated solder bridge','wire_choice':'Tensility30-02075 solid20AWG mPPE','wire_maxOD_mm':1.6,'source_min_bend_radius_mm':9,'formed_radius_prototype_allocation_mm':[9,9.1],'common_XY_path_fixture_allocation_mm':.02,'minimum_sleeve_inner_diameter_allowance_mm':3.65,'wire_sleeve_tolerance_samples':wirechecks,'minimum_wire_to_sleeve_screen_mm':mingap,'minimum_wire_to_source_max_body_sampled_gap_mm':wirebodygap,'wire_pair_jacket_contact_at_maxOD':True,'wire_length_each_including_bare_mm':wirelen,'wire_pair_R20_max_DCR_based_ohm':R20,'wire_pair_R80_engineering_ohm':R80,'wire_drop_at_3A_screen_V':3*R80,'wire_heat_at_3A_screen_W':9*R80,'no_ampacity_or_faultI2t_grant':True,'complete_preformed_axial_insertion_collision_mm3':insert_collision,'assembly_method':'Wires must be fed/formed and split sleeve assembled after sled insertion; jig/motion/forming/pull/insulation proof UNMET','retention_force_thread_friction_material_qualified':False,'manufacturer_5mm_bottom_10mm_surround_guide_compliance_proven':False,'full_mains_design_or_manufacturing_release':False}
 (P/'contact-graph.json').write_text(json.dumps({n:sorted(v) for n,v in graph.items()},indent=2)+'\n');(P/'vertical-corners.json').write_text(json.dumps(corners,indent=2)+'\n');(P/'pair-checks.json').write_text(json.dumps(pairs,indent=2)+'\n');(P/'checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
except BaseException:
 traceback.print_exc()
 raise
