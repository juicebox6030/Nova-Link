"""Independent MCU/support/frontend and exported cross-sheet net contract.
PASS is scoped circuit capture; antenna, PCB and qualification remain open.
"""
from pathlib import Path
import subprocess,json,xml.etree.ElementTree as E,hashlib
P=Path(__file__).resolve().parent;CLI=['flatpak','run','--command=kicad-cli','org.kicad.KiCad']
def cli(*args):
 p=subprocess.run(CLI+list(args),check=True,text=True,capture_output=True)
 return p.stdout.strip(),p.stderr.strip()
version=cli('version')[0];log=[]
for args in [('sch','export','netlist','--format','kicadxml','-o',str(P/'mcu-radio.net'),str(P/'mcu-radio.kicad_sch')),('sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(P/'erc.json'),str(P/'mcu-radio.kicad_sch')),('sch','export','pdf','-o',str(P/'mcu-radio.pdf'),str(P/'mcu-radio.kicad_sch')),('sch','export','svg','-o',str(P/'rendered'),str(P/'mcu-radio.kicad_sch'))]:log.append({'args':args,'output':cli(*args)})
def read(path):
 r=E.parse(path);nodes={};types={};names={}
 for n in r.findall('./nets/net'):
  for x in n:
   k=(x.attrib['ref'],x.attrib['pin']);nodes[k]=n.attrib['name'].removeprefix('/');types[k]=x.attrib['pintype'];names[k]=x.attrib.get('pinfunction')
 return r,nodes,types,names
r,m,t,n=read(P/'mcu-radio.net');assert len(r.findall('./components/comp'))==24
# Independent transcription SWRS196I Table7-1, not imported from generator.
physical={1:'RF_P_2_4GHZ',2:'RF_N_2_4GHZ',3:'RF_P_SUB_1GHZ',4:'RF_N_SUB_1GHZ',5:'RX_TX',6:'X32K_Q1',7:'X32K_Q2',8:'DIO_3',9:'DIO_4',10:'DIO_5',11:'DIO_6',12:'DIO_7',13:'VDDS2',14:'DIO_8',15:'DIO_9',16:'DIO_10',17:'DIO_11',18:'DIO_12',19:'DIO_13',20:'DIO_14',21:'DIO_15',22:'VDDS3',23:'DCOUPL',24:'JTAG_TMSC',25:'JTAG_TCKC',26:'DIO_16',27:'DIO_17',28:'DIO_18',29:'DIO_19',30:'DIO_20',31:'DIO_21',32:'DIO_22',33:'DCDC_SW',34:'VDDS_DCDC',35:'RESET_N',36:'DIO_23',37:'DIO_24',38:'DIO_25',39:'DIO_26',40:'DIO_27',41:'DIO_28',42:'DIO_29',43:'DIO_30',44:'VDDS',45:'VDDR',46:'X48M_N',47:'X48M_P',48:'VDDR_RF',49:'EGP'}
for p,name in physical.items():assert n['U1',str(p)] in (name,name+'_'+str(p)),(p,n['U1',str(p)])
expected={8:'ROM_BOOT_STRAP',9:'SERVICE_N_DISTINCT_GPIO',10:'MCU_DE_REQUEST',11:'MCU_ISO_REQUEST',12:'MCU_RE_N',14:'SPI_MISO',15:'SPI_MOSI',16:'SPI_SCK',17:'SPI_CS_N',18:'MCU_DMX_RX',19:'MCU_DMX_TX',20:'VBUS_GOOD_3V3',21:'BUCK_PG',24:'TMSC',25:'TCKC',35:'RESET_OK',13:'MCU_VDDS',22:'MCU_VDDS',34:'MCU_VDDS',44:'MCU_VDDS',49:'GND_USB',45:'MCU_VDDR',48:'MCU_VDDR'}
for p,net in expected.items():assert m['U1',str(p)]==net,(p,net)
for p in [8,9,14,18,20,21,25,35]:assert t['U1',str(p)]=='input'
for p in [10,11,12,15,16,17,19,43]:assert t['U1',str(p)]=='output'
assert m['U1','8']!=m['U1','9']
# Export read-only snapshots into our directory; never mutate another sheet owner's artifacts.
inputs=P/'integration-inputs';inputs.mkdir(exist_ok=True)
source_hashes={}
for label,source in [('power',P.parent/'power-service/power-service.kicad_sch'),('dmx',P.parent/'dmx-interface.kicad_sch')]:
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 cli('sch','export','netlist','--format','kicadxml','-o',str(inputs/(label+'.net')),str(source))
 assert before==hashlib.sha256(source.read_bytes()).hexdigest(),'Concurrent source mutation; rerun after owner finishes'
 source_hashes[label]=before
pr,p,pt,pn=read(inputs/'power.net');dr,d,dt,dn=read(inputs/'dmx.net')
# Each MCU boundary signal has actual same-name physical silicon pin in this capture.
mcubound={net for (ref,pin),net in p.items() if ref=='X_MCU'}
assert mcubound==(set(expected.values())-{'MCU_VDDR','MCU_VDDS'})|{'SYS_3V3'}
assert set(mcubound)=={net for (ref,pin),net in m.items() if ref=='X101'}
# Actual cross-sheet endpoint contract; no generated or synthetic netlist.
endpoints={
'SPI_CS_N':[(17,'U2',1)],'SPI_MISO':[(14,'U2',2)],'SPI_MOSI':[(15,'U2',5)],'SPI_SCK':[(16,'U2',6)],
'MCU_DE_REQUEST':[(10,'U17',5)],'MCU_ISO_REQUEST':[(11,'U18',1)],
'RESET_OK':[(35,'U16',1)],'VBUS_GOOD_3V3':[(20,'U18',3)],'BUCK_PG':[(21,'U4',4)],
'SERVICE_N_DISTINCT_GPIO':[(9,'S_SERVICE',1)],'ROM_BOOT_STRAP':[(8,'J_FACTORY',6)],
'TMSC':[(24,'J_FACTORY',3)],'TCKC':[(25,'J_FACTORY',4)]}
checks=[]
for net,items in endpoints.items():
 for mp,ref,pin in items:
  assert m['U1',str(mp)]==p[ref,str(pin)]==net
  checks.append({'net':net,'MCU_pin':mp,'power_endpoint':f'{ref}.{pin}'})
assert p['J_FACTORY','5']==p['U16','2']=='MANUAL_RESET_N'
assert p['U16','1']=='RESET_OK' and p['U16','1']!=p['J_FACTORY','5']
# Direction gates and DMX label aliases are explicit; TX/RX are not globally identical labels.
for p_ref,p_pin,d_pin,net in [('U17',3,3,'DMX_DE_SAFE')]:assert p[p_ref,str(p_pin)]==d['U5',str(d_pin)]==net
assert p['U18','7']==d['R4','1']=='DMX_POWER_EN'
assert d['R4','2']==d['U5','8']=='ISOW_EN_PIN'
assert m['U1','28'].startswith('unconnected-') # reserved fault input, not unsafe AON connection
aliases={'MCU_DMX_TX':'DMX_TX','MCU_DMX_RX':'DMX_RX','MCU_RE_N':'DMX_RE_N'}
for net,mp,dp,xpin in [('MCU_DMX_TX',19,2,3),('MCU_DMX_RX',18,4,6),('MCU_RE_N',12,5,5)]:
 assert m['U1',str(mp)]==p['X_DMX',str(xpin)]==net
 assert d['U5',str(dp)]==d['X1',str(xpin)]==aliases[net]
assert d['U5','6']==d['U5','10']=='GND_USB'
assert d['U5','11']==d['U5','15']=='GND_ISO'
assert d['U5','17']==d['U5','20']=='DMX_P' and d['U5','18']==d['U5','19']=='DMX_N'
assert not any(net=='GND_ISO' for net in m.values())
reference=json.loads((P/'reference-contract.json').read_text())
for node,net in reference['pin_nets'].items():
 ref,pin=node.split('.');assert m[ref,pin]==net,(node,m[ref,pin],net)
values={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')}
for ref,mpn in reference['MPNs'].items():
 # Y102 value contains frequency spelling between family and exact custom suffix.
 assert (str(mpn) in values[ref] or ref=='Y102' and 'NX2016SA' in values[ref] and 'EXS00A-CS05517' in values[ref]),(ref,mpn,values[ref])
assert m['U1','43']==m['U101','3']==m['R101','1']=='RF_SELECT'
assert m['R101','2']=='GND_USB' and values['R101']=='100k 1% PROPOSED safe band default'
assert m['TR101','9']==m['U1','1'] and m['TR101','8']==m['U1','2']
assert m['TR101','7']==m['U1','3'] and m['TR101','6']==m['U1','4']
assert not any(ref=='X102' for ref,pin in m)
violations=[v for sh in json.loads((P/'erc.json').read_text())['sheets'] for v in sh['violations']];assert not violations
report={'status':'SUPPORT_AND_DUALBAND_FRONTEND_CAPTURE_PASS_ANTENNA_OPEN','kicad_version':version,'exported_components':24,'actual_ICs':2,'explicit_boundary_components':2,'nets_including_NC':len(r.findall('./nets/net')),'verified_physical_pins':49,'cross_sheet_endpoint_checks':checks,'DMX_aliases':aliases,'factory_reset_to_MR_not_RESET_output':True,'service_distinct_from_ROM':True,'erc_violations':0,'complete_support_capture':True,'reference_pin_connections_checked':len(reference['pin_nets']),'RF_frontend_capture':True,'antenna_final_match_captured':False,'RF_capture':False,'full_product_acceptance':False,'input_source_sha256':source_hashes,'cli_log':log}
import csv
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['reference','value','scope'])
 for ref,value in sorted(values.items()):w.writerow([ref,value,'BOUNDARY NOT PHYSICAL' if ref.startswith('X') else 'Captured prototype component; qualification open'])
(P/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['cli_log','cross_sheet_endpoint_checks']},indent=2))
