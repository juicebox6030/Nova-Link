"""Run with existing Flatpak KiCad Python; checks real parsed pads, no synthetic acceptance."""
from pathlib import Path
import pcbnew as K,json,hashlib,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;L=P/'NOVA_HW.pretty'
power_source=P.parent/'power-service/power-service.kicad_sch';power_at_check_start=hashlib.sha256(power_source.read_bytes()).hexdigest()
def load(n):
 f=K.FootprintLoad(str(L),n);assert f is not None,n
 return f

def pads(n):return {p.GetNumber():p for p in load(n).Pads() if p.GetNumber()}
def xy(v):return (round(K.ToMM(v.x),5),round(K.ToMM(v.y),5))
def check(p,n,pos,size):
 assert xy(p[n].GetPosition())==pos,(n,xy(p[n].GetPosition()),pos)
 assert xy(p[n].GetSize())==size,(n,xy(p[n].GetSize()),size)
f=pads('TI_DFM0020A');assert set(f)==set(map(str,range(1,21)))
for i in range(1,11):check(f,str(i),(-4.85,round((i-5.5)*1.27,5)),(2.1,.6))
for i in range(11,21):check(f,str(i),(4.85,round((15.5-i)*1.27,5)),(2.1,.6))
f=pads('TI_RGZ0048A');assert set(f)==set(map(str,range(1,50)));check(f,'49',(0.,0.),(5.15,5.15))
for i in range(12):
 a=round(-2.75+i*.5,5)
 for n,pos,size in [(i+1,(-3.4,a),(.6,.24)),(i+13,(a,3.4),(.24,.6)),(i+25,(3.4,-a),(.6,.24)),(i+37,(-a,-3.4),(.24,.6))]:check(f,str(n),pos,size)
assert len([p for p in load('TI_RGZ0048A').Pads() if not p.GetNumber()])==16
f=pads('Johanson_0900AD47_IsolatedLands');assert set(f)==set(map(str,range(1,9)))
for i,x in enumerate([-4.4,-.9,.9,4.4]):
 check(f,str(i+1),(x,1.3),(1.,1.));check(f,str(8-i),(x,-1.3),(1.,1.))
# All8 distinct copper pads;6 NC islands have no interconnecting copper primitive.
a=load('Johanson_0900AD47_IsolatedLands');assert len(list(a.Zones()))==1
assert not any(d.GetLayer() in [K.F_Cu,K.B_Cu] for d in a.GraphicalItems())
f=pads('Vishay_CRCW1206');check(f,'1',(-1.275,0.),(1.05,1.8));check(f,'2',(1.275,0.),(1.05,1.8))
load('PCM12_PENDING_MANUFACTURER_LAND_RECHECK') # parser only, not dimensions accepted
# Verify assigned values from actual CLI net exports.
assign={}
for sheet in [P.parent/'dmx-interface.net',P.parent/'mcu-radio/mcu-radio.net']:
 for c in E.parse(sheet).findall('./components/comp'):
  fp=c.findtext('footprint')
  if fp:assign[c.attrib['ref']]=fp
for ref,name in {'U5':'TI_DFM0020A','U1':'TI_RGZ0048A','A101':'Johanson_0900AD47_IsolatedLands','R_TERM1':'Vishay_CRCW1206','R_TERM2':'Vishay_CRCW1206','S_TERM':'PCM12_PENDING_MANUFACTURER_LAND_RECHECK'}.items():assert assign[ref]=='NOVA_HW:'+name
# Independent numeric expectations: TI Gerber/PnP transcription, not generator imports.
vector_expected={
'TI_IPC1352_Vector':{str(i):v for i,v in enumerate([(.75,-.78,.25,.8),(.25,-.78,.25,.8),(-.25,-.78,.25,.8),(-.75,-.78,.25,.8),(-1.155,0,.8,.35),(-.75,.78,.25,.8),(-.25,.78,.25,.8),(.25,.78,.25,.8),(.75,.78,.25,.8),(1.155,0,.8,.35)],1)},
'TI_CAPC1005_Vector':{'1':(-.462,0,.524,.5),'2':(.462,0,.524,.5)},
'TI_CAPC1608_Vector':{'1':(-.7,0,.75,.9),'2':(.7,0,.75,.9)},
'TI_CAPC0603_Vector':{'1':(-.28,0,.35,.4),'2':(.28,0,.35,.4)},
'TI_BLM18_Vector':{'1':(-.7,0,.75,.9),'2':(.7,0,.75,.9)},
'TI_MLZ2012_Vector':{'1':(-.9,0,1.15,1.45),'2':(.9,0,1.15,1.45)}}
for name,expected in vector_expected.items():
 f=pads(name);assert set(f)==set(expected)
 for pin,(x,y,w,h) in expected.items():
  assert xy(f[pin].GetPosition())==(x,y)
  box=f[pin].GetBoundingBox();assert abs(K.ToMM(box.GetWidth())-w)<1e-5 and abs(K.ToMM(box.GetHeight())-h)<1e-5
  assert f[pin].GetShape()==K.PAD_SHAPE_CUSTOM
 # Every numbered Cu/paste island also has its independently shaped mask opening.
 assert len([p for p in load(name).Pads() if not p.GetNumber()])==len(expected)
f=pads('Epson_FC135_Manufacturer');check(f,'1',(-1.25,0.),(1.,1.8));check(f,'2',(1.25,0.),(1.,1.8))
f=pads('NDK_NX2016SA_Manufacturer')
for pin,pos in {'1':(-.675,.525),'2':(.675,.525),'3':(.675,-.525),'4':(-.675,-.525)}.items():check(f,pin,pos,(.85,.75))
f=pads('Vishay_CRCW0402');check(f,'1',(-.525,0.),(.6,.6));check(f,'2',(.525,0.),(.6,.6))
f=pads('Murata_GRM21_Reflow');check(f,'1',(-.95,0.),(.7,1.3));check(f,'2',(.95,0.),(.7,1.3))

for name,x,w,h in [('Coilcraft_0402HP_Manufacturer',.435,.36,.66),('Murata_GJM155_Manufacturer',.4,.4,.5)]:
 f=pads(name);assert set(f)=={'1','2'};check(f,'1',(-x,0.),(w,h));check(f,'2',(x,0.),(w,h))

# Exhaustive per-sheet physical assignment and actual MPN value checks against exports.
contract=json.loads((P/'assignments.json').read_text());seen={};physical=0
for sheet,path,boundaries in [('dmx',P.parent/'dmx-interface.net',{'X1','J1'}),('mcu-radio',P.parent/'mcu-radio/mcu-radio.net',{'X101'})]:
 root=E.parse(path)
 for c in root.findall('./components/comp'):
  ref=c.attrib['ref']
  if ref in boundaries:continue
  key=sheet+'.'+ref;expected=contract[key];fp=c.findtext('footprint');assert fp=='NOVA_HW:'+expected['footprint'],key
  assert c.findtext('value')==expected['value'],key
  footprint=load(expected['footprint']);fp_numbers={pad.GetNumber() for pad in footprint.Pads() if pad.GetNumber()}
  net_pins={node.attrib['pin'] for net in root.findall('./nets/net') for node in net if node.attrib['ref']==ref}
  assert fp_numbers==net_pins,(key,fp_numbers,net_pins)
  seen[key]=expected;physical+=1
assert physical==37 and set(seen)==set(contract)
# Source input hashes are checked against extracted-vector evidence before accepting derived lands.
vector=json.loads((P/'ti-vector-lands.json').read_text())
for path,sha in vector['source_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
for path,evidence in json.loads((P/'replacement-source-evidence.json').read_text()).items():
 assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==evidence['sha256'],path
before=json.loads((P/'input-hashes.json').read_text());after={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in before}
power=next(f for f in before if 'power-service' in f);assert power_at_check_start==after[power],'Concurrent power mutation DURING footprint check'
provisional=[k for k,v in contract.items() if not v['status'].startswith('SOURCE_DIMENSIONED')]
r={'status':'ALL_PHYSICAL_ASSIGNMENTS_CHECKED_ONE_SWITCH_DATUM_GATE','kicad_version':K.GetBuildVersion(),'parsed_footprints':17,'dimension_checked_footprints':16,'numbered_pads_dimension_checked':113,'physical_component_assignments':physical,'source_backed_assignments':physical-len(provisional),'provisional_assignments':provisional,'all_actual_export_pad_numbers_match':True,'power_input_unchanged':before[power]==after[power],'power_unchanged_during_check':True,'before_sha256':before,'after_sha256':after,'remaining_gates':['PCM12 mounting-row-to-locator vertical datum and known pad gap mismatch','Replacement RF parasitics/SRF at band and assembly qualification','Custom crystal electrical suffix procurement/qualification; layout and thermal-via implementation'],'full_footprint_acceptance':False,'PCB_DRC_or_routing_claim':False}
(P/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
