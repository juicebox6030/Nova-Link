from pathlib import Path
import pcbnew as K,json,hashlib,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;EDA=P.parents[1];m=json.loads((P/'inputs.json').read_text());b=K.LoadBoard(str(P/'candidate.kicad_pcb'));old=K.LoadBoard(str(EDA/'placement-candidate/candidate.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};orig={f.GetReference():f for f in old.GetFootprints()}
def mm(v):return tuple(round(K.ToMM(x),6) for x in [v.x,v.y])
def signature(f):return sorted([(p.GetNumber(),mm(p.GetPosition()),mm(p.GetSize()),mm(p.GetDrillSize()),p.GetNetname(),int(p.GetLayer())) for p in f.Pads()])
assert set(fs)==set(orig)|{'J_USB','U2'}
for ref,f in orig.items():assert signature(fs[ref])==signature(f) and fs[ref].GetValue()==f.GetValue(),ref
f=K.FootprintLoad(str(P/'Candidate.pretty'),'GCT_USB4125_GF_A');pads=list(f.Pads());assert len(pads)==10
expected={'B12':(-2.75,.8),'B9':(-1.52,.76),'A5':(-.5,.7),'B5':(.5,.7),'A9':(1.52,.76),'A12':(2.75,.8)}
for p in pads:
 pin=p.GetNumber()
 if pin=='SH':assert mm(p.GetPosition()) in [(-4.32,0.),(4.32,0.),(-4.32,3.8),(4.32,3.8)];assert mm(p.GetSize())==(1.1,1.7) and mm(p.GetDrillSize())==(.6,1.2)
 else:x,w=expected[pin];assert mm(p.GetPosition())==(x,-.08) and mm(p.GetSize())==(w,1.2)
for ref,contract in m['contracts'].items():
 for p in fs[ref].Pads():
  if p.GetNumber():assert p.GetNetname()==contract[p.GetNumber()]
root=E.parse(EDA/'power-service/power-service.net');nodes={(n.get('ref'),n.get('pin')):net.get('name').lstrip('/') for net in root.findall('./nets/net') for n in net.findall('node')}
for ref in ['U2','J_USB']:
 for pin,net in m['contracts'][ref].items():
  if pin!='SH':assert nodes[ref,pin]==net,(ref,pin)
# All old pads/net semantics preserved; verify RF NC and critical DMX joins directly.
def net(ref,pin):return next(p.GetNetname() for p in fs[ref].Pads() if p.GetNumber()==str(pin))
for a,c in [(2,19),(4,18),(5,12)]:assert net('U5',a)==net('U1',c)
assert net('U5',3)!=net('U1',10) and net('U5',6)!=net('U5',11)
assert len({net('A101',i) for i in [2,3,5,6,7,8]})==6
conflicts=[];bounds={}
for ref,f in fs.items():
 if ref.startswith('H'):continue
 pts=[]
 for g in f.GraphicalItems():
  if g.GetLayer()==K.F_CrtYd:
   q=g.GetBoundingBox();pts += [(K.ToMM(q.GetX()),K.ToMM(q.GetY())),(K.ToMM(q.GetRight()),K.ToMM(q.GetBottom()))]
 box=[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)];bounds[ref]=box
 def intersects(r):return max(box[0],r[0])<min(box[2],r[2]) and max(box[1],r[1])<min(box[3],r[3])
 if intersects([26,23.5,61,37]):conflicts.append([ref,'cap'])
 if ref!='U5' and intersects([4,34.8,26,37.2]):conflicts.append([ref,'isolation'])
 if ref!='J_USB' and intersects([36.5,45.1,48.9,51]):conflicts.append([ref,'USB reserve'])
 if ref in ['U2','J_USB'] and intersects([83.4,23,94,51]):conflicts.append([ref,'antenna'])
 # Connector mating lip/courtyard may extend beyond edge; all copper DRC still applies.
 if ref!='J_USB' and (box[0]<4 or box[1]<23 or box[2]>94 or box[3]>51):conflicts.append([ref,'edge'])
assert not conflicts,conflicts
iso={net('U5',i) for i in range(11,21)}|{net('S_TERM',3)}
for ref,f in fs.items():
 if ref!='U5' and any(p.GetNetname() in iso for p in f.Pads()):assert bounds[ref][3]<34.8 and bounds[ref][2]<26,ref
assert len(b.GetTracks())==0
# Detect baseline board/NOR library mutation; export timestamp not a geometry dependency.
for path,digest in m['raw_sha256'].items():
 if not path.endswith('.net'):assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
for name,evidence in json.loads((P/'sources.json').read_text()).items():assert hashlib.sha256((P/'sources'/name).read_bytes()).hexdigest()==evidence['sha256'],name
d=json.loads((P/'drc.json').read_text());assert not d['violations']
r={'status':'PARTIAL_PROPOSED_PLACEMENT_PASS_NOT_RELEASED','kicad':K.GetBuildVersion(),'electrical_parts':39,'retained_parts':37,'baseline_pad_geometry_net_values_unchanged':True,'original_source_backed':36,'original_provisional_switch':1,'new_USB_electrical_pads':6,'shell_stakes':4,'new_NOR_pads':9,'geometric_DRC_violations':len(d['violations']),'unconnected_items':len(d['unconnected_items']),'spatial_conflicts':conflicts,'tracks':0,'bounds_mm':bounds,'qualified_1p5A_power_circuit_placed':False,'manufacturer_PCB_thickness_tolerance_verified':False}
(P/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='bounds_mm'},indent=2))
