"""Seal only this candidate; run after validate.sh. No protected-input writes."""
from pathlib import Path
import json,hashlib,subprocess,csv,datetime
P=Path(__file__).resolve().parent;root=P.parents[3];rel=str(P.relative_to(root));sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();read=lambda n:json.loads((P/n).read_text())
assert subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()=='main'
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='b42c0e6284aac734fde851c69146abf73920f337'
protected=read('protected-inputs.json');assert len(protected)==349 and all(sha(root/n)==h for n,h in protected.items())
sources=read('sources.json');assert len(sources)==14 and all(sha(root/s['path'])==s['sha256'] for s in sources)
drc=read('drc.json');erc=read('erc.json');route=read('routing-check.json');elec=read('electrical-check.json');cad=read('saved-CAD-check.json');preserved=read('preservation-check.json')
assert sum(len(s['violations']) for s in erc['sheets'])==0
assert not drc['unconnected_items'] and len(drc['violations'])==4 and all(v['type']=='hole_clearance' for v in drc['violations'])
assert route['saved_pad_net_checks']==127 and route['tracks']==582 and route['vias']==92 and route['endpoint_checks']==1164
assert cad['STEP_volume_agreement'] and cad['saved_zero_overlap_body_pairs']==561 and preserved['protected_current_matches']==349
assert read('land-check.json')['coordinate_dimension_checks']==57
ledger=list(csv.DictReader((P/'component-ledger.csv').open()));assert len([r for r in ledger if r['kind']=='purchased'])==32
# Remove local editor/FreeCAD backup and Python cache transients only, never protected inputs.
for f in P.rglob('*'):
 if f.is_file() and (f.suffix in ['.pyc','.kicad_prl','.FCBak'] or '.FCStd.' in f.name):f.unlink()
for f in sorted(P.rglob('__pycache__'),reverse=True):
 if not list(f.iterdir()):f.rmdir()
artifacts={str(f.relative_to(P)):sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name not in ['receipt.json','SHA256SUMS']}
commands=[line[2:] for line in (P/'validation.log').read_text().splitlines() if line.startswith(('+ python3 ','+ flatpak ','+ pdftoppm ','+ /home/juicebox/.local/bin/freecadcmd '))]
assert len(commands)>=20 and any('verify-envelopes.py' in c for c in commands)
r={
 'revision':'AXIAL-R1','date_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'repo_HEAD':head,'branch':'main',
 'status':'Complete routed prototype capture at27x20; compactness/process/function gates UNMET; no release',
 'owned_write_root':rel,'changed_paths':[rel+'/'+n for n in artifacts]+[rel+'/receipt.json',rel+'/SHA256SUMS'],
 'hardware_only':True,'no_install_children_hardware_firmware_outreach_or_git_publication':True,
 'circuit_deltas':route['circuit_delta'],'source_logic_limits_V':{'EN_VIL_max':.63,'EN_VIH_min':1.17,'actual_max_low':elec['startup']['PG_EN_max_low_V'],'actual_min_high':elec['startup']['PG_EN_min_high_V']},
 'DVDT_series':elec['DVDT_series'],'original_component_values_and_supplier_lands_preserved':True,
 'checks':{'ERC_violations':0,'DRC_new_violations':0,'DRC_total_violations':4,'known_GCT_NPTH_clearance_mm':[.1794,.2283],'DRC_exclusions_or_rule_relaxations_added':False,'unconnected':0,'IC_pin_checks':elec['IC_pin_checks'],'USB_terminal_checks':elec['USB_physical_terminal_checks'],'passive_checks':elec['resistor_checks']+elec['capacitor_checks'],'CC_PG_static_rows':len(elec['CC_state_rows']),'pads':127,'tracks':route['tracks'],'vias':route['vias'],'trace_endpoints':route['endpoint_checks'],'source_land_dimensions':57,'independent_foreign_track_clearance_min_mm':route['independent_track_to_track_foreign_net_clearance_min_mm'],'quiet_ground_stars_and_copper_voids':True,'D_short':route['USB_D_SHORT'],'CC_trace_lengths_mm':route['CC_total_trace_length_mm'],'reopened_CAD':cad},
 'physical':{'PCB_mm':[27,20,1],'25x18_target_achieved':False,'area_growth_percent':20,'smallest_supported_this_pass_not_global_minimum_proof':True,'purchased_parts':32,'fabricated_land_probe_footprints':2,'all_footprints':34,'original_purchased_parts':30,'original_footprints':32,'complete_courtyard_sum_mm2':route['complete_courtyard_sum_mm2'],'body_and_land_projection_mm2':route['physical_body_area_including_fabricated_lands_mm2'],'minimum_courtyard_gap_mm':read('placement-check.json')['minimum_courtyard_gap_mm'],'all_components_top':True,'port_datum':route['port_datum'],'local_frame':'X axial towardUSB; Y tangential; Z componentnormal; PCBZ-1..0','envelopes':read('envelope-check.json'),'parent_Astra_transform_and_collar_acceptance':False},
 'conditional_current_model_unchanged':{'efficiency_min_published':False,'actual_low_VIN_converter_current_deliverability_guaranteed':False,'worst':elec['input_model']['worst_case'],'conditional_port_voltage_window_V':elec['regulation']['conditional_port_window_V'],'new_copper_resistance_thermal_measured':False},
 'remaining_UNMET':['25x18board/bay target and wholecollar fit','supplier connector profile/matingface/stake/PCB-thickness/NPTH process','FPC clamp/coverlay/solder/strain/cycle qualification','70umouter/35uminner4layer1mm stack, plating, filled/plugged/tentedvias, RNMmask/stencil approval','healthy startup max current/timing, PG/loadstep/rebound behavior','hotinductor and actual lowVIN current deliverability, efficiency, filter ESR/loopstability','sealed module/regulator/FPC/contact thermal and line/temperature/derating','USB attach/detach/VCONN/discharge/ESD/contactsharing/compliance','input reverse transient/leakage publishedmaximum gaps','independent DCoutputOVP singlefault containment','upstream FPCshort stationaryI2t/faultcoordination','IRM20lead/carrier/harness/mains/endcap safety integration','XFL4020NRND prototype stock/lifecycle'],
 'validation_command':'bash '+rel+'/validate.sh > '+rel+'/validation.log 2>&1','validation_exit_code':0,'exact_executed_check_export_commands':commands,
 'independent_checker_imports':'No schematic generator, builder or router imported by literal/land/routing/reopenedCAD checkers',
 'protected_current_inputs_verified':len(protected),'protected_input_manifest_sha256':sha(P/'protected-inputs.json'),'preservation':preserved,
 'accepted_parent_deltas':['accepted-citation-metadata-delta.json','accepted-source-review-metadata-delta.json'],'frozen_original_review_modified':False,
 'primary_PDF_sources_with_current_hashes':sources,'artifact_hashes':artifacts,'artifact_count_excluding_receipt_inventory':len(artifacts),'manufacturing_release':False}
(P/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
files=sorted(f for f in P.rglob('*') if f.is_file() and f.name!='SHA256SUMS');(P/'SHA256SUMS').write_text(''.join(sha(f)+'  '+str(f.relative_to(P))+'\n' for f in files))
print(json.dumps({'artifact_hashes':len(artifacts),'inventory_entries_including_receipt':len(files),'receipt_sha256':sha(P/'receipt.json'),'inventory_sha256':sha(P/'SHA256SUMS'),'board_sha256':sha(P/'source-axial.kicad_pcb'),'protected_matches':len(protected)},indent=2))
