"""Independent evidence contract. Does not refresh hashes or claim physical qualification."""
from pathlib import Path
import json,hashlib,itertools,copy,math
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def read(n):return json.loads((P/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
f=read('frozen-inputs.json');old=ROOT/f['read_only_parent_path']
assert sha(old/'receipt.json')==f['original_receipt_sha256']
assert sha(P/'failed-receipt.json')==f['original_receipt_sha256']
for n,h in f['original_artifacts'].items():assert sha(old/n)==h,('original modified',n)
for n,h in f['copied_evidence'].items():assert sha(P/n)==h,('copied input changed',n)
for s in read('sources.json')['sources']:assert sha(ROOT/s['path'])==s['sha256'],s['path']
r=read('receipt.json')
for n,h in r['hashes'].items():assert sha(P/n)==h,('artifact modified',n)
assert r['geometric_prototype_accepted'] and not r['physical_qualification'] and not r['source_board_integrated']
g=read('groups.json');excluded={n for n,v in g.items() if v.startswith('pose') or v in ['placeholder','screen']}
assert excluded=={'Flex_minus90','Flex_0','Flex_90','Components_TARGET','USBPlugScreen'}
physical=(set(g)-excluded)|{'ActiveFlex'}
assert len(g)==43 and len(physical)==39
expected_pairs={tuple(sorted(p)) for p in itertools.combinations(physical,2)}
expected_threads={tuple(sorted((n,'StationarySpool'))) for n in ['FixedScrew0','FixedScrew1']}
expected_threads|={tuple(sorted((n,'RotorHalfPositiveY'))) for n in ['MovingScrew0','MovingScrew1']}
expected_threads|={tuple(sorted((n,'RotorHalfNegativeY'))) for n in g if n.startswith('FrameBolt')}
expected_threads|={tuple(sorted(p)) for p in [('IndexRearCap','StationarySpool'),('IndexKnob','IndexPin')]}
assert len(expected_threads)==10
c=read('checks.json')
def validate_pairs(c):
 assert not c['residual'] and c['status']=='PASS'
 assert {tuple(sorted(x['parts'])) for x in c['allowed_thread_pairs']}==expected_threads
 for angle in [-90,0,90]:
  for released in [False,True]:
   rows=[x for x in c['pairs'] if x['angle']==angle and x['released']==released]
   assert len(rows)==len(expected_pairs)
   assert {tuple(sorted((x['a'],x['b']))) for x in rows}==expected_pairs
   for x in rows:
    key=tuple(sorted((x['a'],x['b'])))
    if key not in expected_threads:assert x['thread_limit_mm3']==0 and x['intersection_mm3']<1e-6
    else:assert 0<x['thread_limit_mm3']<=3.2 and x['intersection_mm3']<=x['thread_limit_mm3']+1e-6
validate_pairs(c);assert len(c['pairs'])==4446
# Bounded in-memory mutations must fail; no active geometry or evidence is changed.
bad=copy.deepcopy(c);bad['pairs'][0]['intersection_mm3']=.1
try:validate_pairs(bad);raise RuntimeError('collision mutation escaped')
except AssertionError:pass
bad=copy.deepcopy(c);bad['pairs'].pop()
try:validate_pairs(bad);raise RuntimeError('coverage mutation escaped')
except AssertionError:pass
v=read('reopen.json');assert len(v['native'])==43 and len(v['STEP'])==7 and len(v['thread_regions'])==10
assert all(x['valid'] and x['closed'] and x['solids']==1 for x in v['native'])
for x in v['STEP']:assert x['each_solid_valid_closed'] and x['solids']==(38 if x['path']=='exploded.step' else 39)
cl=read('clearances.json');assert cl['status']=='PASS' and len(cl['distances'])==10
assert all(x['distance_mm']>=x['minimum_screen_mm'] for x in cl['distances'])
assert abs(cl['integral_stop_stub_volume_mm3']-math.pi)<1e-6
access=read('access.json');assert access['status']=='PASS' and all(x['intersection_mm3']<1e-6 for x in access['checks'])
sw=read('sweep.json');assert [x['angle'] for x in sw['rows']]==list(range(-90,91))
assert sum(x['lock_allowed'] for x in sw['rows'])==13
assert all(x['released_intersection_mm3']<1e-6 for x in sw['rows'])
assert all((x['locked_pin_intersection_mm3']<1e-6 if x['lock_allowed'] else x['locked_pin_intersection_mm3']>.01) for x in sw['rows'])
con=read('containment.json');assert con['status'].startswith('PASS') and con['sweep_input_sha256']==sha(P/'sweep-envelope.FCStd')
assert con['moving_outside_swept_input_mm3']<1e-6 and con['pin_union_outside_original_mm3']<1e-6 and con['tip_geometry_equal']
assert con['added_key_XMax_mm']<=41.40001 and con['rotor_XMin_mm']>=41.99999
assert all((x['intersection_mm3']<1e-6 if x['allowed'] else x['intersection_mm3']>.01) for x in con['axial_stop_checks'])
assert len(con['rear_insertion_checks'])==13 and all(x['housing_intersection_mm3']<1e-6 for x in con['rear_insertion_checks'])
assert all(x['key_interference_mm3']>.01 for x in con['stem_key_checks'])
m=read('motion.json');assert len(m['rows'])==181 and m['minimum_turn_gap_mm']>.1398 and m['minimum_bend_R_mm']>24.9999 and m['max_length_error_mm']<1e-8
d=read('dimensions.json');assert d['power_placeholder']['maximum_height_mm']==3.46 and d['power_placeholder']['assembly_height_allowance_mm']==.15
assert d['static_stack']['fixed_min_unpadded_gap_mm']>.055 and d['static_stack']['moving_min_unpadded_gap_mm']>.055
assert abs(d['power_placeholder']['reserved_outer_corner_radius_mm']-math.hypot(29.71,9))<1e-12
print(json.dumps({'status':'PASS geometric prototype evidence; physical qualification remains open','artifact_hashes':len(r['hashes']),'frozen_original_hashes':len(f['original_artifacts']),'primary_sources':3,'native_connected_closed_parts':43,'STEP_exports_reopened':7,'full_pair_checks':4446,'permitted_named_thread_interfaces':10,'unexpected_intersections':0,'tool_checks':len(access['checks']),'released_motion_positions':181,'detents':13,'in_memory_negative_checks':2,'source_board_integrated':False},indent=2))
