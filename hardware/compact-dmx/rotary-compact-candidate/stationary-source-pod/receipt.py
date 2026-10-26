from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;root=P.parents[3];h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[]
for rel,url,page,basis in [
 ('hardware/compact-dmx/rotary-compact-candidate/regulated-source/sources/irm20.pdf','https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF','p3;2025-11-21','52.4x27.2x24 nominal,+/-.5;3.5+/-1 projection; parent selects12V variant'),
 ('hardware/compact-dmx/rotary-compact-candidate/stationary-irm20-integration/sources/meanwell-pcb-installation.pdf','https://www.meanwell.com/Upload/PDF/IRM-01/PCB.pdf','p1 Installation2','5mm bottom plusMylar;10mm general surrounding; source does not approve this carrier/support construction'),
 ('hardware/compact-dmx/rotary-compact-candidate/regulated-source/sources/irm20-mechanical.png',None,'Existing primaryPDF page rendering, visually inspected','No pixel-scaled dimensions; all nominal/tolerance numbers from labeled manufacturer drawing'),
 ('hardware/compact-dmx/rotary-compact-candidate/stationary-irm20-integration/installation-gate/receipt.json',None,'Frozen parentaccepted construction gate','IRM20/43IDproductionBLOCKED; not superseded by this allocation')]:sources.append({'path':rel,'sha256':h(root/rel),'url':url,'page':page,'basis':basis})
(P/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
for p in P.glob('*.FCBak'):p.unlink()
if (P/'__pycache__').exists():shutil.rmtree(P/'__pycache__')
c=json.loads((P/'checks.json').read_text());assert c['status']=='PASS allocation screens' and not c['spacing_failures']
art={str(p.relative_to(P)):h(p) for p in P.rglob('*') if p.is_file() and p.name not in ['receipt.json','receipt-check.log']}
r={'status':'One conditional stationary allocation completed; compactness and mains construction NOT accepted','head':'b42c0e6284aac734fde851c69146abf73920f337','owned_path':str(P.relative_to(root)),'artifacts':art,'protected_inputs':len(json.loads((P/'protected-inputs.json').read_text())),'source_files':len(sources),'product_envelope_mm':c['whole_product_planning_dimensions'],'pod_shell_mm':[128,82,62],'source_reservation_mm':[81,52,44],'native_closed_connected_solids':len(c['native_valid']),'STEP':c['STEP'],'spacing_checks':c['spacing_checks'],'physical_allocation_pairs':c['physical_pairs'],'USB_motion_positions':c['motion_positions'],'USB_motion_checks':c['USB_motion_checks'],'detents':c['detents'],'USB_min_screen_gap_mm':c['USB_min_stationary_gap'],'unchanged_sidecar':'protected25-placement entire output folder included in protected-inputs.json','not_consumed':'source12-candidate unfinished files; old5V board is spatial comparison ONLY','remaining_gates':c['not_complete_construction'],'commands':['FreeCAD1.1.3 offscreen build.py','FreeCAD1.1.3 offscreen run_check.py (real nonzero exit on failed assertion)','python3 draw.py','pdftoppm -scale-to 1400 -png allocation-sections.pdf preview; bothpages visually inspected','python3 verify_receipt.py'],'publication':'None; allprioroutputs frozen'}
(P/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('ARTIFACTS',len(art),'PROTECTED',r['protected_inputs'],'SOURCES',len(sources))
