from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[3];S=P.parent/'cylindrical-source-repair';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(S/'receipt.json')=='0cc43cc3a2596b44cfa81834fe26f41583948954af58fdb4d292100895d1d61f'
rr=json.loads((S/'receipt.json').read_text());assert all(sha(S/k)==h for k,h in rr['artifacts'].items())
paths=[f for f in S.rglob('*') if f.is_file()]+[P.parent/'source12-candidate'/('source12-'+n+'.kicad_pcb') for n in ['rotating','stationary']]
(P/'inputs.json').write_text(json.dumps({str(f.relative_to(R)):sha(f) for f in sorted(paths)},indent=2)+'\n');print('FROZEN',len(paths))
