from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[3];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=json.loads((P/'receipt.json').read_text())
for p,v in r['artifacts'].items():assert h(P/p)==v,p
for p,v in json.loads((P/'protected-inputs.json').read_text()).items():assert h(root/p)==v,p
for s in json.loads((P/'sources.json').read_text()):assert h(root/s['path'])==s['sha256'],s['path']
c=json.loads((P/'checks.json').read_text());assert c['status']=='PASS allocation screens' and not c['spacing_failures'];assert all(c['native_valid'].values())
assert c['motion_positions']==181 and len(c['detents'])==13 and not any(m['intersection']>1e-7 for m in c['motion'])
assert c['whole_product_planning_dimensions']==[330.,89.,72.]
assert all(x['valid'] for x in c['STEP'].values())
print('PASS',len(r['artifacts']),'artifact hashes,',r['protected_inputs'],'protected inputs,',r['source_files'],'source hashes;330x89x72allocation; construction NOT released')
