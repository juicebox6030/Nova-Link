from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[3];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=json.loads((P/'receipt.json').read_text())
for p,v in r['artifacts'].items():assert h(P/p)==v,p
n=0
for f in ['protected-inputs.json','source12-frozen-inputs.json']:
 for p,v in json.loads((P/f).read_text()).items():assert h(root/p)==v,p;n+=1
for s in json.loads((P/'sources.json').read_text()):assert h(root/s['path'])==s['sha256'],s['path']
assert r['S12_receipt_sha256']=='51393c2a663f8cc206af64d4d0aa09d541832f1a5ac542f7a93bc06f95e2e519'
print('PASS artifact hashes',len(r['artifacts']),'protected entries',n,'sources',len(json.loads((P/'sources.json').read_text())),'NOT a geometry acceptance')
