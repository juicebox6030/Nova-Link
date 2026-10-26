from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;E=P.parents[1];Q=E/'power-service/qualified15-candidate';C=E/'cell-protection-candidate';I=P.parent/'integrated25'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[Q,C,I,P.parent/'placement-boxes.json']
freeze={str(f.relative_to(P.parents[4])):h(f) for p in paths for f in (p.rglob('*') if p.is_dir() else [p]) if f.is_file() and '__pycache__' not in str(f)}
assert not (P/'frozen-inputs.json').exists();(P/'frozen-inputs.json').write_text(json.dumps(freeze,indent=2)+'\n')
for src,name in [(Q/'Qualified.pretty','Qualified.pretty'),(C/'CellProtection.pretty','CellProtection.pretty'),(I/'Buffer25.pretty','Buffer25.pretty')]:shutil.copytree(src,P/name)
source=(Q/'generate.py').read_text();(P/'qualified-generator-frozen.py').write_text(source)
(P/'protection-generator-frozen.py').write_text((C/'generate.py').read_text())
print(len(freeze))
