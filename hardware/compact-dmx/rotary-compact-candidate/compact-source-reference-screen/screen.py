from pathlib import Path
import json, math, hashlib
P=Path(__file__).resolve().parent
root=P.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,h in json.loads((P/'protected-inputs.json').read_text()).items():
 
 if sha(root/rel)!=h:
  delta=json.loads((P/'observed-parent-record-delta.json').read_text());assert rel in delta and delta[rel]['frozen']==h and delta[rel]['observed_current']==sha(root/rel),rel
cir=json.loads((P.parent/'compact-interface-repair/numeric-check.json').read_text())
active=2*1.046167656*1.75e-8/(.0078*70e-6*.9)*(1+.00393*60)
r=active+.020+.045+cir['static_flex_hot_loop_ohm']+cir['wire_hot_loop_ohm_nominal_1mm_copper']
cases=[]
for vconn in [0,.250,.410]:
 ib=1.5+.010+vconn
 drop=ib*(r+.064)+1.5*(.055+.020+.025)+.050
 cases.append(dict(VCONN_A=vconn,bus_A=ib,allocated_drop_V=drop,source_low_needed_V=4.75+drop,port_at_nominal_5V=5-drop,source_corner_window_to_5p45_V=5.45-(4.75+drop)))
s12=json.loads((P.parent/'source12-candidate/electrical-check.json').read_text())
loads=[]
for load in [1.76,1.92,2.24]:
 power=s12['regulation']['reference_divider_bias_corners_V'][1]*load/.8
 i=.002
 for _ in range(100):i=power/(12.1-i*r)+.002
 loads.append(dict(buck_output_A=load,conditional_12p1V_input_A=i,margin_to_1p125_A=1.125-i))
out={'revision':'CSR-R1','active_hot_loop_ohm':active,'full_input_path_R_ohm':r,'direct_5V_counterfactual':cases,'TIDA_12V_conditional':loads,'assumptions':'80C copper; inherited minimum flex section; nominal wire copper; 20mohm input termination/PCB allowance; 80% buck efficiency not guaranteed; 50mV one-sided output allowance; no revised circuit selected','areas_mm2':{'IRM_body':52.9*27.7,'IRM_conservative_carrier':81*52,'TIDA_actual_board':66*50},'complete_enclosure_comparison':'UNKNOWN; installation, maximum assembled height, harness and retention unresolved','status':'SCREEN ONLY; no electrical or mechanical qualification'}
(P/'numeric-screen.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
