"""Constant output power, explicit cell ESR; no converter efficiency guarantee."""
from pathlib import Path
import math,json,hashlib
P=Path(__file__).resolve().parent
START=2.448;FLOOR=1.705917;LOAD=1.11

def runtime(c,r,eta=.8,start=START,n=10000):
 power=LOAD/eta;end=FLOOR+r*power/FLOOR
 if end>=start or end*end<4*r*power:return 0.
 def f(v):return (v+math.sqrt(v*v-4*r*power))/2
 h=(start-end)/n
 return c/power*h/3*(f(end)+f(start)+sum((4 if i%2 else 2)*f(end+i*h) for i in range(1,n)))
parts=[('HV1325-2R7156-R',15,.9,.030,[13.5,28.4]),('HV1625-2R7256-R',25,.9,.027,[16.5,28.4]),('SCCT30B186SRB',18,.9,.060,[13.5,32]),('SCCT35B226SRB',22,.9,.058,[13.5,37]),('CXHP2R7206R-TW',20,.8,.060,[13.5,26.5])]
out=[]
for mpn,c,tol,r,dims in parts:
 effective=c*tol*.7
 out.append({'MPN':mpn,'nominal_F':c,'initial_tolerance_factor':tol,'aging_factor':.7,'effective_F':effective,'max_body_diameter_length_mm':dims,'initial_ESR_ohm':r,'aged_ESR_ohm':2*r,'initial_ESR_aged_C_runtime_s':runtime(effective,r),'aged_ESR_aged_C_runtime_s':runtime(effective,2*r),'nominal_25mA_2p6V_charge_min':c*2.6/.025/60})
assert abs(out[0]['aged_ESR_aged_C_runtime_s']-9.729548)<1e-5
pref=out[1];assert pref['aged_ESR_aged_C_runtime_s']>16
assert abs(runtime(15.75,.054,n=20000)-runtime(15.75,.054))<1e-8
# Independently integrate dV/dt=-I/C with tiny steps, terminate at loaded floor.
v=START;t=0;dt=.0001;p=LOAD/.8
while True:
 vt=(v+math.sqrt(v*v-4*.054*p))/2
 if vt<=FLOOR:break
 v-=p/vt/15.75*dt;t+=dt
assert abs(t-pref['aged_ESR_aged_C_runtime_s'])<.001
sens=[{'eta':eta,'ESR_ohm':r,'runtime_s':runtime(15.75,r,eta)} for eta in [.7,.75,.8,.85] for r in [.054,.108,.162]]
chargecorner=25*1.3*2.652/(270/(12000*(1+.0035)))/60
# Raising charge voltage alone: ideal even zeroESR aged15F requires this start for12s.
required_start=math.sqrt(FLOOR**2+2*LOAD*12/(9.45*.8))
inputs=json.loads((P/'inputs.json').read_text());changes=[k for k,v in inputs.items() if hashlib.sha256(Path(k).read_bytes()).hexdigest()!=v]
report={'assumptions':{'start_V':START,'loaded_cutoff_V':FLOOR,'load_W':LOAD,'electronics_efficiency':.8,'cold_ESR_limit':None,'aging_note':'Independent initial tolerance and70%retention; endurance-test limits, not field lifetime guarantee'},'parts':out,'preferred_sensitivity':sens,'preferred_cell_current_at_cutoff_A':LOAD/.8/FLOOR,'preferred_ESR_loss_at_cutoff_W':(LOAD/.8/FLOOR)**2*.054,'preferred_charge_corner_min_before_tail':chargecorner,'preferred_nominal_stored_J_at2p6':.5*25*2.6**2,'preferred_max_stored_J_at2p7_32p5F':.5*32.5*2.7**2,'ideal15F_start_required_for12s_V':required_start,'crosscheck_forward_time_s':t,'concurrent_input_changes':changes,'measured_runtime':False}
(P/'screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
