from pathlib import Path
import pcbnew as K,json,xml.etree.ElementTree as E,hashlib
P=Path(__file__).resolve().parent;L=P/'Service.pretty'
def mm(v):return tuple(round(K.ToMM(q),6) for q in (v.x,v.y))
def read(name):
 f=K.FootprintLoad(str(L),name);assert f;return f
n=read('AT25SF161B_MHB_Derived');u=read('CX70M_24P1_IntegrationCandidate')
np={p.GetNumber():p for p in n.Pads() if p.GetNumber()};assert set(np)==set(map(str,range(1,10)))
for i in range(4):
 for pin,x in [(i+1,-2.7),(8-i,2.7)]:
  p=np[str(pin)];assert mm(p.GetPosition())==(x,round(-1.905+1.27*i,6));assert mm(p.GetSize())==(1.2,.6)
assert mm(np['9'].GetSize())==(3.4,4.)
up={p.GetNumber():p for p in u.Pads() if p.GetNumber()!='SH' and p.GetNumber()};assert set(up)=={s+str(i) for s in 'AB' for i in range(1,13)}
order=['B12','B11','B10']+['A'+str(i) for i in range(1,13)]+['B3','B2','B1']
for i,pin in enumerate(order):
 p=up[pin];assert mm(p.GetPosition())==(round(-3.4+.4*i,6),-.925);assert mm(p.GetSize())==(.23,.85)
for i,pin in enumerate(['B9','B8','B7','B6','B5','B4']):
 p=up[pin];assert mm(p.GetPosition())==(round(-2+.8*i,6),0.);assert mm(p.GetDrillSize())==(.4,.4);assert mm(p.GetSize())==(.6,.6)
shell=[p for p in u.Pads() if p.GetNumber()=='SH'];assert len(shell)==8 # 6 attachments; 2 overlapping copper extensions
assert len([p for p in shell if p.GetAttribute()==K.PAD_ATTRIB_PTH])==4
for p in shell:
 if p.GetAttribute()==K.PAD_ATTRIB_PTH:assert mm(p.GetDrillSize())==(.6,1.7)
expected_shell={(-3.915,-.925), (3.915,-.925),(-5.55,-.45),(5.55,-.45),(-5.55,4.6),(5.55,4.6),(-5.3,4.6),(5.3,4.6)}
assert {mm(p.GetPosition()) for p in shell}==expected_shell
for p in shell:
 x,y=mm(p.GetPosition())
 assert mm(p.GetSize())==((.46,.85) if y==-.925 else (.9,2.3) if abs(x)==5.3 else (1.2,2.3))
for file,meta in json.loads((P/'sources.json').read_text()).items():assert hashlib.sha256((P/'sources'/file).read_bytes()).hexdigest()==meta['sha256']
path=P.parent/'power-service/power-service.net' ;root=E.parse(path).getroot();nodes={}
for net in root.findall('./nets/net'):
 for node in net.findall('node'):nodes[node.get('ref'),node.get('pin')]=net.get('name').lstrip('/')
nor={1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:'GND_USB',5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:'GND_USB'}
for pin,net in nor.items():assert nodes['U2',str(pin)]==net
assert {pin for ref,pin in nodes if ref=='J_USB'}==set(up)
for pin in up:
 target='GND_USB' if pin[1:] in ['1','12'] else 'VBUS_RAW' if pin[1:] in ['4','9'] else 'CC1' if pin=='A5' else 'CC2' if pin=='B5' else None
 if target:assert nodes['J_USB',pin]==target
 else:assert nodes['J_USB',pin].startswith('unconnected-')
# Confirm Rd components on each CC net; inspect source passives rather than infer USB behavior.
cc={}
for c in root.findall('./components/comp'):
 ref=c.get('ref');nets={v for (r,p),v in nodes.items() if r==ref}
 for pin in ['CC1','CC2']:
  if ref.startswith('R') and nets=={pin,'GND_USB'}:cc[pin]={'ref':ref,'value':c.findtext('value')}
assert set(cc)=={'CC1','CC2'} and all('5.1' in x['value'] for x in cc.values()),cc
r={'kicad':K.GetBuildVersion(),'parsed_footprints':2,'verified_electrical_pad_identifiers':33,'USB_contacts':24,'NOR_pads_including_local_EP9':9,'shell_physical_attachments':6,'shell_netlist_present':False,'USB_data_pads_NC':True,'CC_Rd':cc,'NOR_EP9_ground_matches_recommendation':True,'coordinate_checks_pass':True,'source_netlist_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'qualification':'UNPLACED_INTEGRATION_CANDIDATES_NOT_RELEASED','gates':['USB .8mm reference vs current1.0mm board; tolerance not supplied','USB shell circuit/ESD policy absent','USB paste corner shapes and mask/process allowances need manufacturing approval','NOR lands are engineering derivation from package, not manufacturer recommended lands','No product placement/height/access/DFM qualification']}
(P/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
