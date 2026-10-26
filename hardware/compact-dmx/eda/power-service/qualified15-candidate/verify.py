"""Independent literal source/pin/passive and actual-netlist state checks.
Does not import generator. Semiconductor pin maps transcribed from original PDFs.
"""
from pathlib import Path
import csv,json,re,itertools,math,runpy,xml.etree.ElementTree as E
P=Path(__file__).resolve().parent;root=E.parse(P/'qualified15.net')
mux_model=runpy.run_path(str(P/'mux-mode-proof.py'))
mux_evidence=mux_model['run']()
comps={c.attrib['ref']:c.findtext('value') for c in root.findall('./components/comp')}
roles={c.attrib['ref']:c.findtext('./fields/field[@name="Role"]') for c in root.findall('./components/comp')}
pins={};types={}
for n in root.findall('./nets/net'):
 name=n.attrib['name'].rsplit('/',1)[-1]
 for x in n:pins[x.attrib['ref']+'.'+x.attrib['pin']]=name;types[x.attrib['ref']+'.'+x.attrib['pin']]=x.attrib['pintype']
old_root=E.parse(P/'history/pre-u40-fix-qualified15.net')
old_pins={x.attrib['ref']+'.'+x.attrib['pin']:n.attrib['name'].rsplit('/',1)[-1] for n in old_root.findall('./nets/net') for x in n}
pin_changes=[[k,old_pins.get(k),pins.get(k)] for k in sorted(old_pins.keys()|pins.keys()) if old_pins.get(k)!=pins.get(k)]
assert pin_changes==[['U40.5','GND_USB','AON_USB_LIMITED']],pin_changes
G='GND_USB';A='AON_2V5'
# Exact core pinouts incl exposed pads. None must be an explicit NC.
expected={
'U40':{1:G,2:'AON_RAW',3:'AON_USB_LIMITED',4:'AON_PRIORITY',5:'AON_USB_LIMITED',6:'BOOST_3V9',7:'AON_RAW',8:None},
'U6':{1:'CC_ALLOW',2:G,3:'SOURCE_SENSE_OD',4:'EFUSE_PGTH',5:'VBUS_RAW',6:'LIMITED_5V',7:'EFUSE_DVDT',8:G,9:'EFUSE_ILM',10:'EFUSE_TIMER'},
'U3':{1:'LIMITED_5V',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:G,5:None,6:None,7:'VCHG_FB',8:'CAP_POS',9:G},
'U5':{1:'BOOST_FB',2:'CAP_BOOST_EN',3:'CAP_POS',4:G,5:'BOOST_SW',6:'BOOST_3V9'},
'U19':{1:G,2:'BACKUP_RAW',3:'LIMITED_5V',4:'SOURCE_VALID',5:A,6:'BOOST_3V9',7:'BACKUP_RAW',8:None},
'U4':{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'BUCK_EN',14:'SYS_3V3',15:G,16:G,17:G},
'U7':{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:A},
'U9':{1:G,2:'AON_OK',3:A},'U24':{1:'CC_RAW',2:G,3:'CC_RAW',4:None,5:'CC_3V3'},
'U25':{1:'CC1',2:'CC2',3:G,4:'CC_VBUS_DET',5:None,6:None,7:'CC_OUT1',8:'CC_OUT2',9:None,10:G,11:G,12:'CC_3V3'},
'U26':{1:'CC_ALLOW',2:G,3:'CC_ADVERT_OK',4:None,5:'CC_3V3',6:'CC_3V3'},
'U8':{1:'CAP_OK_OD',2:G,3:'CAP_SENSE',4:'CAP_START_SENSE',5:A,6:'CAP_START_N_OD'},
'U10':{1:'SOURCE_SENSE_OD',2:G,3:'USB_SENSE',4:'MAIN_SENSE',5:A,6:'MAIN_NOT_READY_OD'},
'U20':{1:'SOURCE_SENSE_OD',2:G,3:'RAW_SENSE',4:'BOOST_SENSE',5:A,6:'BOOST_NOT_READY_OD'},
'U27':{1:'VBUS_GOOD_3V3',2:G,3:'BUCK_PG_BUF',4:None,5:'SOURCE_VALID',6:A},
'U16':{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},
'U2':{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G},
'U28':{1:None,2:'CC_OUT1',3:G,4:'CC_ADVERT_OK',5:'CC_3V3'},
'U30':{1:'SOURCE_SENSE',2:G,3:'CC_ALLOW',4:'SOURCE_VALID',5:A,6:'AON_OK'},
'U31':{1:'MAIN_READY',2:G,3:'BOOST_READY',4:'CAP_SAFE_PATH',5:A,6:'SOURCE_VALID'},
'U32':{1:'CAP_OK',2:G,3:'AON_OK',4:'CAP_RESET_N',5:A,6:'CAP_SAFE_PATH'},
'U33':{1:'SOURCE_VALID',2:'CAP_START_OK',3:'CHARGE_DISABLE',4:G,5:'SOURCE_VALID',6:'BUCK_PG',7:'CAP_SET_N',8:A},
'U34':{1:'CAP_SET_N',2:'CAP_BAR',3:'CAP_BAR',4:G,5:'CAP_RESET_N',6:'CAP_ARM',7:'CAP_ARM',8:A},
'U35':{1:'SOURCE_VALID',2:G,3:'CAP_ARM',4:'BUCK_EN',5:A,6:'MAIN_READY'},
'U36':{1:'SOURCE_SENSE_OD',2:G,3:'CAP_OK_OD',4:'CAP_OK',5:A,6:'SOURCE_SENSE'},
'U37':{1:'BUCK_PG',2:G,3:'CAP_ARM',4:'CAP_BOOST_EN',5:A,6:'BUCK_PG_BUF'},
'U38':{1:'CAP_START_N_OD',2:G,3:'MAIN_NOT_READY_OD',4:'MAIN_READY',5:A,6:'CAP_START_OK'},
'U39':{1:'BOOST_NOT_READY_OD',2:G,3:G,4:None,5:A,6:'BOOST_READY'},
'U17':{1:'BUCK_EN',2:'RESET_OK',3:'DMX_DE_SAFE',4:G,5:'MCU_DE_REQUEST',6:'SYS_READY',7:'SYS_READY',8:'SYS_3V3'},
'U18':{1:'MCU_ISO_REQUEST',2:'SYS_READY',3:None,4:G,5:G,6:G,7:'DMX_POWER_EN',8:'SYS_3V3'}}
mpns=dict(zip(['U6','U3','U5','U19','U4','U7','U9','U24','U25','U26','U8','U10','U20','U27','U16','U2','U28','U30','U31','U32','U33','U34','U35','U36','U37','U38','U39','U17','U18'],['TPS259474LRPWR','BQ25173DSGR','TPS61023DRLR','TPS2116DRLR','TPS62132RGTR','TPS7A0225PDBVR','TPS3839G25DBZR','TPS70933DBVR','TUSB320LAIRWBR','TPS3808G33DBVR','TPS3700DDCR','TPS3700DDCR','TPS3700DDCR','TPS3808G01DBVR','TPS3831K33DQNR','AT25SF161B-MHB-T','SN74LVC1G14DCKR','SN74LVC1G11DCKR','SN74LVC1G0832DCKR','SN74LVC1G11DCKR','SN74LVC2G132DCUR','SN74LVC2G132DCUR','SN74LVC1G3208DCKR','SN74LVC2G17DCKR','SN74LVC2G17DCKR','SN74LVC2G14DCKR','SN74LVC2G14DCKR','SN74LVC2G08DCUR','SN74LVC2G08DCUR']))
mpns['U40']='TPS2116DRLR'
assert {r for r in comps if r.startswith('U')}==set(expected)
for ref,ns in expected.items():
 assert comps[ref]==mpns[ref],ref
 for no,net in ns.items():
  actual=pins.get(ref+'.'+str(no),'unconnected-');assert actual==net if net is not None else actual.startswith('unconnected-'),(ref,no,net,actual)
byrole={v:k for k,v in roles.items()};assert len(byrole)==len(roles)
rs={}
def rr(role,value,a,b):rs[role]=(value,a,b)
for x in [('AON_PRIORITY_TOP',22100,'AON_USB_LIMITED','AON_PRIORITY'),('AON_PRIORITY_BOTTOM',10000,'AON_PRIORITY',G),('CC_BLEED',10000,'CC_3V3',G),('CC_FEED',150,'VBUS_RAW','CC_RAW'),('AON_FEED',330,'VBUS_RAW','AON_USB_LIMITED'),('CC_VBUS',909000,'VBUS_RAW','CC_VBUS_DET'),('CC_OUT1_PU',10000,'CC_3V3','CC_OUT1'),('CC_OUT2_PU',10000,'CC_3V3','CC_OUT2'),('CC_ALLOW_PD',249000,'CC_ALLOW',G),('CC_ALLOW_PU',115000,'CC_3V3','CC_ALLOW'),('EFUSE_ILM',3320,'EFUSE_ILM',G),('EFUSE_PGTH_TOP',10000,'LIMITED_5V','EFUSE_PGTH'),('EFUSE_PGTH_BOTTOM',10000,'EFUSE_PGTH',G),('RAW_BLEED',10000,'VBUS_RAW',G),('USB_BLEED',100000,'LIMITED_5V',G),('BOOST_BLEED',100000,'BOOST_3V9',G),('ICHG_FILTER',100,'ICHG_PIN','ICHG_FILTER'),('ICHG',11900,'ICHG_FILTER',G),('VCHG_TOP',22500,'CAP_POS','VCHG_FB'),('VCHG_BOTTOM',10000,'VCHG_FB',G),('BOOST_TOP',562000,'BOOST_3V9','BOOST_FB'),('BOOST_BOTTOM',100000,'BOOST_FB',G),('BUCK_PG',4700,'SYS_3V3','BUCK_PG'),('SOURCE_STATUS',10000,'SYS_3V3','VBUS_GOOD_3V3'),('MR',10000,'SYS_3V3','MANUAL_RESET_N'),('SERVICE',10000,'SYS_3V3','SERVICE_N_DISTINCT_GPIO'),('ROM',10000,'SYS_3V3','ROM_BOOT_STRAP'),('DE',100000,'MCU_DE_REQUEST',G),('ISO',100000,'MCU_ISO_REQUEST',G),('RE',10000,'SYS_3V3','MCU_RE_N'),('CS',10000,'SYS_3V3','SPI_CS_N'),('WP',10000,'SYS_3V3','FLASH_WP_N'),('HOLD',10000,'SYS_3V3','FLASH_HOLD_N'),('SCK',100000,'SPI_SCK',G),('MOSI',100000,'SPI_MOSI',G)]:rr(*x)
for pre,top,rail,sense in [('CAP',32400,'CAP_POS','CAP_SENSE'),('CAP_START',52300,'CAP_POS','CAP_START_SENSE'),('USB',89800,'LIMITED_5V','USB_SENSE'),('MAIN',80600,'BACKUP_RAW','MAIN_SENSE'),('RAW',89800,'VBUS_RAW','RAW_SENSE'),('BOOST_MON',80600,'BOOST_3V9','BOOST_SENSE')]:rr(pre+'_TOP',top,rail,sense);rr(pre+'_BOTTOM',10000,sense,G)
for n in ['SOURCE_SENSE_OD','CAP_OK_OD','CAP_START_N_OD','MAIN_NOT_READY_OD','BOOST_NOT_READY_OD']:rr('PU_'+n,33000 if n=='SOURCE_SENSE_OD' else 47000,A,n)
for n in ['BUCK_EN','CAP_BOOST_EN']:rr('PD_'+n,47000,n,G)
rr('CE_DEFAULT',100000,A,'CHARGE_DISABLE')
rr('DVDT_SERIES',100,'EFUSE_DVDT','EFUSE_DVDT_C')
ps={}
for role,(value,a,b) in rs.items():
 ref=byrole['R_'+role];v=comps[ref];m=re.fullmatch(r'TNPW(0402|0805|1206)(\d+)([RK])(\d*)BE(ED|EA) (\d+)ohm 0.1% 25ppm',v);assert m,(role,v)
 assert int(m[6])==value and math.isclose(float(m[2]+'.'+(m[4] or '0'))*(1000 if m[3]=='K' else 1),value),(role,v)
 assert value<=100000 if m[1]=='0402' else True
 ps[ref]=(v,a,b)
capmpn={'100n':'GRM155R71E104KE14D 100nF 25V X7R','1u':'GRM155R61C105KA12D 1uF 16V X5R','10u':'GRM21BR71A106KE51L 10uF 10V X7R','10n':'GRM155R71H103KA88D 10nF 50V X7R'}
def cc(role,t,rail):ps[byrole[role]]=(capmpn[t],rail,G)
for role,t,rail in [('DVDT','10n','EFUSE_DVDT_C'),('ITIMER','10n','EFUSE_TIMER'),('ICHG','100n','ICHG_FILTER'),('RAW','100n','VBUS_RAW'),('USB','10u','LIMITED_5V'),('CHGIN','1u','LIMITED_5V'),('SS','10n','BUCK_SS'),('AON_USB','1u','AON_USB_LIMITED')]:cc('C_'+role if 'C_'+role in byrole else role,t,rail)
for pre,rail,n,t in [('BACKUP','BACKUP_RAW',2,'10u'),('SYS','SYS_3V3',2,'10u'),('BOOST_OUT','BOOST_3V9',2,'10u'),('BOOST_IN','CAP_POS',1,'10u'),('AON_IN','AON_RAW',2,'1u'),('AON_OUT',A,2,'1u'),('CC_IN','CC_RAW',1,'10u'),('CC_OUT','CC_3V3',1,'10u'),('FLASH','SYS_3V3',1,'1u')]:
 for i in range(n):cc('C_'+pre+str(i+1),t,rail)
for ref in expected:
 if ref in ['U6','U3','U5','U4','U7','U24','U19','U40']:continue
 rail='CC_3V3' if ref in ['U25','U26','U28','U29'] else 'SYS_3V3' if ref in ['U2','U16','U17','U18'] else A
 cc('C_BYPASS_'+ref,'100n',rail)
for role,v,a,b in [('L_BOOST_L','XGL4020-222MEC 2.2uH 20%','BOOST_SW','CAP_POS'),('L_BUCK_L','XFL4020-222MEC 2.2uH 20%','BUCK_SW','SYS_3V3'),('C_CELL','HV1325-2R7156-R 15F 2.7V','CAP_POS',G),('S_SERVICE_CONTACT','PCB normally-open SERVICE contact','SERVICE_N_DISTINCT_GPIO',G),('S_RESET_CONTACT','PCB normally-open RESET contact','MANUAL_RESET_N',G)]:ps[byrole[role]]=(v,a,b)
assert set(ps)=={r for r in comps if re.fullmatch('[RCDLS][0-9]+',r)}
for ref,(v,a,b) in ps.items():assert (comps[ref],pins[ref+'.1'],pins[ref+'.2'],types[ref+'.1'],types[ref+'.2'])==(v,a,b,'passive','passive'),ref
mcu=['SYS_3V3',G,'MCU_DMX_TX','MCU_DMX_RX','MCU_DE_REQUEST','MCU_RE_N','MCU_ISO_REQUEST','SPI_CS_N','SPI_MOSI','SPI_SCK','SPI_MISO','VBUS_GOOD_3V3','SERVICE_N_DISTINCT_GPIO','ROM_BOOT_STRAP','RESET_OK','TMSC','TCKC','BUCK_PG']
dmx=['SYS_3V3',G,'MCU_DMX_TX','DMX_DE_SAFE','MCU_RE_N','MCU_DMX_RX','DMX_POWER_EN']
for ref,ns in [('J2',mcu),('J3',dmx),('J4',['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])]:
 for i,n in enumerate(ns):assert pins[ref+'.'+str(i+1)]==n
assert comps['J1']=='USB4125-GF-A'
for no,n in {'A5':'CC1','B5':'CC2','A9':'VBUS_RAW','B9':'VBUS_RAW','A12':G,'B12':G,'SH':G}.items():assert pins['J1.'+no]==n
assert {k.split('.')[1] for k in pins if k.startswith('J1.')}=={'A5','B5','A9','B9','A12','B12','SH'}
assert not any(n=='INPUT_FAULT_N' for n in pins.values()) # no invented MCU fault translator
assert not any('TPS61094' in v or 'TPS2553' in v for v in comps.values())
assert pins['U5.3']==pins['U3.8']=='CAP_POS'
assert pins['U24.1']=='CC_RAW' and pins[byrole['R_CC_FEED']+'.1']=='VBUS_RAW'
# Actual exported outputs are the physical wired-AND, not a fabricated logic box.
assert {k for k,n in pins.items() if n=='SOURCE_SENSE_OD' and types[k]=='open_collector'}=={'U6.3','U10.1','U20.1'}
assert pins['U28.5']==pins['U26.5']==pins['U26.6']=='CC_3V3'
assert pins['U26.1']==pins['U6.1']=='CC_ALLOW' and pins['U26.3']=='CC_ADVERT_OK'
# Evaluate actual exported gates; latch is solved as state, not a fake digital input.
comb=[]
for r,v in comps.items():
 if r=='U34':continue
 if v=='SN74LVC1G14DCKR':comb.append(('not',[pins[r+'.2']],pins[r+'.4']))
 if v=='SN74LVC1G08DCKR':comb.append(('and',[pins[r+'.1'],pins[r+'.2']],pins[r+'.4']))
 if v in ['SN74LVC1G11DCKR','SN74LVC1G0832DCKR','SN74LVC1G3208DCKR']:comb.append(({'SN74LVC1G11DCKR':'and','SN74LVC1G0832DCKR':'andor','SN74LVC1G3208DCKR':'orand'}[v],[pins[r+'.'+str(i)] for i in [1,3,6]],pins[r+'.4']))
 if v in ['SN74LVC2G08DCUR','SN74LVC2G132DCUR']:
  for a,b,y in [(1,2,7),(5,6,3)]:
   if not pins.get(r+'.'+str(y),'unconnected-').startswith('unconnected-'):comb.append(('nand' if '132' in v else 'and',[pins[r+'.'+str(i)] for i in [a,b]],pins[r+'.'+str(y)]))
 if v in ['SN74LVC2G17DCKR','SN74LVC2G14DCKR']:
  for a,y in [(1,6),(3,4)]:
   if not pins.get(r+'.'+str(y),'unconnected-').startswith('unconnected-'):comb.append(('not' if '14' in v else 'buf',[pins[r+'.'+str(a)]],pins[r+'.'+str(y)]))
def calc(ex,q):
 # Combinational cases below assume established supplies, not a proof that
 # AON always exists. Physical supply selection is exercised separately below.
 e={G:False,A:True,'CC_3V3':True,'SYS_3V3':True,'CAP_ARM':q,'CAP_BAR':not q,'MCU_DE_REQUEST':True,'MCU_ISO_REQUEST':True,**ex}
 # U26 is the actual source/supply supervisor, with delayed release.
 # Static supplyvalid + MR truth is abstracted here; analog pullproof separate.
 e['CC_ALLOW']=ex['CC_SUPPLY_VALID'] and not ex['CC_OUT1']
 pending=comb[:]
 while pending:
  rest=[]
  for op,ns,out in pending:
   if any(n not in e for n in ns):rest.append((op,ns,out));continue
   vs=[e[n] for n in ns]
   e[out]=all(vs) if op=='and' else not all(vs) if op=='nand' else not vs[0] if op=='not' else vs[0] if op=='buf' else (vs[0] and vs[1]) or vs[2] if op=='andor' else (vs[0] or vs[1]) and vs[2]
  assert len(rest)<len(pending),rest
  pending=rest
 return e
def settle(ex,q):
 for i in range(6):
  e=calc(ex,q);s=not e['CAP_SET_N'];r=not e['CAP_RESET_N'];assert not (s and r),(ex,q,e)
  qq=False if r else True if s else q
  if qq==q:return e,q
  q=qq
 raise AssertionError('latch did not settle')
inputs=['SOURCE_SENSE_OD','CAP_OK_OD','CAP_START_N_OD','MAIN_NOT_READY_OD','BOOST_NOT_READY_OD','CC_OUT1','CC_SUPPLY_VALID','AON_OK','BUCK_PG','RESET_OK']
cases=0
for bits in itertools.product([False,True],repeat=len(inputs)):
 ex=dict(zip(inputs,bits))
 if not ex['CAP_START_N_OD'] and not ex['CAP_OK_OD']:continue
 for q in [False,True]:
  e,qq=settle(ex,q);cases+=1
  assert e['CC_ALLOW']==(not ex['CC_OUT1'] and ex['CC_SUPPLY_VALID'])
  if not ex['AON_OK']:assert not e['SOURCE_VALID'] and not qq and not e['BUCK_EN'] and not e['CAP_BOOST_EN']
  if not ex['CAP_OK_OD']:assert not qq and not e['CAP_BOOST_EN']
  if not q and not e['SOURCE_VALID']:assert not qq
  if not e['SOURCE_VALID'] and not e['CAP_SAFE_PATH']:assert not qq
  assert e['CHARGE_DISABLE']==(not (e['SOURCE_VALID'] and ex['BUCK_PG']))
  if not ex['MAIN_NOT_READY_OD'] and e['SOURCE_VALID']:assert e['BUCK_EN'] # Empty cap does not block USB boot.
  if not e['CC_ALLOW']:assert not e['SOURCE_VALID'] # main eFuse EN actually CC_ALLOW, independent of backup.
  if e['SYS_READY']:assert e['BUCK_EN'] and ex['RESET_OK']
# True physical advertisement modes, both orientations, per TUSB Table3.
cc=[]
for orient in ['CC1','CC2']:
 for mode,out1,out2 in [('unattached',True,True),('default',True,False),('1.5A',False,True),('3A',False,False),('detached',True,True),('invalid/dead-VDD',True,True)]:
  ex=dict(zip(inputs,[True,False,True,False,True,out1,True,True,False,False]));e,q=settle(ex,False)
  allowed=mode in ['1.5A','3A'];assert e['CC_ALLOW']==allowed and e['BUCK_EN']==allowed and not q
  cc.append({'orientation':orient,'mode':mode,'OUT1':int(out1),'OUT2':int(out2),'main_eFuse_enabled':allowed,'empty_cap_buck_enabled':e['BUCK_EN']})
ex=dict(zip(inputs,[True,False,True,False,True,False,True,True,False,True]));e,q=settle(ex,False);assert e['BUCK_EN'] and e['CHARGE_DISABLE']
ex['BUCK_PG']=True;e,q=settle(ex,q);assert not e['CHARGE_DISABLE']
ex.update(CAP_OK_OD=True,CAP_START_N_OD=False);e,q=settle(ex,q);assert q and not e['BOOST_READY']
ex['BOOST_NOT_READY_OD']=False;e,q=settle(ex,q);assert q
ex.update(CC_OUT1=True,SOURCE_SENSE_OD=False);e,q=settle(ex,q);assert q and e['BUCK_EN'] and not e['CC_ALLOW'] and e['CHARGE_DISABLE']
ex['CAP_OK_OD']=False;ex['CAP_START_N_OD']=True;e,q=settle(ex,q);assert not q and not e['BUCK_EN']
ex['CAP_OK_OD']=True;ex['CAP_START_N_OD']=False;e,q=settle(ex,q);assert not q # rebound without source cannot arm
ex.update(CC_OUT1=False,SOURCE_SENSE_OD=True);e,q=settle(ex,q);assert q
ex.update(SOURCE_SENSE_OD=False,MAIN_NOT_READY_OD=True);e,q=settle(ex,q);assert not q
ex['MAIN_NOT_READY_OD']=False;e,q=settle(ex,q);assert not q # ready rail rebound cannot restart.
# Source-based physical U40 states drive AON reset, rather than assuming AON.
# Only settled, adequately supplied logic is evaluated: no invented sub1.65V
# gate behavior or zero-time supervisor/softstart response.
physical=[]
for label,raw,boost,cc_ok,source_ok,armed in [
 ('cold source',3.73769,0,True,True,False),
 ('default source',3.73769,0,False,True,False),
 ('hot attach',3.73769,3.9,True,True,True),
 ('backup after detach',0,3.9,False,False,True),
 ('source-free cap rebound',0,3.9,False,False,False)]:
 choice=mux_model['u40_selection'](pins,raw,boost,raw>mux_evidence['priority_input_threshold_max_V'])
 supply=raw if choice=='VIN1' else boost if choice=='VIN2' else 0
 assert supply>=3.7 # conditional2mA raw allocation/valid boost, not transient assertion
 ex=dict(zip(inputs,[source_ok,boost>0,not boost,False,not boost,not cc_ok,cc_ok,True,False,True]))
 if label=='cold source':
  ex['AON_OK']=False;e,q=settle(ex,False)
  assert not e['SOURCE_VALID'] and not e['BUCK_EN'] and not q
  ex['AON_OK']=True # only after the actual supervisor's reset release
 e,q=settle(ex,armed)
 assert e['SOURCE_VALID']==(source_ok and cc_ok)
 if label=='cold source':assert e['BUCK_EN'] and not q and e['CHARGE_DISABLE']
 if not armed and not e['SOURCE_VALID']:assert not q and not e['CAP_BOOST_EN'] and not e['BUCK_EN']
 physical.append({'scenario':label,'U40_selection':choice,'conditional_AON_input_V':supply,'SOURCE_VALID':e['SOURCE_VALID'],'CAP_ARM':q,'BUCK_EN':e['BUCK_EN']})
# eFuse latch is not cleared by its own PG/output collapse: pin1 is CC_ALLOW.
assert pins['U6.1']=='CC_ALLOW' and all('SOURCE_VALID' not in ns for op,ns,y in comb if y=='CC_ALLOW')
# Stable-source status supervisor pin contract: actual source + buffered buckPG,
# delayed assertion after both; asynchronous low on either, no timed good override.
assert pins['U27.5']=='SOURCE_VALID' and pins['U27.3']=='BUCK_PG_BUF' and pins['U27.1']=='VBUS_GOOD_3V3'
viol=[v for sh in json.loads((P/'erc.json').read_text())['sheets'] for v in sh['violations']];assert not viol,viol
rows=list(csv.DictReader((P/'component-ledger.csv').open()));area=sum(float(r['body_area_mm2']) for r in rows if r['kind']=='physical')
report={'status':'PASS static electrical/netlist checks; not arbitrary analog timing or manufacturing release','ICs':len(expected),'IC_pins_checked':sum(map(len,expected.values())),'two_terminal_checks':len(ps),'stable_cases':cases,'CC_orientation_mode_cases':cc,'temporal_scenarios':'empty-cap source boot; PG-gated charging; cap-only booster startup; downgrade backup; UVLO and proven rail-loss cutoff; no source-free rebound rearm PASS','fault_latch':'TPS259474L internally latched circuit-breaker; EN stays CC_ALLOW despite PG/output collapse. No blanket peak-current claim.','source_stability':'TPS3808G01 CTopen12..28ms assertion after actual SOURCE_VALID and actualBUCKPG; asynchronous assertion low; finite propagation requires measurement','source_wired_AND':['U6.3 PG','U10.1 USBUV','U20.1 RAWUV'],'ERC_errors':0,'ERC_warnings':0,'ERC_exclusions':0,'physical_parts':sum(r['kind']=='physical' for r in rows),'body_area_excluding_cell_including_USB_mm2':area-383.4,'body_area_excluding_cell_and_USB_mm2':area-383.4-60.792,'USB_contract':'GCT six physical contacts+SH; no old24contact phantom pins; TUSB internalRd only','MCU_DMX_factory_mapping':'18/7/6 preserved; no fault translator or firmware','manufacturing_release':False}
report['U40_source_behavior']={'evidence':'mux-mode-proof.json','only_exported_pin_changes':pin_changes,'datasheet_truth_rows':mux_evidence['documented_truth_rows_tested'],'qualified_corner_cases':mux_evidence['qualified_source_corner_cases'],'old_grounded_MODE_negative_cases':len(mux_evidence['old_wiring_negative_regressions']),'physical_supply_gate_cases':physical,'unpowered_logic':'Not evaluated as valid logic; no assertion about sub1.65V gates or supervisor timing'}
(P/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='CC_orientation_mode_cases'},indent=2))
