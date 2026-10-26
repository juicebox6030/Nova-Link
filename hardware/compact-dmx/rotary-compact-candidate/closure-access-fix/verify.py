from pathlib import Path
import json,hashlib,math
P=Path(__file__).resolve().parent;R=P.parents[3];S=P.parent/'cylindrical-source-repair';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j=lambda n:json.loads((P/n).read_text())
inputs=j('inputs.json');assert all(sha(R/k)==h for k,h in inputs.items())
assert sha(S/'receipt.json')=='0cc43cc3a2596b44cfa81834fe26f41583948954af58fdb4d292100895d1d61f'
for n,h in [('rotating','f1931419a9a326e5db8364302c8d59cf1586a1ae810676db475f92b45bb97c30'),('stationary','d6f79be09ed5e7984f2f915d9d3b9399978f7412795d7fff4c0ef8d8caabdbdc')]:assert sha(P.parent/'source12-candidate'/('source12-'+n+'.kicad_pcb'))==h
p=j('patch.json');c=j('checks.json');s=j('screw-insertion.json');e=j('export-check.json');sec=j('section.json')
assert len(p['rows'])==4 and all(x['before_installed_upper_intersection_mm3']>127 and x['after_installed_upper_intersection_mm3']<1e-7 for x in p['rows'])
assert p['single_connected_closed_valid'] and p['added_volume_mm3']<1e-7
assert c['valid_closed_single_solids']==356 and c['other_shapes_preserved_numeric_1e12']==355 and c['all_placements_preserved']
assert len(c['tool_vs_closed_physical_pairs'])==1356 and max(x['intersection_mm3'] for x in c['tool_vs_closed_physical_pairs'])<1e-7
assert len(c['upper_insertion_fixed_part_checks'])==334 and max(x['swept_bound_intersection_mm3'] for x in c['upper_insertion_fixed_part_checks'])<1e-7
assert c['changed_upper_added_volume_mm3']<1e-7 and c['seat_region_removed_mm3']<1e-7
assert s['pairs']==1352 and len(s['positive'])==4 and not s['unintended'] and s['upper_installed']
assert len(sec['bearing_seats'])==4 and all(abs(x['old_bearing_area_mm2']-x['new_bearing_area_mm2'])<1e-6 for x in sec['bearing_seats'])
assert e['valid_closed'] and e['exported_objects']==150 and e['reopened_solids']==150 and sha(P/'prototype.step')==e['STEP_sha256']
if (P/'receipt.json').exists():assert all(sha(P/k)==h for k,h in j('receipt.json')['artifacts'].items())
print('CAF-R1 PASS:49 input hashes;355 unchanged shapes;1356 installed-driver pairs;334 lid-sweep checks;1352 screw-insertion pairs;150 STEP solids. PRODUCT HOLD.')
