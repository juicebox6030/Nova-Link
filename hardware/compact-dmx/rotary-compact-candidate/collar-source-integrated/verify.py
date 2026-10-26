"""Independent final evidence contract; never updates frozen hashes."""
from pathlib import Path
import json,hashlib,itertools,copy,math,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def read(n):return json.loads((P/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
f=read('frozen-inputs.json');count=0
for folder,items in f.items():
 for name,h in items.items():assert sha(P.parent/folder/name)==h,('frozen input changed',folder,name);count+=1
board='53b83aa71d1bcd986906509348bc061eb9e334296ddc980340c954eb8305cbcc';assert sha(P/'source-board-unchanged.kicad_pcb')==board
for s in read('sources.json')['sources']:assert sha(ROOT/s['path'])==s['sha256']
g=read('groups.json');assert len(g)==86
assert not any('TARGET' in n or n=='USB4105ShellEnvelope' or n.startswith('USBStake') for n in g)
physical={n for n,k in g.items() if k not in ['reserve','screen'] and not k.startswith('pose')}|{'ActiveFlex'};assert len(physical)==78
pairs={tuple(sorted(q)) for q in itertools.combinations(physical,2)}
c=read('checks.json')
old= json.loads((P.parent/'mechanism-repaired/checks.json').read_text())
expected={tuple(sorted(x['parts'])) for x in old['allowed_thread_pairs']}
expected|={tuple(sorted((n,'RotorHalfPositiveY'))) for n in ['BoardRetainerScrew_m11','BoardRetainerScrew_11','TailClampScrew_74_4','TailClampScrew_96_6']}
def check(data):
 assert data['status']=='PASS' and not data['residual']
 assert {tuple(sorted(x['parts'])) for x in data['allowed_threads']}==expected and len(expected)==14
 for angle in [-90,0,90]:
  for released in [False,True]:
   rows=[r for r in data['pairs'] if r['angle']==angle and r['released']==released]
   assert len(rows)==len(pairs) and {tuple(sorted((r['a'],r['b']))) for r in rows}==pairs
   for r in rows:
    if tuple(sorted((r['a'],r['b']))) not in expected:assert r['thread_limit_mm3']==0 and r['intersection_mm3']<1e-6
    else:assert 0<r['thread_limit_mm3']<=3.2 and r['intersection_mm3']<=r['thread_limit_mm3']+1e-6
check(c);assert len(c['pairs'])==18018
bad=copy.deepcopy(c);bad['pairs'].pop()
try:check(bad);raise RuntimeError('missing-pair mutation escaped')
except AssertionError:pass
bad=copy.deepcopy(c)
for r in bad['pairs']:
 if r['thread_limit_mm3']==0:r['intersection_mm3']=.1;break
try:check(bad);raise RuntimeError('collision mutation escaped')
except AssertionError:pass
s=read('source-contract.json');assert s['status'].startswith('PASS') and s['transform']['determinant']==1 and s['transform']['translation_mm']==[75,26.1,10]
assert len(s['source_shape_checks'])==42 and all(x['inverse_transform_symmetric_difference_mm3']<1e-7 for x in s['source_shape_checks'])
assert all(x['intersection_mm3']<1e-6 for key in ['assembly_reserve_checks','plug_checks','insertion_checks','continuous_insertion_bounds'] for x in s[key])
assert len(s['continuous_insertion_bounds'])==152
assert len(s['plug_checks'])==231 and len(s['insertion_checks'])==132 and s['OD_mm']==66 and s['locked_span_mm']==73.17 and s['released_span_mm']==77.37
assert not s['source_board_functional_acceptance'] and not s['supplier_connector_profile_approved']
m=read('motion-check.json');assert m['status'].startswith('PASS') and len(m['rows'])==181 and sum(x['detent'] for x in m['rows'])==13
assert len(m['unchanged_active_pose_checks'])==3 and all(x['equal'] and x['all_edges_straight'] and x['plane_polygon_faces']==4100 and x['volume_difference_mm3']<1e-7 for x in m['unchanged_active_pose_checks'])
assert all(x['added_material_full_revolution_bound_mm3']<1e-6 and x['old_released_intersection_mm3']<1e-6 for x in m['rows'])
assert all((x['locked_pin_intersection_mm3']<1e-6 if x['detent'] else x['locked_pin_intersection_mm3']>.01) for x in m['rows'])
a=read('access.json');assert a['status']=='PASS' and len(a['checks'])==1078 and all(x['intersection_mm3']<1e-6 for x in a['checks'])
ct=read('contacts.json');assert ct['status'].startswith('PASS') and len(ct['contacts'])==5 and len(ct['new_threads'])==4
cu=read('copper-check.json');assert cu['board_sha256']==board and cu['footprints']==34 and cu['numbered_pad_primitives']==127 and cu['actual_holes_clear']==98 and cu['minimum_copper_gap_mm']>=.30049
pads={p['pin']:p for p in cu['termination_pads']};assert pads['1']['net']=='FPC_5V' and pads['2']['net']=='GND_ISO';assert pads['1']['local_xy_mm']==[6,18.4] and pads['2']['local_xy_mm']==[15,18.4]
xmlpins={n.get('pin'):net.get('name').lstrip('/') for net in E.parse(P.parent/'source-axial-routing/regulated-source.net').findall('./nets/net') for n in net if n.get('ref')=='J0'}
assert {k:v['net'] for k,v in pads.items()}==xmlpins
assert all(p['size_mm']==[8,2] and abs(p['corner_radius_mm']-.2)<1e-7 for p in pads.values())
fp=read('fanout-proof.json');assert fp['ruling_direction']==[1,0,0] and fp['terminal_bend_radius_mm']==2.5 and fp['source_budget_requalification_required'] and fp['not_in_active_motion_proof']
assert 183<fp['static_centerline_length_mm']<184 and .014<fp['additional_loop_R85_ohm']<.015
r=read('reopen.json');assert r['status']=='PASS' and r['native_sha256']==sha(P/'integrated.FCStd') and len(r['native'])==86 and len(r['STEP'])==8 and len(r['bounded_thread_regions'])==14
assert all(x['valid'] and x['closed'] and x['solids']==1 for x in r['native']);assert all(x['each_valid_closed'] for x in r['STEP'])
receipt=read('receipt.json')
for n,h in receipt['hashes'].items():assert sha(P/n)==h,('artifact changed',n)
assert receipt['geometric_prototype_accepted'] and not receipt['manufacturing_release'] and not receipt['electrical_acceptance']
print(json.dumps({'status':'PASS integrated geometric prototype; physical/electrical/manufacturing qualification OPEN','frozen_input_hashes':count,'artifact_hashes':len(receipt['hashes']),'source_board_bytes_unchanged':board,'native_connected_closed_parts':86,'saved_STEP_exports':8,'full_pair_checks':18018,'unexpected_intersections':0,'bounded_thread_interfaces':14,'source_shapes_preserved':42,'tool_checks':1078,'plug_checks':231,'board_slide_checks':132,'released_positions':181,'detents':13,'negative_mutation_checks':2,'static_extension_hot_loop_ohm':fp['additional_loop_R85_ohm']},indent=2))
