"""Verify evidence for a REJECTED assembly candidate. Never returns mechanism acceptance."""
from pathlib import Path
import hashlib,json,math
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def read(n):return json.loads((P/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read('receipt.json')
for name,h in r['hashes'].items():assert sha(P/name)==h,('artifact changed',name)
for source in read('sources.json')['sources']:assert sha(ROOT/source['path'])==source['sha256'],source['path']
for source in read('sources.json')['parent_kinematics']:
 assert sha(ROOT/source['path'])==source['sha256']
 assert sha(ROOT/source['copied_to'])==source['sha256']
old=json.loads((P.parent/'receipt.json').read_text())
for name,h in old['hashes'].items():assert sha(P.parent/name)==h,('phase0 changed',name)
m=read('motion.json');assert [x['angle'] for x in m['rows']]==list(range(-90,91))
assert abs(m['active_length_mm']-1046.167655992167)<1e-9
assert m['minimum_turn_gap_mm']>.1398 and m['minimum_bend_R_mm']>24.9999 and m['max_length_error_mm']<1e-8
mec=read('mechanism-screen.json');assert mec['positions']==181
# Independently recompute the exact chosen static-tail/backing clash budget.
b=.30/(2*math.pi);radius=25-.30*b;inner=radius-.08*radius/math.hypot(radius,b)
gap=inner-24.9;assert abs(gap-mec['clamp_stack']['fixed_tail_backing_min_clearance_mm'])<1e-12
assert .25-gap>.2443 # preserves known failure, does not hide it
cad=read('cad-checks.json');saved=read('reopen-checks.json')
assert len(cad['valid_shapes'])==40 and saved['solid_total']==41
assert all(x['closed_solids'] and x['valid'] for x in saved['rows'])
assert len(cad['active_flex_selected_pose_checks'])==105
assert len(cad['selected_mechanism_checks'])==93
assert all(x['intersection_mm3']<1e-8 for x in cad['active_flex_selected_pose_checks']+cad['selected_mechanism_checks'])
assert cad['valid_shapes']['RotorHalfPositiveY']['solids']==2 # disconnected backing remains rejected
contacts=cad['neutral_positive_volume_contacts'];assert len(contacts)==17
heads=[x for x in contacts if x['a'].startswith('FrameBolt') and x['b']=='RotorHalfPositiveY']
assert len(heads)==4 and all(.57<x['volume_mm3']<.58 for x in heads)
assert r['assembly_accepted'] is False
print(json.dumps({'evidence_integrity':'PASS','assembly_acceptance':'FAIL / intentionally retained completion defects','artifact_hashes':len(r['hashes']),'primary_sources':3,'parent_source_copies':2,'frozen_phase0_artifacts':len(old['hashes']),'path_positions':181,'valid_closed_solids':41,'active_flex_CAD_pairs_clear':105,'selected_stationary_moving_pairs_clear':93,'neutral_contacts_retained':17,'clamp_stack_shortfall_mm':.25-gap},indent=2))
