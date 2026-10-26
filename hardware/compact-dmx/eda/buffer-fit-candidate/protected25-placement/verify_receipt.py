from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[4];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=json.loads((P/'receipt.json').read_text())
for p,h in r['artifacts'].items():assert sha(P/p)==h,p
for p,h in json.loads((P/'frozen-inputs.json').read_text()).items():assert sha(root/p)==h,p
assert r['checks']['board_footprints']==192 and r['checks']['ERC_violations']==0 and r['checks']['DRC_violations']==0
assert r['mechanics']['native_and_STEP_solids']==40 and r['mechanics']['nominal_intersections']==0
print('PASS',len(r['artifacts']),'artifact hashes;',r['frozen_inputs'],'frozen input hashes; conditional prototype only')
