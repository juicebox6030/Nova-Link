from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;R=P.parents[3];B=P.parent
paths=[f for d in ['compact-interface-repair','cylindrical-source-repack','source12-candidate'] for f in (B/d).rglob('*') if f.is_file()]
paths += [R/'.tools/checks/cylindrical-source-parent'/n for n in ['check.py','receipt.json','post-doc-integrity.json']]
paths += [R/'hardware/compact-dmx'/d/n for d in ['connector-interface-candidate','connector-mating-envelope'] for n in ['README.md','receipt.json']]
paths += [B/'regulated-source/sources/irm20.pdf',B/'stationary-irm20-integration/sources/meanwell-pcb-installation.pdf',B/'constant-length-mechanism/motion.json']
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
(P/'protected-inputs.json').write_text(json.dumps({str(f.relative_to(R)):h(f) for f in sorted(set(paths))},indent=2)+'\n')
(P/'parent-correction.json').write_text(json.dumps({'CYL_R1_receipt':h(B/'cylindrical-source-repack/receipt.json'),'expected_parent_document_change':json.loads((R/'.tools/checks/cylindrical-source-parent/post-doc-integrity.json').read_text()),'prior_manifest_not_modified':True,'comparison_correction':'Matched allowances; no numerical owner threshold','corridor_correction':'Full normal circular sections and BRep swept volumes, not radial centerline subtraction'},indent=2)+'\n')
print(len(set(paths)))
