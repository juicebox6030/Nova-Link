from pathlib import Path
import json
r=240*(1-.01-.0001*65);allowed=.25*(155-85)/(155-70)
d={'nominal_parallel_ohm':120,'minimum_each_ohm_at_conservative85C_corner':r,'minimum_parallel_ohm':r/2,'current_at6V_A':6/(r/2),'each_power_at6V_W':36/r,'each_power_at5V_W':25/r,'allowed_each_W_at85C':allowed,'switch_contact_rating_A_at6V':.3,'normal_operation_only_no_fault_rating':True,'assembly_default':'OFF position1; manual latched state retained without power'}
assert d['each_power_at6V_W']<allowed and d['current_at6V_A']<.3
(Path(__file__).parent/'termination-budget.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
