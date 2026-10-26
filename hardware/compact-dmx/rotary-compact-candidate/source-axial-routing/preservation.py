"""Rehash current protected inputs and independently constrain the root-authorized metadata delta."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;root=P.parents[3];old=P.with_name('regulated-source');sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
protected=json.loads((P/'protected-inputs.json').read_text());assert all(sha(root/n)==h for n,h in protected.items())
delta=json.loads((P/'accepted-citation-metadata-delta.json').read_text());latest=json.loads((P/'accepted-source-review-metadata-delta.json').read_text());chain=dict(delta['after']);chain.update({str((old/n).relative_to(root)):h for n,h in latest['after'].items()});assert len(delta['after'])==6 and len(latest['after'])==4 and all(sha(root/n)==h for n,h in chain.items())
snapshot=root/'.tools/reviews/rotary-source-20261023';manifest=json.loads((snapshot/'snapshot-manifest.json').read_text());changed=[]
for n,h in manifest.items():
 assert sha(snapshot/n)==h,n
 if sha(old/n)!=h:changed.append(str((old/n).relative_to(root)))
allowed=[str((old/n).relative_to(root)) for n in ['protected-inputs.json','receipt.json','SHA256SUMS','DESIGN.md','verify.py']]
assert set(changed)==set(allowed),(changed,allowed)
# Frozen cell review captured repository-relative paths; only three approvedcell metadata changes.
sm=root/'.tools/reviews/cell-protection-20261023/snapshot-manifest.json';m=json.loads(sm.read_text())['files'];cellchanges=[n for n,h in m.items() if sha(root/n)!=h]
assert set(cellchanges)=={n for n in delta['after'] if '/cell-protection-candidate/' in n},cellchanges
sources=json.loads((P/'sources.json').read_text());assert all(sha(root/s['path'])==s['sha256'] for s in sources)
r={'protected_current_matches':len(protected),'changed_protected':[],'root_authorized_metadata_delta_paths':list(chain),'rotary_review_artifacts_unchanged_other_than_five_authorized_doc_check_inventory_files':True,'cell_review_artifacts_unchanged_other_than_three_metadata_files':True,'primary_PDF_hashes_verified':len(sources),'frozen_rotary_review_hashes_verified':len(manifest)}
(P/'preservation-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
