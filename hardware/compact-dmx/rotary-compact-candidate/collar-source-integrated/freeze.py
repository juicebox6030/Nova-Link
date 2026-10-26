from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;B=P.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(B/'source-axial-routing/source-axial.kicad_pcb')=='53b83aa71d1bcd986906509348bc061eb9e334296ddc980340c954eb8305cbcc'
d={}
for folder in ['mechanism-repaired','source-axial-routing']:
 d[folder]={str(p.relative_to(B/folder)):sha(p) for p in sorted((B/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
(P/'frozen-inputs.json').write_text(json.dumps(d,indent=2)+'\n')
