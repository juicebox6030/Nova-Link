"""Independent conservative analytic keepout / engineering load screen."""
from pathlib import Path
import json,math
P=Path(__file__).resolve().parent
m=json.loads((P/'motion.json').read_text());rows=[]
for row in m['rows']:
 a=row['angle'];q=math.radians(a)
 # Two radial end faces offset by the finite peg radius, giving nominal +/-90 stops.
 lo=math.pi/2-math.asin(1/28.5);hi=3*math.pi/2+math.asin(1/28.5);theta=math.pi+q
 stopgap=28.5*math.sin(min(theta-lo,hi-theta,math.pi/2))-1
 assert stopgap>-1e-10
 # Rotation invariant radial envelopes; axial separation applies at EVERY angle.
 d={'angle_deg':a,'stop_face_peg_gap_mm':stopgap,'released_pin_to_index_axial_gap_mm':43-(43.7-4.2),'fixed_stop_to_rotating_board_axial_gap_mm':73.8-73.5,'ear_screw_to_active_axial_gap_mm':min(47-(45.75+.9),(68.25-.9)-67),'board_corner_to_shell_mm':32-math.hypot(29.3,9),'connector_corner_to_shell_mm':32-math.hypot(29.41,4.47),'minimum_active_inner_guide_gap_mm':row['guide_inner_gap'],'minimum_active_outer_guide_gap_mm':row['guide_outer_gap']}
 assert all(v>=-1e-8 for k,v in d.items() if k!='angle_deg');rows.append(d)
T=.5;force=T/.0285
# Engineering target, NOT allowable or pass/fail material rating.
loads={'manual_lock_torque_target_Nm':T,'pin_radius_from_axis_mm':28.5,'tangential_load_N':force,'pin_diameter_mm':2,'pin_single_shear_MPa':force/(math.pi),'ring_thickness_mm':1.5,'ring_bearing_stress_MPa':force/(2*1.5),'pin_cantilever_length_allocated_mm':1.7,'pin_bending_stress_MPa':32*force*1.7/(math.pi*2**3),'warning':'No supplier material allowables, insert pullout, creep, fatigue or impact qualification; not a torque rating.'}
# Actual chosen backing is a constant-radius shoe. Tail is pitch-sloped. Its
# available backing-side clearance is smallest at the fixed tail's far end.
b=.30/(2*math.pi);r=25-b*.30;inner_face=r-.08*r/math.hypot(r,b)
clamp={'fixed_tail_backing_min_clearance_mm':inner_face-24.9,'proposed_stiffener_full_thickness_mm':.20,'stiffener_and_assembly_gap_required_mm':.25,'shortfall_mm':.25-(inner_face-24.9),'basis':'Exact normal offset of static continuation at theta=-0.30; backing outer radius24.9. Stiffener is engineering proposal, NOT an added CAD solid or supplier requirement.','disposition':'FAIL selected clamp stack if .20mm stiffener plus .05mm assembly gap is required. No controlled stiffener transition is claimed. Thin bonded tail without stiffener is not approved as a substitute.'}
res={'status':'PATH/KEEP_OUT SCREEN PASS; CLAMP COMPLETION GATE FAIL','positions':181,'rows':rows,'loads':loads,'clamp_stack':clamp,'allocated_tolerance_examples_mm':{'bearing_radial_nominal':.15,'bearing_remaining_after_two_.03_radial_and_.05_runout':.04,'stop_board_axial_nominal':.30,'stop_board_remaining_after_two_.05_positions_and_.05_endplay':.15,'clamp_ear_axial_nominal':.35,'ear_remaining_after_two_.05_positions_and_.05_endplay':.20},'unbounded':['Elastic equilibrium, lateral drift and friction','Supplier actual maximum flex thickness and bend life','Actual board components and static fanout','Clamping stiffness/preload, retention and dynamic material strain']}
(P/'mechanism-screen.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps({k:v for k,v in res.items() if k!='rows'},indent=2))
