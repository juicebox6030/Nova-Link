"""Verify the real CLI export, not generator-owned pin data. Circuit capture only."""
from pathlib import Path
import subprocess,json,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
cli=['flatpak','run','--command=kicad-cli','org.kicad.KiCad']
def run(*args):return subprocess.run(cli+list(args),check=True,capture_output=True,text=True).stdout.strip()
version=run('version');sch=str(P/'recovery-candidate.kicad_sch')
run('sch','export','netlist','--format','kicadxml','-o',str(P/'recovery-candidate.net'),sch)
run('sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(P/'erc.json'),sch)
run('sch','export','pdf','-o',str(P/'recovery-candidate.pdf'),sch)
run('sch','export','svg','-o',str(P/'rendered'),sch)
r=ET.parse(P/'recovery-candidate.net')
components={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')}
assert len(components)==31,len(components)
actual={};types={}
for net in r.findall('./nets/net'):
 name=net.attrib['name'].removeprefix('/')
 for node in net:
  pin=node.attrib['ref']+'.'+node.attrib['pin'];actual[pin]=name;types[pin]=node.attrib['pintype']
G='GND_USB'
expected={
'U101':{'A1':'VBUS','A2':None,'B1':'VBUS','B2':'BRIDGE_5V','C1':G,'C2':'BRIDGE_ILIM'},
'U102':{1:'BRIDGE_5V',2:G,3:'BRIDGE_5V',4:None,5:'BRIDGE_3V3'},
'U103':{1:None,2:None,3:G,4:'USB_DP',5:'USB_DM',6:'BRIDGE_3V3',7:'BRIDGE_3V3',8:'BRIDGE_3V3',9:'BRIDGE_RST_N',10:None,11:'USB_ACTIVE',12:G,13:'BRIDGE_3V3',14:None,15:G,16:None,17:'BRIDGE_RX',18:'BRIDGE_TX',19:None,20:None,21:G},
'U104':{1:'VBUS',2:G,3:'REC_EN',4:None,5:'REC_ILIM',6:'REC_5V'},
'U105':{1:'REC_5V',2:G,3:'REC_EN',4:None,5:'REC_3V3'},
'U106':{1:'USB_ACTIVE',2:'REC_REQUEST',3:'REC_EN',4:G,5:'REC_INTENT',6:'CONFIG_VERIFIED',7:'REC_INTENT',8:'BRIDGE_3V3'},
'U107':{1:G,2:'MCU_TX',3:G,4:'BRIDGE_RX',5:'BRIDGE_3V3'},
'U108':{1:G,2:'BRIDGE_TX',3:G,4:'MCU_RX',5:'MCU_3V3'},
'J101':{1:'VBUS',2:G,3:'USB_DP',4:'USB_DM'},
'J102':{1:'REC_3V3',2:G,3:'MCU_TX',4:'MCU_RX',5:'MCU_3V3'}}
for ref,a,b in [('R101','BRIDGE_ILIM',G),('R102','REC_ILIM',G),('R103','USB_ACTIVE',G),('R104','REC_REQUEST',G),('R105','REC_EN',G),('R106','BRIDGE_3V3','BRIDGE_RST_N'),('R107','MCU_TX',G),('R108','BRIDGE_TX',G),('R109','CONFIG_VERIFIED',G),('S102','BRIDGE_3V3','CONFIG_VERIFIED'),('S101','BRIDGE_3V3','REC_REQUEST')]:expected[ref]={1:a,2:b}
for i,n in enumerate(['VBUS','BRIDGE_5V','BRIDGE_5V','BRIDGE_3V3','BRIDGE_3V3','REC_5V','REC_3V3','BRIDGE_3V3','BRIDGE_3V3','MCU_3V3']):expected[f'C{101+i}']={1:n,2:G}
assert set(components)==set(expected)
for ref,pins in expected.items():
 for pin,net in pins.items():
  k=f'{ref}.{pin}'
  if net is None:assert actual.get(k,'unconnected-').startswith('unconnected-'),(k,actual.get(k))
  else:assert actual[k]==net,(k,actual[k],net)
# Electrical types independently checked for every implemented IC pin.
expecttypes={
'U101':['input','open_collector','power_in','power_out','power_in','output'],
'U102':['power_in','power_in','input','no_connect','power_out'],
'U103':['bidirectional','bidirectional','power_in','bidirectional','bidirectional','power_in','power_in','input','open_collector','no_connect','output','power_in','input','output','input','output','input','output','bidirectional','bidirectional','power_in'],
'U104':['power_in','power_in','input','open_collector','output','power_out'],
'U105':['power_in','power_in','input','no_connect','power_out'],
'U106':['input','input','output','power_in','input','input','output','power_in'],
'U107':['input','input','power_in','tri_state','power_in'],
'U108':['input','input','power_in','tri_state','power_in']}
for ref,ts in expecttypes.items():
 pins=list(expected[ref])
 for pin,t in zip(pins,ts):
  got=types.get(f'{ref}.{pin}')
  if got is not None:assert got.split('+')[0]==t,(ref,pin,t,got)
assert components['R101']=='19.2k 0.1%' and components['R102']=='88.7k 1%'
assert r.find("./components/comp[@ref='S102']/property[@name='dnp']") is not None
assert actual['U107.5']!=actual['U108.5'] # receiving-domain supplies
assert actual['J102.1']!=actual['J102.5'] # no fabricated normal/recovery merger
assert not any(k.startswith('#FLG') for k in actual)
erc=json.loads((P/'erc.json').read_text());v=[v for s in erc['sheets'] for v in s['violations']];assert not v,v
report={'capture_check':'PASS','product_power_acceptance':'NOT_MET','kicad_version':version,'components':len(components),'ICs':8,'boundary_connectors':2,'exported_nets':len(r.findall('./nets/net')),'erc_errors':0,'erc_warnings':0,'erc_exclusions':0,'all_component_pin_connections_checked':True,'IC_pin_types_checked':True,'power_flags':0,'scope':'USB recovery candidate only; normal path, CC, cap/UVLO latch, rail merger, BOOT/RESET sequencing not captured. Not an accepted product circuit.'}
(P/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
