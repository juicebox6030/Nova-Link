from pathlib import Path
import json,hashlib,math
P=Path(__file__).resolve().parent;R=P.parents[3];sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();load=lambda f:json.loads((P/f).read_text())
protected=load('protected-inputs.json');assert all(sha(R/k)==v for k,v in protected.items())
# Original R1 manifest remains strict; only the exact parent-declared document delta is accepted here.
r1=P.parent/'cylindrical-source-repack';old=json.loads((r1/'protected-inputs.json').read_text());declared=load('parent-correction.json')['expected_parent_document_change']['intentional_parent_deltas'];expected={x['path']:(x['frozen_sha256'],x['current_sha256']) for x in declared};deltas=[]
for k,h in old.items():
 now=sha(R/k)
 if now!=h:assert expected.get(k)==(h,now),(k,h,now);deltas.append(k)
rr=json.loads((r1/'receipt.json').read_text());assert all(sha(r1/k)==v for k,v in rr['artifacts'].items())
for k,v in load('sources.json').items():assert sha(P.parent/k)==v['sha256']
for n,h in [('rotating','f1931419a9a326e5db8364302c8d59cf1586a1ae810676db475f92b45bb97c30'),('stationary','d6f79be09ed5e7984f2f915d9d3b9399978f7412795d7fff4c0ef8d8caabdbdc')]:assert sha(P.parent/'source12-candidate'/('source12-'+n+'.kicad_pcb'))==h
c=load('cad-check.json');cl=load('classified.json');a=load('access-check.json');m=load('motion-clearance.json');e=load('export-check.json');ct=load('contact-check.json');comp=load('comparison.json')
assert c['valid_single_solids']==356 and c['preserved_BRep_numeric_1e12']==317
assert c['new_vs_physical_pairs']==9086 and not cl['unintended'] and len(cl['classified_positive_pairs'])==14
assert not c['lock_access_collisions'] and all(x['proof']!='UNPROVED' for x in c['motion_certificates'])
assert all(x['outside_worst_bore_mm3']<1e-7 for x in c['corridors'])
assert not a['source_failures'] and not a['board_failures'] and len(a['sampled_angles'])==181
assert len(m['stop_positions'])==181 and len(m['lock_positions'])==13 and len(m['released_pin_new_part_pairs'])==84
assert min(x['minimum_BRep_boundary_distance_mm'] for x in m['corridor_boundary_distances'])>.48
assert e['valid_closed'] and e['reopened_solids']==150 and sha(P/'prototype.step')==e['STEP_sha256']
assert len(ct['contacts'])==13 and ct['fuse_unconnected'] and ct['fuse_conductor_envelope_gap']>.99
assert comp['film_worst_bore_clearance']>.37
assert abs(comp['matched_allowance_sensitivity']['classic']['40']['conditional_length_reduction']-25)<1e-9
if (P/'receipt.json').exists():assert all(sha(P/k)==v for k,v in load('receipt.json')['artifacts'].items())
print('PASS bounded integrity/geometry: protected',len(protected),'R1',len(old)-len(deltas),'/',len(old),'plus',len(deltas),'declared parent delta; STEP150; pairs9086;181stops/13locks. PRODUCT HOLD.')
