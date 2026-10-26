"""Read-only acceptance of the frozen prototype evidence, not product qualification."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=next(p for p in P.parents if (p/'AGENTS.md').exists())
def read(n):return json.loads((P/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=read('receipt.json')
for n,h in receipt['artifacts'].items():assert sha(P/n)==h,('artifact mutation',n)
protected={}
for f in ['protected-inputs.json','additional-inputs.json','connector-inputs.json']:protected.update(read(f))
for n,h in protected.items():assert sha(R/n)==h,('protected mutation',n)
for s in receipt['sources']:assert sha(R/s['path'])==s['sha256'],('source mutation',s['path'])
pairs=read('pair-classification.json');assert pairs['status']=='PASS' and not pairs['unintended']
rep=read('repaired-pairs.json');wire=read('wire-radius-check.json');assert wire['status']=='PASS' and not wire['unintended'];assert rep['native_sha256']==wire['before_native_sha256'];assert wire['after_native_sha256']==sha(P/'interface-prototype.FCStd');assert wire['unchanged_BRep_numeric_1e12']==356
assert len(rep['unchanged_BRep_structure_numeric_tolerance_1e12'])==358 and rep['pairs']==674
groups=read('groups.json');assert not [n for n in groups if any(v in n for v in ['TARGET','PowerBoard','COL_SRC_','COL_BoardRetainer','COL_TailClamp'])]
pads=read('pad-cad-check.json');assert pads['status']=='PASS' and pads['count']==189
for r in pads['rows']:assert r['centroid_error']<1e-7 and r['volume_error']<1e-7
for zone in ['rotating','stationary']:
 f=f'source12-{zone}.kicad_pcb';assert (P/'electrical-frozen'/f).read_bytes()==(P.parent/'source12-candidate'/f).read_bytes()
assert (P/'electrical-frozen/source12.net').read_bytes()==(P.parent/'source12-candidate/source12.net').read_bytes()
contacts=read('contact-check.json');assert len(contacts['rows'])==22 and max(x['gap'] for x in contacts['rows'])<1e-6
assert not read('primary-check.json')['failures']
access=read('access-check.json');assert access['status']=='PASS' and access['tool_count']==16 and not access['tool_failures'] and not access['USB_failures'] and access['USB_positions']==181
assert all(x['volume']<1e-7 for x in access['board_insertion'])
assert read('lock-access-check.json')['status']=='PASS'
motion=read('motion-check.json');assert motion['status']=='PASS' and not motion['bad'] and len(motion['rows'])==181 and len(motion['lock_rows'])==13
assert all(x['volume']<1e-7 for x in motion['stop_rows']) and min(motion['stop_overtravel'].values())>0
envelope=read('active-envelope-check.json');assert envelope['status']=='PASS' and len(envelope['new_part_rows'])==299 and all(r['volume']<1e-7 for r in envelope['new_part_rows'])
active=read('active-fanout-check.json');assert active['status']=='PASS' and len(active['rows'])==181 and active['min_moving_gap']>0 and active['fixed_gap']>0
native=read('reopen-check.json');assert native['native_sha256']==sha(P/'interface-prototype.FCStd') and len(native['native_parts'])==360
assert all(x=={'valid':True,'closed':True,'solids':1} for x in native['native_parts'].values())
assert receipt['product_qualified'] is False and receipt['compactness_accepted'] is False
print(json.dumps({'status':'PASS frozen mechanical evidence only','artifacts':len(receipt['artifacts']),'protected':len(protected),'sources':len(receipt['sources']),'native_parts':360,'pads':189,'contacts':len(pairs['classified_contacts']),'motion_positions':181,'product_qualified':False},indent=2))
