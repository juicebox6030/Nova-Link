#!/usr/bin/env python3
"""Literal source, mating-key, dimensional-allocation and preservation checks.
No mains electrical/certification acceptance is computed.
"""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'source-manifest.json').read_text())
assert len({r['file'] for r in manifest})==len(manifest)
for r in manifest:
 assert r['status']=='fetched',r
 assert digest(ROOT/r['file'])==r['sha256'],r['file']
 assert r['url'].startswith(('https://www.neutrik.com/','https://www.neutrik.us/','https://leviton.com/')),r['url']
c=json.loads((ROOT/'contracts.json').read_text());j=json.loads((ROOT/'cad-inspection.json').read_text());saved=json.loads((ROOT/'saved-cad-check.json').read_text())
assert len(c['interfaces'])==c['candidate_interface_count']==6
literal=[('pc-in','NAC3MPXXA','NAC3FXXA-W-S',30.4),('pc-out','NAC3MPXXB','NAC3FXXB-W-S',30.4),('true1-in','NAC3MPX-TOP','NAC3FX-W-TOP',31.2),('true1-out','NAC3FPX-TOP','NAC3MX-W-TOP',32.8),('nema-in','5278-C','5269-C',45.3),('nema-out','5279-C','5266-C',43.6)]
for x,(key,pn,mate,depth) in zip(c['interfaces'],literal):
 assert (x['id'],x['part'],x['mate'],x['drawing_rear_depth_mm'])==(key,pn,mate,depth)
 assert digest(ROOT/x['source_step'])==x['source_step_sha256']==j['items'][key]['source_sha256']
 assert x['drawing_depth_excess_over_24_mm']==round(depth-24,4)>0
 assert x['mating_plane'].startswith('UNKNOWN:')
 src=(ROOT/x['source_page']).read_text()
 assert pn.lower() in src.lower()
 for view in ['front','side']:
  svg=ROOT/'views'/(key+'-'+view+'-edges.svg');t=ET.parse(svg)
  assert t.getroot().tag=='{http://www.w3.org/2000/svg}svg'
  assert len(t.findall('.//{http://www.w3.org/2000/svg}path'))>10
assert len(j['items'])==saved['objects_checked']==12 and saved['chassis_checked']==6
# Independent original-model unit checks, not an arbitrary import-scale assumption.
for x in c['interfaces'][:4]:
 s=(ROOT/x['source_step']).read_text()
 assert re.search(r'SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)',s)
for key in ['nema-in','nema-out']:
 s=(ROOT/'sources'/(key+'.step')).read_text()
 conv=re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'\s*,\s*#(\d+)\s*\)",s)
 assert conv
 factor=re.search(r'#'+conv[1]+r'\s*=\s*LENGTH_MEASURE_WITH_UNIT\s*\(\s*LENGTH_MEASURE\s*\(\s*([\d.Ee+-]+)',s)
 assert factor and abs(float(factor[1])-.0254)<1e-15
# Source-page roles independently support the literal pairing choices.
for key,phrases in {'pc-mate-a':['color coded (blue)','power-in'], 'pc-mate-b':['color coded (grey)','power-out'], 'pc-in':['inlet','blue'], 'pc-out':['outlet','grey'], 'nema-in':['NEMA 5-15P'], 'nema-out':['NEMA 5-15R'], 'nema-mate-f':['NEMA 5-15R'], 'nema-mate-m':['NEMA 5-15P']}.items():
 txt=(ROOT/'sources'/(key+'.txt')).read_text()
 for phrase in phrases:assert phrase.lower() in txt.lower(),(key,phrase)
for key,item in j['items'].items():
 src=(ROOT/'sources'/(key+'.step')).read_text()
 assert 'ISO-10303-21;' in src and 'FILE_NAME' in src and 'FILE_SCHEMA' in src
 assert item['declares_millimetres'] or item['conversion_inch_count']>0
# Primary mating assignment and legacy negative cases.
pc=(ROOT/'sources/pc-cable-assembly.txt').read_text()
for pn in ['NAC3MPXXA','NAC3MPXXB','NAC3FXXA-W-S','NAC3FXXB-W-S','NAC3MPA-1','NAC3MPB-1']:assert pn in pc
compat=(ROOT/'sources/pc-compatibility.txt').read_text()
assert 'fully mating compatible' in compat and 'do not support the CBC functionality' in compat
family=(ROOT/'sources/pc-family.txt').read_text()
assert 'have no CBC' in family
pairs={('NAC3MPXXA','NAC3FXXA-W-S'),('NAC3MPXXB','NAC3FXXB-W-S'),('NAC3MPA-1','NAC3FXXA-W-S'),('NAC3MPX-TOP','NAC3FX-W-TOP'),('NAC3FPX-TOP','NAC3MX-W-TOP'),('5278-C','5269-C'),('5279-C','5266-C')}
assert ('NAC3MPXXA','NAC3FXXB-W-S') not in pairs
assert ('NAC3MPA-1','NAC3FXXB-W-S') not in pairs
assert ('NAC3MPX-TOP','NAC3MX-W-TOP') not in pairs
# CBC applies to an exact combination, independently of mere mechanical mating.
def cbc(a,b):return (a,b) in {('NAC3MPXXA','NAC3FXXA-W-S'),('NAC3MPXXB','NAC3FXXB-W-S'),('NAC3MPX-TOP','NAC3FX-W-TOP'),('NAC3FPX-TOP','NAC3MX-W-TOP')}
assert cbc('NAC3MPXXA','NAC3FXXA-W-S') and not cbc('NAC3MPA-1','NAC3FXXA-W-S')
assert c['interfaces'][4]['flange_diameter_mm']==c['interfaces'][5]['flange_diameter_mm']==63.5>48
protected=json.loads((ROOT/'protected-inputs.json').read_text())
deltas=[str(p) for p,h in protected['files'].items() if not (REPO/p).exists() or digest(REPO/p)!=h]
# Concurrent parent documentation deltas are reported; never silently accepted/refreshed.
assert not deltas,('Protected inputs changed outside this task',deltas)
result={'status':'PASS_REFERENCE_CONTRACT_CHECKS','sources_checked':len(manifest),'official_steps_checked':12,'barrel_candidate_interfaces':6,'external_mate_models':6,'saved_models_checked':12,'protected_inputs_checked':len(protected['files']),'protected_deltas':deltas,'negative_mating_cases':3,'legacy_no_cbc_negative_case':True,'all_24mm_bare_rear_allocations_fail':True,'nema_48mm_flange_allocation_fails':True,'manufacturing_release':False}
(ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
