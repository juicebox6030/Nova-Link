"""Candidate-only final sources/preservation/actual CLI-result audit."""
from pathlib import Path
import json,hashlib,csv
P=Path(__file__).resolve().parent;root=P.parents[3]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
protected=json.loads((P/'protected-inputs.json').read_text())
assert all(sha(root/f)==h for f,h in protected.items())
sources=json.loads((P/'sources.json').read_text())
assert all(sha(root/s['path'])==s['sha256'] for s in sources)
drc=json.loads((P/'drc.json').read_text());assert not drc['violations']
erc=json.loads((P/'erc.json').read_text());assert not any(s['violations'] for s in erc['sheets'])
area=json.loads((P/'area-check.json').read_text());checks=json.loads((P/'checks.json').read_text())
rows=list(csv.DictReader((P/'component-ledger.csv').open()))
assert sum(r['kind']=='added' for r in rows)==area['added_protection_parts']==14
assert area['physical_footprints']==21 and area['numbered_pads']==61
result={'status':'PASS bounded capture/source/preservation/static checks; functional protection acceptance UNMET',
 'protected_matches':len(protected),'changed_protected_files':[],'cached_original_manufacturer_PDF_hashes_verified':len(sources),
 'fuse_source_caveat':'Cached Littelfuse manufacturer PDF is2011 mirror;2025 primary webcrosscheck saved separately, local currentPDF403. No invented2025PDFhash.',
 'ERC_violations':0,'ERC_ignored_defaults':erc['ignored_checks'],
 'DRC_geometric_violations':0,'DRC_unconnected_items':len(drc['unconnected_items']),'DRC_ignored_defaults':drc['ignored_checks'],
 'fitted_to_sidecar':False,'routed':False,'manufacturing_release':False}
(P/'package-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
