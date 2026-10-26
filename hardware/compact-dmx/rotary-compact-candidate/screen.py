"""Phase0 failure screen. No qualified flex-motion or product CAD claim."""
from pathlib import Path
import math,json,csv
P=Path(__file__).resolve().parent
I=1.5;vlow=5*.975;rho20=1.75e-8;alpha=.00393
# rho/alpha/process/termination values are engineering allocations, not flex supplier guarantees.
rows=[]
for L in [.8,1.,1.1]:
 for t in [35e-6,70e-6]:
  for temp in [20,80]:
   R=2*L*rho20*(1+alpha*(temp-20))/((.008-.0002)*(t*.9))
   term=.020;switch=.055
   rows.append(dict(length_m=L,copper_nom_um=t*1e6,temp_C=temp,loop_R_ohm=R,flex_drop_V=I*R,flex_heat_W=I*I*R,termination_drop_V=I*term,TPS_drop_V=I*switch,port_DC_V=vlow-I*(R+term+switch),pass_4p75=vlow-I*(R+term+switch)>=4.75))
assert not any(r['pass_4p75'] for r in rows)
# Even optimistic no process allowance, zero terminations,25C IC max37mohm fails70um/1m at20C.
best_R=2*1*rho20/(.008*70e-6);best_port=vlow-I*(best_R+.037)
assert best_port<4.75
remaining_R=(vlow-4.75)/I-.055
required_t_no_term=2*1*rho20*(1+alpha*60)/(.008*remaining_R)
required_t_with_term=2*1*rho20*(1+alpha*60)/(.008*(remaining_R-.02))
# Fixed-radius Archimedean spiral falsification, not an elastic clockspring solution.
ri=25.;ro=30.5;N=6.;thickness=.16

def length(n,end=ro):
 phi=2*math.pi*n;b=(end-ri)/phi
 def f(r):return .5*(r*math.sqrt(r*r+b*b)+b*b*math.asinh(r/b))
 return (f(end)-f(ri))/b
L0=length(N);motion=[]
for angle in range(-90,91):
 n=N+angle/360;L=length(n);pitch=(ro-ri)/n
 lo,hi=25.00001,40.
 for _ in range(70):
  mid=(lo+hi)/2
  if length(n,mid)<L0:lo=mid
  else:hi=mid
 rr=(lo+hi)/2
 motion.append(dict(angle_deg=angle,turns=n,pitch_mm=pitch,interturn_radial_gap_mm=pitch-thickness,fixed_radius_length_mm=L,length_error_mm=L-L0,constant_length_free_outer_radius_mm=rr,outer_radius_pass=rr<=ro))
with (P/'spiral-diagnostic.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=motion[0].keys(),lineterminator='\n');w.writeheader();w.writerows(motion)
# One compensation direction: local rotating regulator BEFOREsourcecontroller.
# Specification target only, no selected part or guaranteed conversion efficiency.
out=5.10;regtol=.01;postR=.02;switch=.055;targetmin=out*(1-regtol)-I*(postR+switch)
Pin=(out*I+.015)/.90
Rworst=next(r['loop_R_ohm'] for r in rows if r['length_m']==1.1 and r['copper_nom_um']==70 and r['temp_C']==80)+.02
vs50=vlow-5*.0003*25
current=(vs50-math.sqrt(vs50**2-4*Rworst*Pin))/(2*Rworst)
report={'status':'PHASE0 FAIL unchanged5Vsourcepath; no complete compact assembly produced','electrical_rows':rows,'IRM_voltage_min_25C_V':vlow,'line_load_already_in_tolerance':True,'optimistic_1m70um_no_terms_port_V':best_port,'allowed_FPC_R_with_zero_termination_ohm':remaining_R,'required_actual_copper_um_at1m80C_8mm_no_terms':required_t_no_term*1e6,'required_actual_copper_um_with20mohm_terms':required_t_with_term*1e6,'motion_diagnostic':{'positions':len(motion),'neutral_length_mm':L0,'min_radial_turn_gap_mm':min(m['interturn_radial_gap_mm'] for m in motion),'length_error_endpoints_mm':[motion[0]['length_error_mm'],motion[-1]['length_error_mm']],'constant_length_required_outer_radius_minus90_mm':motion[0]['constant_length_free_outer_radius_mm'],'not_a_motion_solution':True},'compensation_direction_only':{'local_regulator_before_TPS_V':out,'regulation_target':regtol,'DC_min_port_V':targetmin,'efficiency_allocation':.9,'input_power_W':Pin,'IRM50C_low_V':vs50,'source_current_A':current,'regulator_input_V':vs50-current*Rworst,'requires_new_component_capture':True},'lock_stress_screen':{'torque_target_Nm':1.,'pin_radius_mm':28.,'pin_diameter_mm':2.,'index_thickness_mm':1.5,'pin_shear_MPa':1000/28/(math.pi),'ring_bearing_MPa':1000/28/(2*1.5),'material_allowable_not_established':True},'manufacturing_release':False}
(P/'screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='electrical_rows'},indent=2))
