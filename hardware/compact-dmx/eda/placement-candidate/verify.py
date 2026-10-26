#!/usr/bin/env python3
import pcbnew as K, pathlib,json,xml.etree.ElementTree as E,hashlib,collections
D=pathlib.Path(__file__).resolve().parent;eda=D.parent;b=K.LoadBoard(str(D/'candidate.kicad_pcb')); manifest=json.loads((D/'inputs.json').read_text());assign=json.loads((eda/'footprints/assignments.json').read_text());fps={f.GetReference():f for f in b.GetFootprints()}; checked=0
# Independently reconstruct source connectivity, not a comparison with generator's expected map.
alias={'DMX_TX':'MCU_DMX_TX','DMX_RX':'MCU_DMX_RX','DMX_RE_N':'MCU_RE_N'}
for sheet,file in [('dmx','dmx-interface.net'),('mcu-radio','mcu-radio/mcu-radio.net')]:
 root=E.parse(eda/file).getroot();expected={}
 for n in root.findall('./nets/net'):
  raw=n.get('name').lstrip('/'); name=alias.get(raw,raw)
  if name.startswith('unconnected-'):name=sheet+'_'+name
  for p in n.findall('node'):expected[p.get('ref'),p.get('pin')]=name
 for key,a in assign.items():
  if not key.startswith(sheet+'.'):continue
  ref=key.split('.')[-1];fp=fps[ref]
  component=root.find("./components/comp[@ref='"+ref+"']")
  assert fp.GetValue()==component.findtext('value')==a['value'],(ref,'value')
  assert component.findtext('footprint')=='NOVA_HW:'+a['footprint'],(ref,'footprint assignment')
  assert str(fp.GetFPID().GetLibItemName())==a['footprint'],(ref,'actual board footprint')
  actual={p.GetNumber():p.GetNetname() for p in fp.Pads() if p.GetNumber()}
  wanted={pin:net for (r,pin),net in expected.items() if r==ref}
  assert actual==wanted,(ref,actual,wanted);checked+=len(actual)
assert len(fps)==41 and len(assign)==37
assert len({p.GetNetname() for p in fps['A101'].Pads() if p.GetNumber() in ['2','3','5','6','7','8']})==6
assert len(b.GetTracks())==0
# Actual-board semantic checks independent of the export-name transformation above.
def net(ref,pin):
 return next(p.GetNetname() for p in fps[ref].Pads() if p.GetNumber()==str(pin))
semantic_pairs=[('U5',2,'U1',19),('U5',4,'U1',18),('U5',5,'U1',12)]
for a,p,c,q in semantic_pairs: assert net(a,p)==net(c,q),(a,p,c,q)
assert net('U5',3)!=net('U1',10), 'DE gate bypassed'
assert net('R4',1)!=net('U1',11) and net('R4',2)!=net('U1',11), 'Power gate bypassed'
assert net('U5',6)!=net('U5',11), 'Isolation grounds shorted' 
# Conservative courtyard AABBs against physical reserves; no use of silk/body instead of courtyard.
reserves={'USB_slot':[36.5,45.1,48.9,51], 'cap_and_leads':[26,23.5,61,37]}; conflicts=[]; boxes={}
for ref,f in fps.items():
 if ref.startswith('H'):continue
 points=[]
 for g in f.GraphicalItems():
  if g.GetLayer()==K.F_CrtYd:
   bb=g.GetBoundingBox();points.extend([(K.ToMM(bb.GetX()),K.ToMM(bb.GetY())),(K.ToMM(bb.GetRight()),K.ToMM(bb.GetBottom()))])
 assert points,ref
 box=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)];boxes[ref]=box
 if box[0]<4 or box[1]<23 or box[2]>94 or box[3]>51:conflicts.append([ref,'courtyard_off_board',box])
 for name,r in reserves.items():
  if max(box[0],r[0])<min(box[2],r[2]) and max(box[1],r[1])<min(box[3],r[3]):conflicts.append([ref,name])
# Pin-domain spatial sanity around rotated isolator, not a certified creepage test.
u=fps['U5'];p={x.GetNumber():x for x in u.Pads()};assert all(K.ToMM(p[str(n)].GetPosition().y)>37.2 for n in range(1,11));assert all(K.ToMM(p[str(n)].GetPosition().y)<34.8 for n in range(11,21))
# Every non-bridge courtyard must avoid the corridor. All isolated-net parts
# must remain wholly on its isolated side, including mechanical switch lands.
iso_nets={net('U5',n) for n in range(11,21)}|{net('S_TERM',3)}
isolated_refs=[]
for ref,box in boxes.items():
 if ref=='U5':continue
 if max(box[0],4)<min(box[2],26) and max(box[1],34.8)<min(box[3],37.2):conflicts.append([ref,'isolation_corridor'])
 if any(p.GetNetname() in iso_nets for p in fps[ref].Pads() if p.GetNumber()):
  isolated_refs.append(ref)
  if box[3]>=34.8 or box[0]<4 or box[2]>26:conflicts.append([ref,'isolated_domain_outside_region'])
assert set(isolated_refs)=={'C3','C4','R_TERM1','R_TERM2','S_TERM'},isolated_refs
def stable_export(data):
 root=E.fromstring(data);date=root.find('./design/date')
 if date is not None:date.text=None
 return hashlib.sha256(E.tostring(root,encoding='utf-8')).hexdigest()
mutations=[]; raw_export_differences=[]
for name,digest in manifest['sha256'].items():
 data=(eda/name).read_bytes();raw=hashlib.sha256(data).hexdigest()
 if name in manifest['stable_export_sha256']:
  if raw!=digest:raw_export_differences.append(name)
  if stable_export(data)!=manifest['stable_export_sha256'][name]:mutations.append(name)
 elif raw!=digest:mutations.append(name)
# Bounded in-memory regression: timestamp-only tolerated; all electrical and
# other metadata changes rejected. Active source files are never mutated.
fingerprint_tests={}
for name in manifest['stable_export_sha256']:
 data=(eda/name).read_bytes();baseline=stable_export(data)
 root=E.fromstring(data);root.find('./design/date').text='2099-01-01T00:00:00'
 assert stable_export(E.tostring(root))==baseline
 for label,xpath,attr in [('value','./components/comp/value',None),('footprint','./components/comp/footprint',None),('net_name','./nets/net','name'),('pin','./nets/net/node','pin'),('pintype','./nets/net/node','pintype'),('other_metadata','./design/tool',None)]:
  root=E.fromstring(data);node=root.find(xpath);assert node is not None,(name,label)
  if attr:node.set(attr,node.get(attr,'')+'_MUTATION')
  else:node.text=(node.text or '')+'_MUTATION'
  assert stable_export(E.tostring(root))!=baseline,(name,label)
 fingerprint_tests[name]='date-only accepted; value/footprint/net/pin/pintype/other metadata changes rejected'

drc=json.loads((D/'drc.json').read_text());result={'physical_components':37,'mechanical_holes':4,'checked_numbered_pads':checked,'nets':len({p.GetNetname() for f in fps.values() for p in f.Pads() if p.GetNumber()}),'six_antenna_NC_islands_distinct':True,'source_hash_mutations':mutations,'raw_export_hash_differences':raw_export_differences,'stable_fingerprint_tests':fingerprint_tests,'reserve_or_edge_conflicts':conflicts,'courtyard_bounds_mm':boxes,'drc_violations':len(drc['violations']),'unconnected_items':len(drc['unconnected_items']),'semantic_TX_RX_RE_pairs':semantic_pairs,'isolated_component_refs':sorted(isolated_refs),'tracks':0,'status':'PARTIAL_PLACEMENT_ONLY'}
(D/'validation.json').write_text(json.dumps(result,indent=2)+'\n');assert not conflicts,conflicts;assert not mutations,mutations;assert not drc['violations'];print(json.dumps({k:v for k,v in result.items() if k!='courtyard_bounds_mm'},indent=2))
