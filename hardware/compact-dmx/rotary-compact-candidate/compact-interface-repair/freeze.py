from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[3];out={}
for folder in ['combined-compact-allocation','source12-candidate','mechanism-repaired','collar-source-integrated']:
 for p in (P.parent/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in str(p):out[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
assert not(P/'protected-inputs.json').exists()
(P/'protected-inputs.json').write_text(json.dumps(out,indent=2)+'\n');print(len(out))
