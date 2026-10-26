from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
R=P.parents[3]
files=['hardware/compact-dmx/eda/power-service/qualified15-candidate/'+n for n in ['DESIGN.md','corner-proof.py','corner-proof.json','placement.json','qualified15-placement.kicad_pcb']]+['hardware/compact-dmx/eda/service-footprints/gct-power-candidate/mechanical/flush-prototype.FCStd']
# Run only at initial input capture; screen.py verifies rather than overwrites.
assert not (P/'inputs.json').exists(), 'Initial freeze exists; do not overwrite mutation evidence'
out={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in files}
(P/'inputs.json').write_text(json.dumps(out,indent=2)+'\n')
