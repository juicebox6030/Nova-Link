"""Recompute the captured source model with actual added conductors. No hardware assurance."""
from pathlib import Path
from itertools import product
import hashlib,json,math
P=Path(__file__).resolve().parent; B=P.parent
inputs=['regulated-source/verify.py','collar-source-integrated/fanout-proof.json','stationary-irm20-integration/checks.json']
fanout=json.loads((B/inputs[1]).read_text());wire=json.loads((B/inputs[2]).read_text())
# Same documented model as regulated-source/verify.py: forced-PWM upper DC
# output, 80% efficiency, 410mA VCONN, 1mA output/5mW input auxiliary allocations.
vsource=4.6375; efuse_floor=3334/1002*.9
vout=max(v*(1+54200*(1+a)/(10000*(1+b)))+i*54200*(1+a)
         for a,b,v,i in product([-.002,.002],[-.002,.002],[.792,.808],[-1e-7,1e-7]))
base=2*1.046167656*1.75e-8/(.0078*70e-6*.9)*(1+.00393*60)+.020+.045
rows=[]
for label,extra in [('original',0),('added_tail_nominal_hot',fanout['additional_loop_R85_ohm']),('added_tail_engineering_corner',fanout['allocated_63um_plus3percent_rho_hot_loop_ohm']),('added_tail_and_stationary_wires',fanout['allocated_63um_plus3percent_rho_hot_loop_ohm']+wire['wire_pair_R80_engineering_ohm'])]:
    resistance=base+extra; power=vout*1.911/.8+.005
    current=(vsource-math.sqrt(vsource*vsource-4*resistance*power))/(2*resistance)
    alternate=2
    for _ in range(100): alternate=power/(vsource-alternate*resistance)
    assert abs(current-alternate)<1e-11
    rows.append(dict(case=label,loop_ohm=resistance,current_A=current,converter_input_V=vsource-current*resistance,breaker_floor_A=efuse_floor,breaker_margin_A=efuse_floor-current,passes=current<efuse_floor))
assert rows[0]['passes'] and all(not r['passes'] for r in rows[1:])
result=dict(status='FAIL assembled stress-current screen; arithmetic regression reproduced',source_artifact_hashes={n:hashlib.sha256((B/n).read_bytes()).hexdigest() for n in inputs},cases=rows,scope='Existing unmeasured source-model allocations retained. Tail85C and stationary-wire80C allocations are screening temperatures, not a coherent measured thermal corner. Joint losses omitted. No changed circuit or manufacturing acceptance.')
(P/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'margins_mA':{r['case']:round(1000*r['breaker_margin_A'],3) for r in rows}},indent=2))
