from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[3];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
folders=[P.parent/'power-architecture-screen',P.parent/'collar-source-integrated',P.parents[1]/'eda/buffer-fit-candidate/protected25-placement']
files=[p for f in folders for p in f.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
files += [P.parent/'regulated-source/sources/irm20.pdf',P.parent/'stationary-irm20-integration/sources/meanwell-pcb-installation.pdf',P.parent/'stationary-irm20-integration/sources/meanwell-pcb-installation.txt']
assert not (P/'protected-inputs.json').exists()
(P/'protected-inputs.json').write_text(json.dumps({str(p.relative_to(root)):h(p) for p in files},indent=2)+'\n')
print('FROZEN',len(files))
