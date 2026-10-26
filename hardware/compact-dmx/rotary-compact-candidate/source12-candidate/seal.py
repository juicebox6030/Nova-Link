"""Seal only this candidate. Receipt does not recursively hash itself."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
protected=json.loads((P/'protected-inputs.json').read_text());deltas=[]
for name,digest in protected.items():
 current=sha(ROOT/name)
 if current!=digest:deltas.append({'path':name,'snapshot_sha256':digest,'current_sha256':current})
assert all(x['path']=='hardware/compact-dmx/README.md' for x in deltas),deltas
(P/'observed-external-deltas.json').write_text(json.dumps({'status':'UNACCEPTED external parent-owned documentation delta; preservation baseline NOT refreshed','deltas':deltas},indent=2)+'\n')
sources=json.loads((P/'sources.json').read_text())
for source in sources:assert sha(ROOT/source['path'])==source['sha256'],source['path']
e=json.loads((P/'electrical-check.json').read_text());b=json.loads((P/'board-check.json').read_text());place=json.loads((P/'placement-check.json').read_text())
assert e['manufacturing_release'] is False
excluded={'receipt.json','SHA256SUMS'}
files=sorted(f for f in P.rglob('*') if f.is_file() and f.name not in excluded and '__pycache__' not in f.parts and not f.name.endswith('.kicad_prl'))
hashes={str(f.relative_to(P)):sha(f) for f in files}
receipt={'revision':'S12-R1','created_UTC':datetime.now(timezone.utc).isoformat(),'repo':'/home/juicebox/Nova-Link','branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'owned_write_path':str(P.relative_to(ROOT))+'/**','disposition':'Captured partial prototype. Healthy static/conditional current screens PASS; independent maximum output fault surge/energy protection UNMET. Not a manufacturing release. No routing or old-board12V permission.',
 'architecture':'Stationary TPS259474L before FPC; rotating TPS62135 forcedPWM5.18V; independent TPS3700 window controls TPS25940L output disconnector before TPS25810 fixed1.5A/full USB4105.',
 'regulators_screened':['TPS62130 (not captured)','TPS62135RGXR (only captured buck)'],'source_bus':'Isolated12V development; IRM20-12 pod allocation only. External USB stays5V>=1.5A.',
 'commands':['bash hardware/compact-dmx/rotary-compact-candidate/source12-candidate/validate.sh','python3 hardware/compact-dmx/rotary-compact-candidate/source12-candidate/seal.py','sha256sum -c hardware/compact-dmx/rotary-compact-candidate/source12-candidate/SHA256SUMS (run from repository root)'],
 'tool_versions':{'KiCad':'10.0.7 flatpak org.kicad.KiCad','Python':'existing system3 / existing flatpak pcbnew','installs':False},
 'checks':{'ERC_violations':0,'literal_IC_pins_nets_types':e['IC_pins_literal'],'physical_components':57,'purchased_components':52,'resistor_pairs':27,'capacitor_pairs':17,'unique_exported_pad_nodes':185,'all_saved_numbered_pad_checks':b['saved_pad_checks'],'state_rows':len(e['state_rows']),'CC_rows':len(e['CC_rows']),'negative_tests':e['negative_tests'],'input_current_corners':len(e['current_paths']['corners']),'DRC':[{'zone':x['zone'],'geometric_violations_by_type':x['DRC_violations_by_type'],'unconnected_items':x['unconnected_items'],'tracks':x['tracks'],'vias':x['vias']} for x in b['boards']]},
 'conditional_numbers':{'port_V':e['regulation']['conditional_port_V'],'OV_trip_V':e['thresholds_V']['buck_OV_rise'],'healthy_to_OV_margin_V':e['regulation']['conditional_OVP_nonnuisance_margin_V'],'normal_output_stress_A':1.920,'VBUS_limit_output_stress_A':2.240,'source_breaker_formula_A':e['current_paths']['source_breaker_formula_A'],'worst_input_model':e['current_paths']['worst'],'output_energy_counterexample':e['output_fault_energy'],'assumptions':'80% efficiency is engineering assumption, not guaranteed minimum. Includes410mA VCONN limit stress,10mA output/2mA input auxiliary,50mV rail allowance,PCB/connector R,hot FPC+fanout/wire. See DESIGN for bias/current-test/timing applicability.'},
 'placement':place,'additional_BOM_gate':'Inherited TMK105B7104MV-FR100nF is explicitly provisional: official current lookup renamed-to-null, exact orderability/specification unresolved. No qualified-MPN assertion.',
 'manufacturing_gates':e['gates']+['Exact100nF MPN qualification/source record unresolved'],
 'protected_snapshot_files':len(protected),'protected_matches':len(protected)-len(deltas),'unaccepted_external_deltas':deltas,'protected_baseline_refreshed':False,'source_artifacts':sources,'current_artifact_count_excluding_receipt_inventory':len(hashes),'current_artifacts_sha256':hashes,'modified_existing_task_inputs':False,'hardware_measurements':False,'firmware_work':False,'git_publication':False,'manufacturing_release':False}
(P/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
inventory=files+[P/'receipt.json']
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(ROOT))+'\n' for f in sorted(inventory)))
print(json.dumps({'revision':receipt['revision'],'artifacts_hashed_including_receipt':len(inventory),'source_artifacts':len(sources),'protected_matches':receipt['protected_matches'],'external_deltas':len(deltas),'receipt_sha256':sha(P/'receipt.json'),'inventory_sha256':sha(P/'SHA256SUMS'),'disposition':receipt['disposition']},indent=2))
