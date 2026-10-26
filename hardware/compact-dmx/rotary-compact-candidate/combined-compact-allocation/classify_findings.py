"""Account for every positive volume; never turn an interface failure into PASS."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;c=json.loads((P/'checks.json').read_text());out=[]
contacts={frozenset(p) for p in [('Trunk_L','L_TrunkToFuse'),('Trunk_N','N_TrunkToCarrier'),('L_FuseToCarrier','Pin_L'),('N_TrunkToCarrier','Pin_N'),('Pin_LVminus','LV_minus_underCarrier'),('Pin_LVplus','LV_plus_underCarrier'),('LV_minus_toClamp','COL_FixedStaticTail')]}
for r in c['positive_intersections']:
 pair=frozenset([r['a'],r['b']])
 if pair in contacts:category='intended electrical endpoint envelope; stripping/solder/terminal construction NOT qualified'
 elif r['a']=='Carrier61x32PlanningPlate' and r['b'] in ['Pin_N','Pin_L','Pin_LVminus','Pin_LVplus']:category='UNMET carrier interface: required pin passage/pad construction not designed'
 elif r['kind']=='electrical_interface_crossing_UNQUALIFIED':category='UNMET source reservation crossing: electrical lead construction requires approval; no distance waiver'
 else:category='FAIL unintended physical interference'
 out.append(dict(r,classification=category))
r={'status':'FAIL integration acceptance','positive_volumes':out,'unintended_count':sum(x['classification'].startswith('FAIL') for x in out),'disconnected_contacts':c['disconnected_wire_contacts'],'USB_geometric_failures':len(c['USB_failures']),'note':'All23 positive volumes are explicit. Valid solids andUSB clearance do not override failed electrical routing/interfaces.'}
(P/'findings.json').write_text(json.dumps(r,indent=2)+'\n');print('FAIL unintended',r['unintended_count'],'disconnected',len(r['disconnected_contacts']),'accounted volumes',len(out))
