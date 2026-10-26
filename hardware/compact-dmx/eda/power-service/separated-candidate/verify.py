"""Independent netlist/pin/passive/logic verification, not a transient simulator.
Does not import generate.py; constants are transcribed from cited original PDFs.
"""
from pathlib import Path
import json,re,itertools,math,csv,hashlib,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent
root=ET.parse(P/'separated-candidate.net')
comps={c.attrib['ref']:c.findtext('value') for c in root.findall('./components/comp')}
pins={};types={};fullnames={}
for n in root.findall('./nets/net'):
    leaf=n.attrib['name'].rsplit('/',1)[-1]
    assert leaf not in fullnames or fullnames[leaf]==n.attrib['name'],('ambiguous local/global name',leaf)
    fullnames[leaf]=n.attrib['name']
    for x in n:
        k=x.attrib['ref']+'.'+x.attrib['pin'];pins[k]=leaf;types[k]=x.attrib['pintype']
G='GND_USB';A='AON_2V5'
# Literal source-based core pin maps. None means an explicit schematic NC.
expected={
'U6':{1:'VBUS_RAW',2:G,3:'MAIN_INPUT_EN',4:'INPUT_FAULT_N',5:'ILIM_SET',6:'LIMITED_5V'},
'U24':{1:'LIMITED_5V',2:G,3:'CHG_BRANCH_EN',4:'INPUT_FAULT_N',5:'LIMITED_5V',6:'CHG_IN'},
'U3':{1:'CHG_IN',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:G,5:None,6:None,7:'VCHG_FB',8:'CAP_POS',9:G},
'U5':{1:'BOOST_FB',2:'CAP_BOOST_EN',3:'CAP_POS',4:G,5:'BOOST_SW',6:'BOOST_3V9'},
'U19':{1:G,2:'BACKUP_RAW',3:'LIMITED_5V',4:'USB_VALID',5:A,6:'BOOST_3V9',7:'BACKUP_RAW',8:None},
'U4':{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'BUCK_EN',14:'SYS_3V3',15:G,16:G,17:G},
'U7':{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:A},
'U9':{1:G,2:'AON_OK',3:A},
'U8':{1:'CAP_OK_OD',2:G,3:'CAP_SENSE',4:'CAP_START_SENSE',5:A,6:'CAP_START_N_OD'},
'U10':{1:'USB_UV_OK_OD',2:G,3:'USB_SENSE',4:'MAIN_SENSE',5:A,6:'MAIN_NOT_READY_OD'},
'U20':{1:'RAW_UV_OK_OD',2:G,3:'RAW_SENSE',4:'RAW_PRESENT_SENSE',5:A,6:'RAW_ABSENT_OD'},
'U21':{1:'CHGIN_OK_OD',2:G,3:'CHGIN_SENSE',4:'BOOST_SENSE',5:A,6:'BOOST_NOT_READY_OD'},
'U16':{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},
'U2':{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G}}
mpns={'U6':'TPS2553DBVR','U24':'TPS2553DBVR','U3':'BQ25173DSGR','U5':'TPS61023DRLR','U19':'TPS2116DRLR','U4':'TPS62132RGTR','U7':'TPS7A0225PDBVR','U9':'TPS3839G25DBZR','U8':'TPS3700DDCR','U10':'TPS3700DDCR','U20':'TPS3700DDCR','U21':'TPS3700DDCR','U16':'TPS3831K33DQNR','U2':'AT25SF161B-MHB-T'}
# Independently transcribed desired functions, then checked against real pin nets.
ands=[('AON_OK','NO_FAULT','CONTROL_OK'),('RAW_UV_OK','AON_OK','FAULT_VALID'),
 ('FAULT_VALID','FAULT_REQUEST','FAULT_SET'),('RAW_UV_OK','USB_UV_OK','USB_VALID'),
 ('CONTROL_OK','RAW_UV_OK','MAIN_INPUT_EN'),('CONTROL_OK','CAP_OK','CAP_BASE_OK'),
 ('USB_VALID','CAP_START_OK','CAP_SET_ALLOW'),('CAP_BASE_OK','CAP_SET_ALLOW','CAP_SET'),
 ('BOOST_READY','MAIN_READY','BOOST_AND_MAIN'),('CAP_ARM','BOOST_AND_MAIN','PROVEN_SET'),
 ('BACKUP_PROVEN','USB_INVALID','LOSS_AFTER_PROOF'),('LOSS_AFTER_PROOF','BACKUP_INVALID','LOSS_CUTOFF'),
 ('CONTROL_OK','CAP_ARM','CAP_BOOST_EN'),('CAP_ARM','BOOST_READY','BACKUP_PATH'),
 ('CONTROL_OK','PATH_AVAILABLE','BUCK_ALLOWED'),('BUCK_ALLOWED','MAIN_READY','BUCK_EN'),
 ('USB_VALID','BUCK_PG_BUF','CHG_BRANCH_PRE'),('CHG_BRANCH_PRE','CONTROL_OK','CHG_SET'),
 ('CONTROL_OK','RAW_UV_OK','CHG_HOLD_OK'),('CHG_ARM','CHG_HOLD_OK','CHG_BRANCH_EN'),
 ('CHG_BRANCH_EN','CHGIN_OK','CHG_ALLOWED')]
ors=[('RAW_ABSENT','AON_BAD','FAULT_RESET'),('CAP_BASE_BAD','LOSS_CUTOFF','CAP_RESET'),('USB_VALID','BACKUP_PATH','PATH_AVAILABLE')]
invs=[('AON_OK','AON_BAD'),('FAULTS_OK','FAULT_REQUEST'),('FAULT_Q','NO_FAULT'),
 ('MAIN_NOT_READY','MAIN_READY'),('CAP_START_N','CAP_START_OK'),('BOOST_NOT_READY','BOOST_READY'),
 ('BOOST_AND_MAIN','BACKUP_INVALID'),('USB_VALID','USB_INVALID'),('CAP_BASE_OK','CAP_BASE_BAD'),
 ('CAP_ARM','CAP_ARM_NOT'),('CHG_ALLOWED','CHARGE_DISABLE'),('CHG_HOLD_OK','CHG_RESET')]
bufs=[('RAW_UV_OK_OD','RAW_UV_OK'),('RAW_ABSENT_OD','RAW_ABSENT'),('USB_UV_OK_OD','USB_UV_OK'),('MAIN_NOT_READY_OD','MAIN_NOT_READY'),('CAP_OK_OD','CAP_OK'),('CAP_START_N_OD','CAP_START_N'),('CHGIN_OK_OD','CHGIN_OK'),('BOOST_NOT_READY_OD','BOOST_NOT_READY'),('INPUT_FAULT_N','FAULTS_OK'),('BUCK_PG','BUCK_PG_BUF')]
for start,ops,mpn in [(30,ands,'SN74LVC2G08DCUR'),(42,ors,'SN74LVC2G32DCUR')]:
    for i in range(0,len(ops),2):
        ref='U'+str(start+i//2);m={4:G,8:A}
        for j in range(2):
            a,b,y=ops[i+j] if i+j<len(ops) else (G,G,None)
            m.update(zip((1,2,7) if j==0 else (5,6,3),(a,b,y)))
        expected[ref]=m;mpns[ref]=mpn
for start,ops,mpn in [(50,invs,'SN74LVC2G04DCKR'),(60,bufs,'SN74LVC2G17DCKR')]:
    for i in range(0,len(ops),2):
        ref='U'+str(start+i//2);m={2:G,5:A}
        for j in range(2):
            a,y=ops[i+j] if i+j<len(ops) else (G,None)
            m.update(zip((1,6) if j==0 else (3,4),(a,y)))
        expected[ref]=m;mpns[ref]=mpn
latches=[('U22','FAULT_SET','FAULT_RESET','FAULT_Q','FAULT_BAR'),('U11','CAP_SET','CAP_RESET','CAP_ARM','CAP_BAR'),('U23','PROVEN_SET','CAP_ARM_NOT','BACKUP_PROVEN','PROVEN_BAR'),('U25','CHG_SET','CHG_RESET','CHG_ARM','CHG_BAR')]
for ref,s,r,q,qb in latches:
    expected[ref]={1:r,2:qb,7:q,5:s,6:q,3:qb,4:G,8:A};mpns[ref]='SN74LVC2G02DCUR'
sysands=[('BUCK_EN','RESET_OK','SYS_READY'),('MCU_DE_REQUEST','SYS_READY','DMX_DE_SAFE'),('MCU_ISO_REQUEST','SYS_READY','DMX_POWER_EN'),('USB_VALID','SYS_READY','VBUS_GOOD_3V3')]
for i,ref in enumerate(('U17','U18')):
    m={4:G,8:'SYS_3V3'}
    for j,(a,b,y) in enumerate(sysands[2*i:2*i+2]):m.update(zip((1,2,7) if j==0 else (5,6,3),(a,b,y)))
    expected[ref]=m;mpns[ref]='SN74LVC2G08DCUR'
for ref,m in expected.items():
    assert comps[ref]==mpns[ref],ref
    for pin,n in m.items():
        k=f'{ref}.{pin}'
        if n is None:assert pins.get(k,'unconnected-').startswith('unconnected-'),k
        else:assert pins[k]==n,(k,pins.get(k),n)
assert {r for r in comps if r.startswith('U')}==set(expected)
assert types['U24.5']=='passive' and pins['U24.5']==pins['U24.1'] # Explicit supported IN mode, not a resistive extrapolation.
assert types['U6.5']=='output'
for k in ('U3.3','U5.2','U19.4','U19.5','U4.13','U8.3','U8.4'):assert types[k]=='input',k
for k in ('U24.4','U6.4','U4.4','U8.1','U10.6'):assert types[k]=='open_collector',k
# Passive list is independent of the generator, including exact values and ends.
rs={}
def rr(r,ohms,a,b):rs[r]=(ohms,a,b)
for item in [('R_AON_USB',330,'VBUS_RAW','AON_USB_LIMITED'),('R_ILIM',61900,'ILIM_SET',G),('R_CC1',5100,'CC1',G),('R_CC2',5100,'CC2',G),('R_RAW_BLEED',10000,'VBUS_RAW',G),('R_LIMIT_BLEED',100000,'LIMITED_5V',G),('R_BOOST_BLEED',100000,'BOOST_3V9',G),('R_ICHG_FILTER',100,'ICHG_PIN','ICHG_FILTER'),('R_ICHG',11900,'ICHG_FILTER',G),('R_VCHG_TOP',22500,'CAP_POS','VCHG_FB'),('R_VCHG_BOTTOM',10000,'VCHG_FB',G),('R_BOOST_TOP',562000,'BOOST_3V9','BOOST_FB'),('R_BOOST_BOTTOM',100000,'BOOST_FB',G),('R_BUCK_PG',4700,'SYS_3V3','BUCK_PG'),('R_MR',10000,'SYS_3V3','MANUAL_RESET_N'),('R_SERVICE',10000,'SYS_3V3','SERVICE_N_DISTINCT_GPIO'),('R_ROM',10000,'SYS_3V3','ROM_BOOT_STRAP'),('R_DE',100000,'MCU_DE_REQUEST',G),('R_ISO',100000,'MCU_ISO_REQUEST',G),('R_RE',10000,'SYS_3V3','MCU_RE_N'),('R_CS',10000,'SYS_3V3','SPI_CS_N'),('R_WP',10000,'SYS_3V3','FLASH_WP_N'),('R_HOLD',10000,'SYS_3V3','FLASH_HOLD_N'),('R_SCK',100000,'SPI_SCK',G),('R_MOSI',100000,'SPI_MOSI',G)]:rr(*item)
for pre,top,rail,sense in [('CAP',32400,'CAP_POS','CAP_SENSE'),('CAP_START',45300,'CAP_POS','CAP_START_SENSE'),('USB',93100,'LIMITED_5V','USB_SENSE'),('MAIN',80600,'BACKUP_RAW','MAIN_SENSE'),('RAW',89800,'VBUS_RAW','RAW_SENSE'),('RAW_PRESENT',10000,'VBUS_RAW','RAW_PRESENT_SENSE'),('CHGIN',80600,'CHG_IN','CHGIN_SENSE'),('BOOST_MON',80600,'BOOST_3V9','BOOST_SENSE')]:
    rr('R_'+pre+'_TOP',top,rail,sense);rr('R_'+pre+'_BOTTOM',10000,sense,G)
for n,_ in bufs:
    if n!='BUCK_PG':rr('R_PU_'+n,47000,A,n)
for n in ('MAIN_INPUT_EN','CHG_BRANCH_EN','CAP_BOOST_EN','BUCK_EN'):rr('R_PD_'+n,47000,n,G)
rr('R_CE_DEFAULT',100000,A,'CHARGE_DISABLE')
ps={}
for r,(v,a,b) in rs.items():
    assert (pins[r+'.1'],pins[r+'.2'])==(a,b),r
    assert re.search(r' '+str(v)+r'ohm 0.1% 25ppm$',comps[r]),(r,comps[r],v)
    m=re.fullmatch(r'TNPW(0402|0603|0805)(\d+)([RK])(\d*)BE(ED|EA)',comps[r].split()[0]);assert m,(r,comps[r])
    val=float(m[2]+'.'+(m[4] or '0'))*(1000 if m[3]=='K' else 1)
    assert math.isclose(val,v),(r,val,v)
    assert v<=({'0402':100000,'0603':332000,'0805':1000000}[m[1]])
    ps[r]=(comps[r],a,b)
capmpn={'100n':'GRM155R71E104KE14D 100nF 25V X7R','1u':'GRM155R61C105KA12D 1uF 16V X5R','10u':'GRM21BR71A106KE51L 10uF 10V X7R'}
def cc(r,v,a):ps[r]=(capmpn[v],a,G)
for r,v,a in [('C_RAW','100n','VBUS_RAW'),('C_ICHG','100n','ICHG_FILTER'),('C_SS','100n','BUCK_SS'),('C_FLASH','100n','SYS_3V3')]:cc(r,v,a)
for pre,rail,n in [('LIMIT','LIMITED_5V',6),('BACKUP','BACKUP_RAW',2),('BUCK_IN','BACKUP_RAW',2),('SYS','SYS_3V3',4),('BOOST_OUT','BOOST_3V9',2),('BOOST_IN','CAP_POS',2)]:
    for i in range(n):cc(f'C_{pre}{i+1}','10u',rail)
for pre,rail,n in [('CHG_IN','CHG_IN',2),('AON_IN','AON_RAW',2),('AON_OUT',A,2),('FLASH_BULK','SYS_3V3',1)]:
    for i in range(n):cc(f'C_{pre}{i+1}','1u',rail)
for ref in expected:
    if ref in ('U2','U16','U17','U18'):rail='SYS_3V3'
    elif ref in ('U8','U9','U10','U20','U21') or mpns[ref].startswith('SN74'):rail=A
    else:continue
    cc('C_'+ref,'100n',rail)
ps.update({'D_AON_USB':('BAT54H,115','AON_RAW','AON_USB_LIMITED'),'D_AON_BUF':('BAT54H,115','AON_RAW','BOOST_3V9'),'L_BOOST':('XGL4020-222MEC 2.2uH 20%','BOOST_SW','CAP_POS'),'L_BUCK':('XFL4020-222MEC 2.2uH 20%','BUCK_SW','SYS_3V3'),'C_BUF':('HV1325-2R7156-R 15F 2.7V','CAP_POS',G),'S_SERVICE':('PCB two-pad SERVICE contact, normally open','SERVICE_N_DISTINCT_GPIO',G),'S_RESET':('PCB two-pad RESET contact, normally open','MANUAL_RESET_N',G)})
assert {r for r in comps if r.startswith(('R_','C_','D_','L_','S_'))}==set(ps)
for ref,(v,a,b) in ps.items():
    assert (comps[ref],pins[ref+'.1'],pins[ref+'.2'])==(v,a,b),ref
    assert types[ref+'.1']==types[ref+'.2']=='passive' and a!=b,ref
# Existing boundaries retained, not phantom internal power sources.
mcu=['SYS_3V3',G,'MCU_DMX_TX','MCU_DMX_RX','MCU_DE_REQUEST','MCU_RE_N','MCU_ISO_REQUEST','SPI_CS_N','SPI_MOSI','SPI_SCK','SPI_MISO','VBUS_GOOD_3V3','SERVICE_N_DISTINCT_GPIO','ROM_BOOT_STRAP','RESET_OK','TMSC','TCKC','BUCK_PG']
dmx=['SYS_3V3',G,'MCU_DMX_TX','DMX_DE_SAFE','MCU_RE_N','MCU_DMX_RX','DMX_POWER_EN']
for ref,ns in [('X_MCU',mcu),('X_DMX',dmx),('J_FACTORY',['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])]:
    for i,n in enumerate(ns):assert pins[f'{ref}.{i+1}']==n
assert not any(k.startswith('X_MCU.') and n=='INPUT_FAULT_N' for k,n in pins.items())
for side in ('A','B'):
    for i in range(1,13):
        k=f'J_USB.{side}{i}'
        if i in (1,12):assert pins[k]==G
        elif i in (4,9):assert pins[k]=='VBUS_RAW'
        elif i==5:assert pins[k]=='CC'+('1' if side=='A' else '2')
        else:assert pins.get(k,'unconnected-').startswith('unconnected-')
assert pins['U5.3']==pins['U3.8']=='CAP_POS'
assert pins['U19.3']!=pins['U19.6'] and pins['U19.4']=='USB_VALID'
assert pins['R_AON_USB.1']=='VBUS_RAW' and pins['R_AON_USB.2']!='LIMITED_5V'
assert all('TPS61094' not in v and 'TUSB' not in v for v in comps.values())
# Evaluate actual exported gate pins after the independent map checks above.
comb=[]
for ref,v in comps.items():
    if v in ('SN74LVC2G08DCUR','SN74LVC2G32DCUR'):
        op='and' if '2G08' in v else 'or'
        for a,b,y in ((1,2,7),(5,6,3)):
            if not pins.get(f'{ref}.{y}','unconnected-').startswith('unconnected-'):comb.append((op,[pins[f'{ref}.{a}'],pins[f'{ref}.{b}']],pins[f'{ref}.{y}']))
    if v in ('SN74LVC2G04DCKR','SN74LVC2G17DCKR'):
        op='not' if '2G04' in v else 'buf'
        for a,y in ((1,6),(3,4)):
            if not pins.get(f'{ref}.{y}','unconnected-').startswith('unconnected-'):comb.append((op,[pins[f'{ref}.{a}']],pins[f'{ref}.{y}']))
def logic(external,state):
    e={G:False,A:True,'SYS_3V3':True,'MCU_DE_REQUEST':True,'MCU_ISO_REQUEST':True,**external}
    for (_,s,r,q,qb),v in zip(latches,state):e[q]=v;e[qb]=not v
    pending=list(comb)
    while pending:
        rest=[]
        for op,ns,y in pending:
            if not all(n in e for n in ns):rest.append((op,ns,y));continue
            vs=[e[n] for n in ns];e[y]=all(vs) if op=='and' else any(vs) if op=='or' else not vs[0] if op=='not' else vs[0]
        assert len(rest)<len(pending),rest
        pending=rest
    return e
settle_steps=0
def settle(ext,state):
    global settle_steps
    for i in range(12):
        e=logic(ext,state);next_state=[]
        for ref,s,r,q,qb in latches:
            assert not(e[s] and e[r]),('SR both asserted',ref,ext,state)
            next_state.append(False if e[r] else True if e[s] else e[q])
        next_state=tuple(next_state)
        if next_state==tuple(state):settle_steps=max(settle_steps,i);return e,next_state
        state=next_state
    raise AssertionError(('state did not settle',ext,state))
inputs=['AON_OK','RAW_UV_OK_OD','RAW_ABSENT_OD','USB_UV_OK_OD','MAIN_NOT_READY_OD','CAP_OK_OD','CAP_START_N_OD','CHGIN_OK_OD','BOOST_NOT_READY_OD','INPUT_FAULT_N','BUCK_PG','RESET_OK']
cases=0
for values in itertools.product((False,True),repeat=len(inputs)):
    ex=dict(zip(inputs,values))
    if ex['RAW_UV_OK_OD'] and ex['RAW_ABSENT_OD']:continue # disjoint measured thresholds
    if not ex['CAP_START_N_OD'] and not ex['CAP_OK_OD']:continue # start threshold above loaded UVLO
    for previous in itertools.product((False,True),repeat=4):
        e,new=settle(ex,previous);cases+=1
        if not ex['AON_OK'] or e['FAULT_Q']:
            assert not any(e[n] for n in ('MAIN_INPUT_EN','BUCK_EN','CAP_BOOST_EN','CHG_BRANCH_EN','VBUS_GOOD_3V3'))
        if not e['RAW_UV_OK']:
            assert not e['MAIN_INPUT_EN'] and not e['CHG_BRANCH_EN'] and not e['VBUS_GOOD_3V3']
        if not e['USB_VALID'] and not previous[1]:assert not e['CAP_ARM'] # source-free rebound cannot arm
        if not e['CAP_OK']:assert not e['CAP_ARM'] and not e['CAP_BOOST_EN']
        if not e['CHGIN_OK']:assert e['CHARGE_DISABLE']
        if e['VBUS_GOOD_3V3']:assert e['USB_VALID'] and e['SYS_READY']
        if not previous[3] and not e['BUCK_PG_BUF']:assert not e['CHG_BRANCH_EN']
        if e['CHG_ARM'] and e['CONTROL_OK'] and e['RAW_UV_OK']:assert e['CHG_BRANCH_EN'] # survives PG loss so real fault can persist
        if e['USB_VALID'] and e['CONTROL_OK'] and e['MAIN_READY']:assert e['BUCK_EN'] # independent of cap state
# Temporal scenarios, still digital logic only, not converter waveforms.
ex={n:True for n in inputs};ex.update(RAW_ABSENT_OD=False,MAIN_NOT_READY_OD=False,CAP_OK_OD=False,CAP_START_N_OD=True,CHGIN_OK_OD=False,BOOST_NOT_READY_OD=True,BUCK_PG=False)
e,st=settle(ex,(False,False,False,False));assert e['BUCK_EN'] and not e['CHG_BRANCH_EN']
ex['BUCK_PG']=True;e,st=settle(ex,st);assert e['CHG_BRANCH_EN'] and e['CHARGE_DISABLE']
ex['CHGIN_OK_OD']=True;e,st=settle(ex,st);assert not e['CHARGE_DISABLE'] and not e['CAP_ARM']
# Short branch: input stays low, branch is kept on despite PG/qualifier loss, until FAULT asserts.
ex.update(CHGIN_OK_OD=False,BUCK_PG=False,USB_UV_OK_OD=False)
e,st=settle(ex,st);assert e['CHG_BRANCH_EN'] and not e['BUCK_EN']
ex['INPUT_FAULT_N']=False;e,st=settle(ex,st);assert e['FAULT_Q'] and not e['CHG_BRANCH_EN']
ex.update(INPUT_FAULT_N=True,USB_UV_OK_OD=True,BUCK_PG=True)
e,st=settle(ex,st);assert e['FAULT_Q'] and not e['BUCK_EN']
ex.update(RAW_UV_OK_OD=False,RAW_ABSENT_OD=True);e,st=settle(ex,st);assert not e['FAULT_Q']
ex.update(RAW_UV_OK_OD=True,RAW_ABSENT_OD=False,CAP_OK_OD=True,CAP_START_N_OD=False,MAIN_NOT_READY_OD=False,BOOST_NOT_READY_OD=False,CHGIN_OK_OD=True)
e,st=settle(ex,st);assert e['CAP_ARM'] and e['BACKUP_PROVEN'] and e['BUCK_EN']
ex.update(RAW_UV_OK_OD=False,USB_UV_OK_OD=False,BUCK_PG=True);e,st=settle(ex,st);assert e['BUCK_EN'] and not e['VBUS_GOOD_3V3']
ex['MAIN_NOT_READY_OD']=True;e,st=settle(ex,st);assert not e['CAP_ARM'] and not e['BUCK_EN']
ex['MAIN_NOT_READY_OD']=False;e,st=settle(ex,st);assert not e['CAP_ARM'] and not e['BUCK_EN']
violations=[v for sh in json.loads((P/'erc.json').read_text())['sheets'] for v in sh['violations']]
assert not violations,violations
rows=list(csv.DictReader((P/'component-ledger.csv').open()))
physical=[r for r in rows if r['kind']=='physical']
area=sum(float(r['body_area_mm2']) for r in physical)
cellarea=float(next(r['body_area_mm2'] for r in rows if r['reference']=='C_BUF'))
report={'status':'PASS: independent static capture checks; not transient/hardware acceptance','components_in_export':len(comps),'fitted_parts':len(physical),'ICs':len(expected),'nets':len(root.findall('./nets/net')),'source_based_IC_pin_checks':sum(map(len,expected.values())),'all_two_terminal_checks':len(ps),'stable_logic_cases':cases,'max_state_settle_iterations':settle_steps,'temporal_logic_scenarios':'empty-cap USB loader; input-ready charging; fault PG-loss persistence; sticky fault/external-cycle; cap backup/proven-loss/no-rearm PASS','ERC_errors':0,'ERC_warnings':0,'ERC_exclusions':0,'ILIM_IN_mode_pin_model':'U24.5 passive analogue for datasheet-supported IN strap; U6.5 remains output; hard strap independently asserted','power_flags':['external VBUS','external ground','physical diode-OR AON','buck-inductor SYS3V3'],'all_active_control_is_captured':True,'external_boundaries':'existing MCU18/DMX7/factory6 contact maps preserved; USB power contacts only; fault translator unimplemented and not routed','estimated_fitted_body_area_mm2':area,'estimated_body_area_excluding_cell_mm2':area-cellarea,'body_area_exceeds150mm2_power_reservation_before_routing':area-cellarea>150,'footprints_routing_housing_or_USB_qualification':False,'manufacturing_release':False}
(P/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
