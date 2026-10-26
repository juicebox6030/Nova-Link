from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;parts=[json.loads((P/f'reopen-part-{i}.json').read_text()) for i in range(3)]
r=parts[0].copy();r['STEP']=[]
for p in parts:
 assert p['status']=='PASS' and p['native']==parts[0]['native'] and p['bounded_thread_regions']==parts[0]['bounded_thread_regions'] and p['native_sha256']==parts[0]['native_sha256']
 r['STEP']+=p['STEP']
assert len(r['STEP'])==8 and len({p['file'] for p in r['STEP']})==8
assert r['native_sha256']==hashlib.sha256((P/'integrated.FCStd').read_bytes()).hexdigest()
r['STEP']=sorted(r['STEP'],key=lambda x:x['file']);(P/'reopen.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS combined86native/8STEP/14threadregions')
