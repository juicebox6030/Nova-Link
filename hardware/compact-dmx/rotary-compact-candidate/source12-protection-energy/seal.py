"""Seal PE-R1 only; do not regenerate or modify any frozen sibling."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
report=json.loads((P/'numeric-check.json').read_text())
sources=json.loads((P/'sources.json').read_text())
for source in sources:assert sha(ROOT/source['path'])==source['sha256'],source['path']
protected=json.loads((P/'protected-inputs.json').read_text())
deltas=[]
for name,digest in protected.items():
 now=sha(ROOT/name) if (ROOT/name).is_file() else None
 if now!=digest:deltas.append({'path':name,'snapshot_sha256':digest,'current_sha256':now})
assert not any(x['path'].startswith('hardware/compact-dmx/rotary-compact-candidate/source12-candidate/') for x in deltas)
# The user explicitly identifies concurrent parent/Astra packaging work. Record
# its changing owned files, without accepting new hashes as preservation matches.
assert all(x['path']=='hardware/compact-dmx/README.md' or x['path'].startswith('hardware/compact-dmx/rotary-compact-candidate/combined-compact-allocation/') for x in deltas),deltas
(P/'external-deltas.json').write_text(json.dumps({'status':'Observed external changes; no baseline acceptance or refresh. This task did not write these files.','deltas':deltas},indent=2)+'\n')
files=sorted(f for f in P.rglob('*') if f.is_file() and f.name not in ['receipt.json','SHA256SUMS'] and '__pycache__' not in f.parts)
hashes={str(f.relative_to(P)):sha(f) for f in files}
receipt={
 'revision':'PE-R1','UTC':datetime.now(timezone.utc).isoformat(),'repo':'/home/juicebox/Nova-Link','HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
 'owned_writes':'hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/**',
 'verdict':report['verdict'],'scope_completed':'One bounded engineering screen of exactly two remedies; no independent review round, new regulator/module family search or circuit capture.',
 'capture_gate':'NOT MET: primary max bounds do not establish output-fault-energy improvement. New KiCad/netlist/ERC/lands/BOM capture intentionally not made. No new CLI electrical pass claimed.',
 'remedies':['LT4363IDE-1#PBF + CSD17577Q3A series clamp/current limiter, with U4 retained for true reverse blocking','TL431BIDBZR + TS820-600B-TR triggered crowbar, with U5/U4 shutdown retained; gate driver/coordination unqualified'],
 'numeric_evidence':{
  'latest_inherited_static_trip_V':5.476745480961925,'reference_C_F':120e-6,'reference_C_not_universal_minimum':True,
  'charge_to5p5_C':report['inherited_reference_window']['charge_to5p5_C'],'energy_to5p5_J':report['inherited_reference_window']['energy_to5p5_J'],'flat_assumed_current_deadline_s':report['inherited_reference_window']['flat_model_deadline_s'],
  'LT_ideal_gain_bounds_no_overlap':[report['remedies'][0]['ideal_gain_lower_for_no_nuisance'],report['remedies'][0]['ideal_gain_upper_for5p5']],
  'TLBI_ideal_gain_bounds_no_overlap':[report['remedies'][1]['ideal_gain_lower_for_no_nuisance'],report['remedies'][1]['ideal_gain_upper_for5p5']],
  'full_fault_current_max_A':None,'full_fault_isolation_max_s':None,'negative_regressions':report['negative_checks'],
  'scope':'Static rejection uses unchanged S12 healthy upper engineering allowance, not a newly guaranteed rail. Retuning/narrower justified temperature could alter DC result, but not create missing response/energy bounds.'},
 'missing_parameters':['Full-chain maximum sensing/drive/path-isolation or trigger-to-clamp delay at actual voltage, small overdrive, ramps and temperature','Maximum initial/continuing fault current, local/module stored capacitance and minimum source/loop impedance; no instantaneous U1/U4 limit assumed','Guaranteed effective Cmin and Cmax/ESR/ESL over life/bias/temperature; saturated L(I,T) and current at fault','Hot FET SOA/charge/feedthrough or SCR peak/di-dt/I2t/thermal coordination and maximum interruption time','Exact provisional100nF MPN/source qualification'],
 'finite_later_plan':'README numbered plan: DC/data gate first;324 electrical cases=3source x3temperature x3load x4timing x3fault,10repeats=3240shots. Separate input-GND short check. Characterize fixture and measurement uncertainty; no hardware performed or authorized by this receipt. Finite samples do not establish missing universal max bounds.',
 'actual_new_physical_parts':0,'actual_new_land_or_body_area_mm2':0,'actual_height_change_mm':0,'changed_board_dimensions':False,'zero_means_no_implemented_change_not_hypothetical_zero_cost':True,
 'S12_inventory_entries_verified':73,'S12_receipt_sha256':'51393c2a663f8cc206af64d4d0aa09d541832f1a5ac542f7a93bc06f95e2e519','all_S12_files_unchanged':True,
 'protected_snapshot_entries':len(protected),'protected_matches':len(protected)-len(deltas),'unaccepted_external_deltas':deltas,'preservation_baseline_refreshed':False,
 'source_artifacts':sources,'primary_source_access_limits':'ADI/ST official PDFs were read through primary web extraction; their cached excerpt hashes are not represented as full PDF hashes. Direct curl protocol errors/timeouts are in retrieval.json. TI PDFs and frozen primary PDFs are hashed normally.',
 'commands':['python3 hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/check.py > hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/check.log','python3 hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/seal.py','sha256sum -c hardware/compact-dmx/rotary-compact-candidate/source12-protection-energy/SHA256SUMS'],
 'artifact_hashes_excluding_receipt_and_inventory':hashes,'new_circuit_ERC':'N/A, no circuit changed or captured','hardware_measurements':False,'vendor_contact':False,'installs':False,'firmware':False,'routing':False,'children_or_reviews':False,'git_publication':False,'manufacturing_release':False}
(P/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(ROOT))+'\n' for f in sorted(files+[P/'receipt.json'])))
print(json.dumps({'revision':receipt['revision'],'verdict':'NOT ESTABLISHED; two remedies, no capture','inventory_files':len(files)+1,'sources':len(sources),'S12_inventory_pass':73,'protected_matches':receipt['protected_matches'],'protected_total':len(protected),'external_deltas':[x['path'] for x in deltas],'receipt_sha256':sha(P/'receipt.json'),'inventory_sha256':sha(P/'SHA256SUMS')},indent=2))
