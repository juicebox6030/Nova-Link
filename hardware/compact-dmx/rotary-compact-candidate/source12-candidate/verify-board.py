"""Reopen actual saved pads and assess actual DRC; no builder import."""
from pathlib import Path
import xml.etree.ElementTree as E,json,hashlib,collections
import pcbnew as K
P=Path(__file__).resolve().parent
t=E.parse(P/'source12.net');nodes={(p.attrib['ref'],p.attrib['pin']):net.attrib['name'].rsplit('/',1)[-1] for net in t.findall('./nets/net') for p in net}
reports=[];seen=[]
for zone in ['rotating','stationary']:
 b=K.LoadBoard(str(P/f'source12-{zone}.kicad_pcb'));checks=[]
 assert len(b.GetTracks())==0 and len(b.Zones())==0
 for f in b.GetFootprints():
  assert not f.IsFlipped()
  for pad in f.Pads():
   if not pad.GetNumber():continue
   key=(f.GetReference(),pad.GetNumber());assert key in nodes
   assert pad.GetNetname()==nodes[key],(key,pad.GetNetname(),nodes[key]);checks.append([*key,pad.GetNetname()]);seen.append(key)
  original=P/'Source12.pretty'/f'{f.GetFPID().GetLibItemName()}.kicad_mod'
  assert original.exists()
 d=json.loads((P/f'drc-{zone}.json').read_text());types=collections.Counter(x['type'] for x in d['violations'])
 # Supplier GCT B4 stakes/NPTH retain exactly four historical hole-clearance findings.
 # No global DRC weakening or exclusions; unrouted items are explicitly retained.
 other=[x for x in d['violations'] if x['type'] not in ['hole_clearance']]
 assert not other,other
 assert types.get('hole_clearance',0)==(4 if zone=='rotating' else 0),types
 if zone=='rotating':
  j=next(f for f in b.GetFootprints() if f.GetReference()=='J1')
  assert j.GetPosition()==K.VECTOR2I(K.FromMM(32),K.FromMM(13)) and j.GetOrientationDegrees()==90
  assert {p.GetNumber() for p in j.Pads() if p.GetNumber()}=={str(x) for x in ['A1_B12','A4_B9','B8','A5','B7','A6','A7','B6','A8','B5','B4_A9','B1_A12','S1','S2','S3','S4']}
 reports.append({'zone':zone,'all_saved_numbered_pad_checks':checks,'numbered_pad_count':len(checks),'DRC_violations_by_type':dict(types),'unconnected_items':len(d.get('unconnected_items',[])),'tracks':0,'vias':0,'routed':False})
assert set(seen)==set(nodes),(set(nodes)-set(seen))
result={'status':'PASS pad equivalence, no new geometric DRC; UNROUTED allocation only','saved_pad_checks':len(seen),'unique_exported_pad_nodes':len(nodes),'boards':reports,'known_GCT_hole_clearance_gate':'Four original primary-drawing NPTH/stake findings retained, no exclusions. Supplier process acceptance UNMET.'}
(P/'board-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({**{k:v for k,v in result.items() if k!='boards'},'boards':[{k:v for k,v in r.items() if k!='all_saved_numbered_pad_checks'} for r in reports]},indent=2))
