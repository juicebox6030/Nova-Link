from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
P=Path(__file__).resolve().parent;root=P.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts={}
for manifest,base in [('protected-inputs.json',root),('source-hashes.json',P),('artifacts.json',P)]:
 data=json.loads((P/manifest).read_text())
 for f,h in data.items():
  if sha(base/f)!=h:
   delta=json.loads((P/'observed-parent-record-delta.json').read_text());assert manifest=='protected-inputs.json' and f in delta and delta[f]['frozen']==h and delta[f]['observed_current']==sha(base/f),(manifest,f)
 counts[manifest]=len(data)
assert zipfile.is_zipfile(P/'sources/tida-cad.zip')
n=json.loads((P/'native-provenance.json').read_text());assert abs(n['width_mm']-66)<1e-6 and abs(n['height_mm']-50)<1e-6
c=json.loads((P/'cad-extraction.json').read_text());assert c['footprint_count']==50
before=sha(P/'numeric-screen.json');subprocess.run([sys.executable,str(P/'screen.py')],check=True,stdout=subprocess.DEVNULL);assert before==sha(P/'numeric-screen.json')
b=json.loads((P/'numeric-screen.json').read_text());assert abs(b['full_input_path_R_ohm']-.18438850632596393)<1e-12
assert b['TIDA_12V_conditional'][-1]['margin_to_1p125_A']<0
assert all(x['port_at_nominal_5V']<4.75 for x in b['direct_5V_counterfactual'])
print(json.dumps({'integrity':'PASS artifacts/sources; frozen inputs except explicitly recorded canonical-doc delta','counts':counts,'native_outline_mm':[66,50],'native_footprints':50,'numeric_reproduction':'PASS','qualification':'NONE'},indent=2))
