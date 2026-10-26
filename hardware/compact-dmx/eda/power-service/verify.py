"""Real KiCad export/ERC plus independent critical circuit checks. No firmware run."""
from pathlib import Path
import subprocess,json,xml.etree.ElementTree as ET,itertools
P=Path(__file__).resolve().parent
cli=['flatpak','run','--command=kicad-cli','org.kicad.KiCad']
def run(*a):return subprocess.run(cli+list(a),check=True,text=True,capture_output=True).stdout.strip()
v=run('version');sch=str(P/'power-service.kicad_sch')
run('sch','export','netlist','--format','kicadxml','-o',str(P/'power-service.net'),sch)
run('sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(P/'erc.json'),sch)
run('sch','export','pdf','-o',str(P/'power-service.pdf'),sch)
run('sch','export','svg','-o',str(P/'rendered'),sch)
r=ET.parse(P/'power-service.net');comps={c.attrib['ref']:c.findtext('value') for c in r.findall('./components/comp')};nets={};types={}
for n in r.findall('./nets/net'):
 for p in n:nets[p.attrib['ref']+'.'+p.attrib['pin']]=n.attrib['name'].removeprefix('/');types[p.attrib['ref']+'.'+p.attrib['pin']]=p.attrib['pintype']
G='GND_USB'

part_values={'U2':'AT25SF161B-MHB-T 16Mbit','U3':'TPS61094DSSR','U4':'TPS62132RGTR','U6':'TPS2553DBVR','U7':'TPS7A0225PDBVR','U8':'TLV3012BIDCKR','U9':'TPS3839G25DBZR','U10':'TPS3700DDCR','U11':'SN74LVC1G74DCUR','U12':'SN74LVC2G08DCUR','U13':'SN74LVC2G32DCUR','U14':'SN74LVC1G04DCKR','U15':'SN74LVC2G08DCUR','U16':'TPS3831K33DQNR','U17':'SN74LVC2G08DCUR','U18':'SN74LVC2G08DCUR','U19':'TPS2116DRLR'}
assert all(comps[k]==value for k,value in part_values.items())
assert Path(sch).read_text().count('(property "Reference" "#FLG')==3

# Independently fixed expected physical IC pins; not imported from the generator.
expect={
'U3':{1:'OSEL_SET',2:'AON_RAW',3:'RUN',4:'NORMAL_IN',5:'BOOST_SW',6:'CAP_POS',7:G,8:G,9:'BACKUP_RAW',10:'BACKUP_RAW',11:'ICHG_SET',12:'VCHG_SET',13:G},
'U4':{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'RUN',14:'SYS_3V3',15:G,16:G,17:G},
'U6':{1:'VBUS_RAW',2:G,3:'VBUS_RAW',4:'INPUT_FAULT_N',5:'ILIM_SET',6:'LIMITED_5V'},
'U7':{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:'AON_2V5'},
'U8':{1:'CAP_OK',2:G,3:'CAP_SENSE',4:'CAP_REF',5:'CAP_REF',6:'AON_2V5'},
'U9':{1:G,2:'AON_OK',3:'AON_2V5'},'U10':{1:'VBUS_OK',2:G,3:'VBUS_SENSE',4:G,5:'AON_2V5',6:None},
'U11':{1:G,2:G,3:None,4:G,5:'RUN_Q',6:'LATCH_CLEAR_N',7:'LATCH_PRE_N',8:'AON_2V5'},
'U12':{1:'VBUS_OK',2:'AON_OK',3:'LATCH_CLEAR_N',4:G,5:'CAP_OR_VBUS',6:'AON_OK',7:'REARM',8:'AON_2V5'},
'U13':{1:'CAP_OK',2:'VBUS_OK',3:None,4:G,5:G,6:G,7:'CAP_OR_VBUS',8:'AON_2V5'},
'U14':{1:None,2:'REARM',3:G,4:'LATCH_PRE_N',5:'AON_2V5'},
'U15':{1:'RUN_Q',2:'AON_OK',3:None,4:G,5:G,6:G,7:'RUN',8:'AON_2V5'},
'U16':{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},
'U17':{1:'RUN',2:'RESET_OK',3:'DMX_DE_SAFE',4:G,5:'MCU_DE_REQUEST',6:'SYS_READY',7:'SYS_READY',8:'SYS_3V3'},
'U18':{1:'MCU_ISO_REQUEST',2:'SYS_READY',3:'VBUS_GOOD_3V3',4:G,5:'VBUS_OK',6:'SYS_READY',7:'DMX_POWER_EN',8:'SYS_3V3'},
'U19':{1:G,2:'NORMAL_IN',3:'LIMITED_5V',4:'LIMITED_5V',5:'LIMITED_5V',6:G,7:'NORMAL_IN',8:None},
'U2':{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G}}
for ref,pins in expect.items():
 for p,n in pins.items():
  k=f'{ref}.{p}'
  if n is None:assert nets.get(k,'unconnected-').startswith('unconnected-'),(k,nets.get(k))
  else:assert nets[k]==n,(k,nets.get(k),n)
# All analogue/logic control terminals must retain meaningful electrical types.
for ref,pins in {'U3':[1,2,3,6,11,12],'U4':[5,7,8,9,13,14],'U6':[3],'U7':[3],'U8':[3,4],'U10':[3,4],'U19':[4,5],'U11':[1,2,6,7],'U12':[1,2,5,6],'U13':[1,2,5,6],'U14':[2],'U15':[1,2,5,6],'U16':[2],'U17':[1,2,5,6],'U18':[1,2,5,6],'U2':[1,3,5,6,7]}.items():
 for pin in pins:assert types[f'{ref}.{pin}']=='input',(ref,pin,types[f'{ref}.{pin}'])
for k,t in {'U3.5':'power_out','U3.9':'power_out','U4.1':'power_out','U6.6':'power_out','U7.5':'power_out','U8.1':'output','U8.5':'output','U10.1':'open_collector','U19.2':'power_out','U11.5':'output','U2.2':'tri_state','U4.4':'open_collector','U6.4':'open_collector'}.items():assert types[k]==t,(k,t)
passives={
'R_CC1':('5.1k 1%','CC1',G),'R_CC2':('5.1k 1%','CC2',G),'R_ILIM':('60.4k 0.1%','ILIM_SET',G),'R_OSEL':('17.4k 1%','OSEL_SET',G),'R_ICHG':('9.53k 1%','ICHG_SET',G),'R_VCHG':('9.53k 1%','VCHG_SET',G),'R_CAP_TOP':('20.0k 0.1%','CAP_POS','CAP_SENSE'),'R_CAP_BOTTOM':('100k 0.1%','CAP_SENSE',G),'R_INPUT_BLEED':('47k','NORMAL_IN',G),'R_RUN_PD':('100k','RUN',G),'R_DE':('100k','MCU_DE_REQUEST',G),'R_ISO':('100k','MCU_ISO_REQUEST',G),'R_RE':('10k','SYS_3V3','MCU_RE_N'),'R_CS':('10k','SYS_3V3','SPI_CS_N'),'R_WP':('10k','SYS_3V3','FLASH_WP_N'),'R_HOLD':('10k','SYS_3V3','FLASH_HOLD_N'),'R_SERVICE':('10k','SYS_3V3','SERVICE_N_DISTINCT_GPIO'),'R_ROM':('10k','SYS_3V3','ROM_BOOT_STRAP'),
'D_AON_USB':('BAT54H,115','AON_RAW','LIMITED_5V'),'D_AON_BUF':('BAT54H,115','AON_RAW','BACKUP_RAW'),'L_BOOST':('XGL4020-222MEC 2.2uH','BOOST_SW','CAP_POS'),'L_BUCK':('XFL4020-222MEC 2.2uH','BUCK_SW','SYS_3V3'),'C_BUF':('HV1325-2R7156-R 15F 2.7V','CAP_POS',G),'C_SS':('3.3n','BUCK_SS',G),'C_IN':('10u effective 10V','NORMAL_IN',G),'C_BACKUP':('22u effective 10V','BACKUP_RAW',G),'C_SYS':('22u effective 10V','SYS_3V3',G),'S_SERVICE':('RESIDENT LOADER SERVICE / NOT ROM','SERVICE_N_DISTINCT_GPIO',G),'S_RESET':('RESET','MANUAL_RESET_N',G)}

# Source detector sees converter VIN after the real reverse barrier, without a slow RC.
passives.update({'R_VBUS_TOP':('93.1k 0.1%','NORMAL_IN','VBUS_SENSE'),
                 'R_VBUS_BOTTOM':('10k 0.1%','VBUS_SENSE',G),
                 'R_VBUS_PU':('10k','AON_2V5','VBUS_OK')})
assert not any(ref in comps for ref in ('D_MAIN','C_VBUS_REF','C_VBUS_FILTER'))

for ref,val,a,b in [('R_INPUT_FAULT','100k','AON_2V5','INPUT_FAULT_N'),('R_BUCK_PG','100k','SYS_3V3','BUCK_PG'),('R_MR','10k','SYS_3V3','MANUAL_RESET_N'),('R_SCK','100k','SPI_SCK',G),('R_MOSI','100k','SPI_MOSI',G)]:passives[ref]=(val,a,b)
for ref,val,rail in [('C_RAW','100n 16V','VBUS_RAW'),('C_LIMIT','1u effective 10V','LIMITED_5V'),('C_U19','100n 10V','LIMITED_5V'),('C_BUCK_IN','10u effective 10V','BACKUP_RAW'),('C_AON_IN','1u effective 10V','AON_RAW'),('C_AON_OUT','1u effective 10V','AON_2V5'),('C_REF','10n','CAP_REF'),('C_FLASH','100n 10V','SYS_3V3'),('C_FLASH_BULK','1u effective 10V','SYS_3V3')]:passives[ref]=(val,rail,G)
for ref,rail in [('U8','AON_2V5'),('U9','AON_2V5'),('U10','AON_2V5'),('U11','AON_2V5'),('U12','AON_2V5'),('U13','AON_2V5'),('U14','AON_2V5'),('U15','AON_2V5'),('U16','SYS_3V3'),('U17','SYS_3V3'),('U18','SYS_3V3')]:passives['C_'+ref]=('100n 10V',rail,G)
assert {ref for ref in comps if ref.startswith(('R_','C_','L_','D_','S_'))}==set(passives)
assert len(comps)==78

for ref,(val,a,b) in passives.items():assert (comps[ref],nets[ref+'.1'],nets[ref+'.2'])==(val,a,b),ref
for ref in comps:
 if ref.startswith(('R_','C_','L_','D_','S_')):
  assert ref+'.1' in nets and ref+'.2' in nets and nets[ref+'.1']!=nets[ref+'.2'],ref
  assert types[ref+'.1']==types[ref+'.2']=='passive',ref
for side in ['A','B']:
 for i in range(1,13):
  k=f'J_USB.{side}{i}'
  if i in (1,12):assert nets[k]==G
  elif i in (4,9):assert nets[k]=='VBUS_RAW'
  elif i==5:assert nets[k]=='CC'+('1' if side=='A' else '2')
  else:assert nets.get(k,'unconnected-').startswith('unconnected-')
assert nets['J_FACTORY.5']=='MANUAL_RESET_N'
assert nets['X_MCU.18']=='BUCK_PG'
assert nets['S_SERVICE.1']!=nets['J_FACTORY.6']==nets['R_ROM.2']
assert not any('CP2102' in value or 'TUSB320' in value or 'STUSB4500' in value for value in comps.values())
# Static truth table independently evaluated AFTER checking real gate connections.
rows=[]
for aon,vbus,cap,q0 in itertools.product([False,True],repeat=4):
 pre=not(vbus and aon);clr=aon and(cap or vbus)
 assert pre or clr # no forbidden simultaneous assertion at stable valid logic levels
 q=0 if not clr else 1 if not pre else q0
 runbit=bool(q and aon)
 if not aon or (not cap and not vbus):assert not runbit
 if aon and vbus:assert runbit
 if aon and not vbus and cap:assert runbit==q0
 rows.append({'AON_OK':aon,'VBUS_OK':vbus,'CAP_OK':cap,'previous_Q':q0,'RUN':runbit})
assert not any(v for sh in json.loads((P/'erc.json').read_text())['sheets'] for v in sh['violations'])
report={'capture_check':'PASS','scope':'Power/buffer/latch/POR/SPI/service hardware captured; MCU/RF and existing DMX sheet are explicit boundaries. Not a routed or qualified product.','kicad_version':v,'components':len(comps),'ICs':len(expect),'nets':len(r.findall('./nets/net')),'erc_errors':0,'erc_warnings':0,'erc_exclusions':0,'critical_IC_pin_map_checks':sum(map(len,expect.values())),'all_two_terminal_checks':len(passives),'all_two_terminal_nodes_present':True,'derived_power_flags':['AON_RAW after diode OR','CAP_POS energy reservoir','SYS_3V3 after buck inductor'],'control_power_flags':0,'stable_latch_cases':len(rows),'USB_data_pins':'NC','service_separate_from_ROM_backdoor':True,'full_product_release':'NOT_RELEASED','cold_cap_startup_accepted':False,'timing_transient_and_hardware_validation':False}
(P/'latch-truth-table.json').write_text(json.dumps(rows,indent=2)+'\n');(P/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

import csv
with (P/'component-ledger.csv').open('w') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['reference','value','pins_in_real_export'])
 for ref,value in sorted(comps.items()):w.writerow([ref,value,sum(k.startswith(ref+'.') for k in nets)])
