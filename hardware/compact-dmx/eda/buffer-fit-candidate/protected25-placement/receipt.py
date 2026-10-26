from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;root=P.parents[4];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ledger={}
for rel in ['hardware/compact-dmx/eda/cell-protection-candidate/sources.json','hardware/compact-dmx/eda/cell-protection-candidate/land-sources.json','hardware/compact-dmx/eda/cell-protection-candidate/component-ledger.csv','hardware/compact-dmx/eda/buffer-fit-candidate/integrated25/sources.json']:
 ledger[rel]={'sha256':sha(root/rel),'basis':'Read-only existing primary-source/part ledger; exact dimensions retained; no new supplier approval'}
(P/'source-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
# Clean only disposable outputs inside this newly owned folder.
for p in P.glob('*.FCBak'):p.unlink()
for p in P.glob('*.kicad_prl'):p.unlink()
import shutil
if (P/'__pycache__').exists():shutil.rmtree(P/'__pycache__')
v=json.loads((P/'verification.json').read_text());m=json.loads((P/'mechanics-check.json').read_text());r=json.loads((P/'reopen.json').read_text())
artifacts={str(p.relative_to(P)):sha(p) for p in P.rglob('*') if p.is_file() and p.name not in ['receipt.json','receipt-check.log']}
receipt={'status':'Bounded candidate completed; conditional geometry with proposed base relief, not protection/manufacturing acceptance','head':'b42c0e6284aac734fde851c69146abf73920f337','owned_path':str(P.relative_to(root)),'frozen_inputs':len(json.loads((P/'frozen-inputs.json').read_text())),'artifacts':artifacts,'checks':v,'mechanics':{'full_pairs':r['full_pairs'],'thread_contacts':len(r['thread_engagements']),'source_shapes_unchanged':r['source_shapes_exactly_preserved'],'native_and_STEP_solids':r['STEP_closed_solids'],'new_body_pairs':len(m['nominal_pairs']),'existing_courtyard_volume_checks':len(m['existing_courtyard_volume_checks']),'nominal_intersections':len(m['nominal_intersections']),'allocated_fuse_base_gap':m['allocated_XY_0_25_down_0_20_base_gap'],'relief':m['relief_bounds']},'remaining_gates':['Unfused trace routing/insulation/restraint and fuse placement approval;11.733819mm straight-line lower bound','Bypass/sense loops and actual copper routing;485unconnected','Base1.6mm floor strength/creep/process, proposed tolerance allocations','Protection turnoff maximum/fuse clearing/healthy10s UNMET','Cell forming/vent/retainer, switch land, USB, RF and factory/assembly qualification unchanged'],'commands':['python3 generate.py','KiCad10.0.7 sch export netlist --format kicadxml','KiCad10.0.7 sch erc --format json','Flatpak python3 place.py and verify.py','KiCad10.0.7 pcb drc --format json --severity-all','FreeCAD offscreen mechanics.py and reopen.py','python3 draw.py; pdftoppm visual inspection']}
(P/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('ARTIFACTS',len(artifacts),'FROZEN',receipt['frozen_inputs'])
