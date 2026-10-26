#!/usr/bin/env python3
"""Validate provenance and bounded HOLD contracts; never validate a mating pose by assumption."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];OLD=ROOT.parent/'connector-interface-candidate'
# ROOT=repo/hardware/compact-dmx/connector-mating-envelope
assert (REPO/'AGENTS.md').exists()
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((ROOT/'protected-inputs.json').read_text())
for p,h in protected.items():assert hashfile(REPO/p)==h,p
inherited=json.loads((OLD/'protected-inputs.json').read_text())['files']
deltas=[{'path':k,'CI_R1_sha256':v,'current_sha256':hashfile(REPO/k),'disposition':'Parent-owned canonical document differs from frozen CI-R1 expectation; not edited by this pass; no automatic baseline refresh.'} for k,v in inherited.items() if hashfile(REPO/k)!=v]
assert all(r['path']=='docs/hardware/DMX_Dongle_and_Power_Barrel.md' for r in deltas),deltas
(ROOT/'inherited-protection-status.json').write_text(json.dumps({'matches':len(inherited)-len(deltas),'total':len(inherited),'deltas':deltas},indent=2)+'\n')
assert hashfile(OLD/'receipt.json')=='58dd649c753c43b13ae55ac53ae8598ee6b020e4b91a6c35f7d42672c3014f5a'
sources=json.loads((ROOT/'source-links.json').read_text())['sources'];new=json.loads((ROOT/'new-source-manifest.json').read_text())
for root,items in [(OLD,sources),(ROOT,new)]:
 for r in items:
  assert hashfile(root/r['file'])==r['sha256'],r['file']
  assert r['url'].startswith('https://www.neutrik.com/')
assert len(sources)==28 and len(new)==4
contracts=json.loads((ROOT/'contracts.json').read_text());saved=json.loads((ROOT/'saved-reference-check.json').read_text())
assert contracts['accepted_installed_pairs']==0 and contracts['installed_length_claims']==0
expected=[('NAC3MPXXA','NAC3FXXA-W-S',30.4),('NAC3MPXXB','NAC3FXXB-W-S',30.4),('NAC3MPX-TOP','NAC3FX-W-TOP',31.2),('NAC3FPX-TOP','NAC3MX-W-TOP',32.8)]
for c,(a,b,rear) in zip(contracts['pairs'],expected):
 assert (c['chassis_part'],c['mate_part'],c['bare_chassis_rear_depth_drawing_mm'])==(a,b,rear)
 assert c['status']=='HOLD_NO_DEFENDED_INSTALLED_TRANSFORM'
 for field in ['accepted_rigid_mating_transform','installed_front_extent_from_panel_mm','installed_transverse_envelope_mm','installed_mating_plane','terminal_assembly_rear_depth_mm','finite_axial_translation_interval_mm','latch_stroke_envelope_mm','manufacturer_required_hand_clearance_mm','proposed_hand_clearance_mm']:assert c[field] is None,(a,field)
 assert not c['continuous_insertion_rotation_verified']
 for key,pn in [(c['chassis_model_key'],a),(c['mate_model_key'],b)]:
  page=(OLD/'sources'/(key+'.html')).read_text();assert pn.lower() in page.lower()
  sr=next(x for x in sources if x['file']=='sources/'+key+'.step')
  assert sr['url'].split('/download/')[1].split('?')[0].lower() in page.lower()
 for probe in c['surface_probes']:assert not probe['establishes_lock_or_stop']
 assert rear>24
assert len(saved['models_checked'])==8 and len(saved['isolated_face_probes'])==8
assert len([r for r in saved['models_checked'] if not r['valid_whole_shape']])==2
assert len([r for r in saved['models_checked'] if r['closed_solids']==0])==2
for r in saved['models_checked']:assert r['saved_placement_identity'] and r['same_topology_and_geometry_invariants'] and r['millimetre_STEP_unit']
assert saved['accepted_installed_poses']==0 and not saved['full_assembly_or_continuous_motion_verified']
for p in saved['isolated_face_probes']:assert not p['accepted_pose'] and not p['whole_model_boolean_performed']
probe=next(p for p in saved['isolated_face_probes'] if p['pair']=='pc-in' and p['chassis_face']=='Face466' and p['mate_face']=='Face247')
assert probe['face_common_area_mm2']<1e-8
# Manual pairing table is the independent mating-type check, not CAD filenames alone.
classic=(OLD/'sources/pc-cable-assembly.txt').read_text();true1=(OLD/'sources/true1-in-mount.txt').read_text()
for a,b,_ in expected[:2]:assert a in classic and b in classic
for a,b,_ in expected[2:]:assert a in true1 and b in true1
safety=(OLD/'sources/true1-safety.txt').read_text();assert all(w in safety for w in ['notch','clockwise','click'])
for key,colour in [('pc-in','blue'),('pc-out','grey')]:
 text=(OLD/'sources'/(key+'.txt')).read_text();assert 'Gender\nmale' in text and colour in text
assert not list(ROOT.rglob('*mated*.step')) and not list(ROOT.rglob('*mated*.FCStd'))
result={'revision':'CME-R1','status':'PASS_EVIDENCE_AND_HOLD_CONTRACTS_NOT_INSTALLED_FIT','protected_inputs_unchanged':len(protected),'CI_R1_inherited_protection_matches':len(inherited)-len(deltas),'CI_R1_inherited_protection_total':len(inherited),'CI_R1_inherited_doc_deltas':len(deltas),'reused_primary_sources':len(sources),'new_exact_mate_drawings':len(new),'saved_unplaced_models_checked':8,'isolated_plane_probes':8,'defended_installed_pairs':0,'unclosed_pairs':4,'bare_rear_depth_exceeds_24mm_pairs':4,'whole_model_invalid_count':2,'open_surface_model_count':2,'manufacturer_pairing_and_key_checks':True,'invented_installed_dimensions':0}
(ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
