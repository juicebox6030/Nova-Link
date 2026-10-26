from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;root=P.parents[3];sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
protected=json.loads((P/'protected-inputs.json').read_text());assert all(sha(root/f)==h for f,h in protected.items())
sources=json.loads((P/'sources.json').read_text());assert all(sha(root/x['path'])==x['sha256'] for x in sources)
mechanical=json.loads((P/'mechanical-input.json').read_text());assert sha(root/mechanical['path'])==mechanical['sha256']
erc=json.loads((P/'erc.json').read_text());assert not any(s['violations'] for s in erc['sheets'])
drc=json.loads((P/'drc.json').read_text());assert len(drc['violations'])==4 and all(x['type']=='hole_clearance' for x in drc['violations'])
land=json.loads((P/'land-check.json').read_text());assert land['coordinate_dimension_checks']==57
area=json.loads((P/'placement-check.json').read_text());assert area['physical_footprints']==32 and area['tracks']==0
shapes=json.loads((P/'envelope-check.json').read_text());assert shapes['module_body_core_collision_volume_mm3']==0 and not shapes['module_full_fit']
r={'status':'PASS bounded capture/source/preservation checks; four real geometricDRC issues and functional/fit gates retained','protected_matches':len(protected),'changed_protected':[],'source_PDF_hashes_verified':len(sources),'mechanical_source_hash_match':True,'independent_land_checks':57,'KiCad':'10.0.7','ERC_violations':0,'ERC_ignored_defaults':erc['ignored_checks'],'DRC_violations':len(drc['violations']),'DRC_unconnected':len(drc['unconnected_items']),'DRC_ignored_defaults':drc['ignored_checks'],'DRC_objection':'4USB4105primary-pattern NPTH-to-copper clearances0.1794/0.2283mm fail default0.25mm. No exemptions/rule relaxation. Fabricator/assembly qualification required.','manufacturing_release':False}
(P/'package-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
