from pathlib import Path
import hashlib,json,math
P=Path(__file__).resolve().parent;R=P.parents[3]
j=lambda n:json.loads((P/n).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
x=j('inputs.json');assert len(x)==77 and all(sha(R/k)==h for k,h in x.items())
p=j('patch.json');c=j('check.json');e=j('export-check.json');s=j('section.json')
assert p['revision']=='CAF-R2' and p['passage_z_mm']==[4.0,41.5]
assert p['valid_connected_closed'] and p['added_volume_mm3']<1e-7
assert c['unchanged_other_BReps']==355 and c['all_placements_preserved_numeric_1e12']
assert c['changed_upper_valid_connected_closed'] and c['changed_upper_added_volume_mm3']<1e-7
assert sha(P/'prototype.FCStd')==c['native_sha256']
assert len(c['four_driver_checks'])==4 and all(r['CAF_R2_overlap_mm3']<1e-7 and r['minimum_tool_to_upper_distance_mm']>.249999 for r in c['four_driver_checks'])
assert len(c['four_bearing_checks'])==4 and all(abs(r['before_area_mm2']-r['after_area_mm2'])<1e-6 and abs(r['after_area_mm2']-math.pi*(4-1.2**2))<1e-5 for r in c['four_bearing_checks'])
assert len(s['bearing_seats'])==4 and all(abs(r['old_bearing_area_mm2']-r['new_bearing_area_mm2'])<1e-6 for r in s['bearing_seats'])
assert e['valid_closed'] and e['exported_objects']==150 and e['reopened_solids']==150
assert sha(P/'prototype.step')==e['STEP_sha256']
# Retain the original complete access checks; CAF-R2 removes fixed material only.
q=P.parent/'closure-access-fix';a=json.loads((q/'checks.json').read_text());b=json.loads((q/'screw-insertion.json').read_text())
assert len(a['tool_vs_closed_physical_pairs'])==1356 and max(r['intersection_mm3'] for r in a['tool_vs_closed_physical_pairs'])<1e-7
assert len(a['upper_insertion_fixed_part_checks'])==334 and max(r['swept_bound_intersection_mm3'] for r in a['upper_insertion_fixed_part_checks'])<1e-7
assert b['pairs']==1352 and b['upper_installed'] and not b['unintended']
if (P/'receipt.json').exists():assert all(sha(P/k)==h for k,h in j('receipt.json')['artifacts'].items())
print('CAF-R2 PASS:77 frozen inputs;355 saved BReps and356 placements preserved;four positive driver gaps/four seats;150 STEP solids. PRODUCT HOLD.')
