"""Separated-power prototype candidate; entirely separate from the active capture.
No resident-loader implementation or hardware qualification is claimed.
"""
from pathlib import Path
import uuid,json
P=Path(__file__).resolve().parent
q=lambda v:json.dumps(str(v))
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-power-service/'+v))
e='(effects (font (size 1 1)))'
lib={};parts=[]
def ic(name,pins):
    # Actual pin numbers/types. Switching/analogue programming outputs remain outputs.
    n=len(pins);h=(n+1)*1.27
    geom=[(pn,str(no),-15.24,h-(i+1)*2.54,0,t) for i,(no,pn,t) in enumerate(pins)]
    lib[name]=(geom,15.24,h)
def part(name,ref,value,nets,x,y):parts.append((name,ref,value,{str(k):v for k,v in nets.items()},x,y))
G='GND_USB'
ic('TPS2553DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'FAULT_N','open_collector'),(5,'ILIM','output'),(6,'OUT','power_out')])
ic('TPS61094DSS',[(1,'OSEL','input'),(2,'MODE','input'),(3,'EN','input'),(4,'VIN','power_in'),(5,'SW','power_out'),(6,'SUP','input'),(7,'PGND','power_in'),(8,'AGND','power_in'),(9,'VOUT','power_out'),(10,'VOUT','passive'),(11,'ICHG','input'),(12,'VCHG','input'),(13,'EP_GND','power_in')])
ic('TPS62132RGT',[(1,'SW','power_out'),(2,'SW','passive'),(3,'SW','passive'),(4,'PG','open_collector'),(5,'FB','input'),(6,'AGND','power_in'),(7,'FSW','input'),(8,'DEF','input'),(9,'SS_TR','input'),(10,'AVIN','power_in'),(11,'PVIN','power_in'),(12,'PVIN','power_in'),(13,'EN','input'),(14,'VOS','input'),(15,'PGND','power_in'),(16,'PGND','power_in'),(17,'EP_GND','power_in')])
ic('TPS7A0225DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')])
ic('TLV3012BDCK',[(1,'OUT','output'),(2,'V_MINUS','power_in'),(3,'IN_PLUS','input'),(4,'IN_MINUS','input'),(5,'REF','output'),(6,'V_PLUS','power_in')])
ic('TPS3700DDC',[(1,'OUTA','open_collector'),(2,'GND','power_in'),(3,'INA_PLUS','input'),(4,'INB_MINUS','input'),(5,'VDD','power_in'),(6,'OUTB','open_collector')])
ic('TPS2116DRL',[(1,'GND','power_in'),(2,'VOUT','power_out'),(3,'VIN1','power_in'),(4,'PR1','input'),(5,'MODE','input'),(6,'VIN2','power_in'),(7,'VOUT','passive'),(8,'ST','open_collector')])
ic('TPS3839DBZ',[(1,'GND','power_in'),(2,'RESET_N','output'),(3,'VDD','power_in')])
ic('TPS3831DQN',[(1,'RESET_N','output'),(2,'MR_N','input'),(3,'GND','power_in'),(4,'VDD','power_in'),(5,'EP','passive')])
ic('SN74LVC1G74DCU',[(1,'CLK','input'),(2,'D','input'),(3,'Q_N','output'),(4,'GND','power_in'),(5,'Q','output'),(6,'CLR_N','input'),(7,'PRE_N','input'),(8,'VCC','power_in')])
for n in ['SN74LVC2G08DCU','SN74LVC2G32DCU']:ic(n,[(1,'1A','input'),(2,'1B','input'),(3,'2Y','output'),(4,'GND','power_in'),(5,'2A','input'),(6,'2B','input'),(7,'1Y','output'),(8,'VCC','power_in')])
ic('SN74LVC1G04DCK',[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')])
ic('AT25SF161B_MHB',[(1,'CS_N','input'),(2,'SO','tri_state'),(3,'WP_N','input'),(4,'GND','power_in'),(5,'SI','input'),(6,'SCK','input'),(7,'HOLD_N','input'),(8,'VCC','power_in'),(9,'EP_NOT_ELECTRICALLY_CONNECTED','passive')])
usb=[]
for side in ['A','B']:
 for i in range(1,13):
  name='GND' if i in (1,12) else 'VBUS' if i in (4,9) else 'CC'+('1' if side=='A' else '2') if i==5 else 'UNUSED_DATA'
  usb.append((side+str(i),name,'passive'))
ic('USB_C_POWER_ONLY_BOUNDARY',usb)
mcunames=[('SYS_3V3','power_in'),(G,'power_in'),('MCU_DMX_TX','output'),('MCU_DMX_RX','input'),('MCU_DE_REQUEST','output'),('MCU_RE_N','output'),('MCU_ISO_REQUEST','output'),('SPI_CS_N','output'),('SPI_MOSI','output'),('SPI_SCK','output'),('SPI_MISO','input'),('VBUS_GOOD_3V3','input'),('SERVICE_N_DISTINCT_GPIO','input'),('ROM_BOOT_STRAP','input'),('RESET_OK','input'),('TMSC','bidirectional'),('TCKC','input'),('BUCK_PG','input')]
ic('CC1352_MCU_RF_BOUNDARY',[(i+1,n,t) for i,(n,t) in enumerate(mcunames)])
dmxnames=['SYS_3V3',G,'MCU_DMX_TX','DMX_DE_SAFE','MCU_RE_N','MCU_DMX_RX','DMX_POWER_EN']
ic('ISOW1412_SHEET_BOUNDARY',[(i+1,n,'power_in' if i<2 else 'output' if i==5 else 'input') for i,n in enumerate(dmxnames)])
ic('FACTORY_PADS',[(i+1,n,'passive') for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])])
for name in ['R','C','L','D','SW_NO']:
 lib[name]=([('K' if name=='D' else '1','1',0,5.08,270,'passive'),('A' if name=='D' else '2','2',0,-5.08,90,'passive')],1.27,2.54)
lib['DERIVED_POWER'] = ([('PWR','1',0,-5.08,90,'power_out')],2.54,2.54)

def definition(name):
    pins,w,h=lib[name]
    lines=[f'(symbol {q(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 {h+2.54} 0) {e}) (property "Value" {q(name)} (at 0 {-h-2.54} 0) {e})',f'(symbol {q(name+"_0_1")} (rectangle (start {-w+2.54 if w>2 else -w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background))))',f'(symbol {q(name+"_1_1")}']
    for pn,no,x,y,a,t in pins:lines.append(f'(pin {t} line (at {x} {y} {a}) (length 2.54) (name {q(pn)} {e}) (number {q(no)} {e}))')
    result=''.join(lines)+'))'
    if name in ('C','SW_NO'):
        # Replace only the graphic primitive, preserving the enclosing unit.
        old=f'(rectangle (start {-w+2.54 if w>2 else -w} {h}) (end {w} {-h}) (stroke (width .254) (type default)) (fill (type background)))'
        segs=[((0,2.54),(0,.508)),((-1.524,.508),(1.524,.508)),((-1.524,-.508),(1.524,-.508)),((0,-.508),(0,-2.54))] if name=='C' else [((0,2.54),(0,1.27)),((0,1.27),(1.27,-1.27)),((0,-1.27),(0,-2.54))]
        draw=''.join(f'(polyline (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width .254) (type default)) (fill (type none)))' for a,b in segs)
        result=result.replace(old,draw)
    return result

# Candidate only: no writes outside P. Source maps in verify.py are independent.
import csv
uid=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'nova-separated-candidate/'+v))
parts=[]; metadata={}; sheet='main'
def add(n,r,v,nets,area,kind='physical',note=''):
    part(n,r,v,nets,0,0)
    metadata[r]={'sheet':sheet,'body_mm2':area,'kind':kind,'note':note}
def two(n,r,v,a,b,area=.5,note=''):
    add(n,r,v,{1:a,2:b},area,note=note)
def resistor(r,ohms,a,b,size='0402'):
    # Vishay TNPW e3 ordering: B=0.1%, E=25ppm/K, ED=0402, EA=0603/0805.
    if size=='0402' and ohms>100000:size='0805'
    if ohms<1000:code=f'{ohms:g}R'
    elif ohms<1000000:
        k=ohms/1000
        code=(f'{k:g}K' if k>=100 else f'{k:.3g}'.replace('.', 'K'))
        if 'K' not in code:code+='K'
        while len(code)<4:code+='0'
    else:raise ValueError(ohms)
    mpn='TNPW'+size+code+'BE'+('ED' if size=='0402' else 'EA')
    two('R',r,f'{mpn} {ohms:g}ohm 0.1% 25ppm',a,b,{'0402':.5,'0603':1.28,'0805':2.5}[size])
def cap(r,which,a,b=G):
    specs={'100n':('GRM155R71E104KE14D 100nF 25V X7R',.5),
           '1u':('GRM155R61C105KA12D 1uF 16V X5R',.5),
           '10u':('GRM21BR71A106KE51L 10uF 10V X7R',2.5)}
    v,area=specs[which];two('C',r,v,a,b,area)
# New sourced parts, physical pin numbers.
# Pin5 is a programmable analogue current-source terminal (datasheet labels O).
# IN-strapped mode is explicitly permitted on pp7/15. Model ONLY that mode as
# passive analogue configuration; independent checks require IN tie and50..100mA.
# It is not a digital output tied against another voltage source.
ic('TPS2553DBV_ILIM_IN',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'FAULT_N','open_collector'),(5,'ILIM_IN_STRAP_ANALOG','passive'),(6,'OUT','power_out')])
ic('BQ25173DSG',[(1,'IN','power_in'),(2,'ISET','input'),(3,'CE_N_ENABLE_LOW','input'),(4,'GND','power_in'),(5,'STAT','open_collector'),(6,'PG_N','open_collector'),(7,'FB','input'),(8,'OUT','power_out'),(9,'EP_GND','power_in')])
ic('TPS61023DRL',[(1,'FB','input'),(2,'EN','input'),(3,'VIN','power_in'),(4,'GND','power_in'),(5,'SW','power_out'),(6,'VOUT','power_out')])
ic('SN74LVC2G02DCU',[(1,'1A','input'),(2,'1B','input'),(3,'2Y','output'),(4,'GND','power_in'),(5,'2A','input'),(6,'2B','input'),(7,'1Y','output'),(8,'VCC','power_in')])
for n in ['SN74LVC2G04DCK','SN74LVC2G17DCK']:
    ic(n,[(1,'1A','input'),(2,'GND','power_in'),(3,'2A','input'),(4,'2Y','output'),(5,'VCC','power_in'),(6,'1Y','output')])
# Real source terminal, not an IC supplying phantom power. Shell is explicit NC
# pending parent mechanical/ESD capture, not a hidden supply return.
add('USB_C_POWER_ONLY_BOUNDARY','J_USB','CX70M-24P1 power contacts; shell integration open',
 {no:G if pn=='GND' else 'VBUS_RAW' if pn=='VBUS' else pn if pn.startswith('CC') else None for no,pn,t in usb},0,'external_interface')
add('TPS2553DBV','U6','TPS2553DBVR',{1:'VBUS_RAW',2:G,3:'MAIN_INPUT_EN',4:'INPUT_FAULT_N',5:'ILIM_SET',6:'LIMITED_5V'},4.64)
add('TPS2553DBV_ILIM_IN','U24','TPS2553DBVR',{1:'LIMITED_5V',2:G,3:'CHG_BRANCH_EN',4:'INPUT_FAULT_N',5:'LIMITED_5V',6:'CHG_IN'},4.64,note='ILIM directly to IN:50..100mA DC, faults wired-OR to U6 fault')
add('BQ25173DSG','U3','BQ25173DSGR',{1:'CHG_IN',2:'ICHG_PIN',3:'CHARGE_DISABLE',4:G,5:None,6:None,7:'VCHG_FB',8:'CAP_POS',9:G},4)
add('TPS61023DRL','U5','TPS61023DRLR',{1:'BOOST_FB',2:'CAP_BOOST_EN',3:'CAP_POS',4:G,5:'BOOST_SW',6:'BOOST_3V9'},1.92)
add('TPS2116DRL','U19','TPS2116DRLR',{1:G,2:'BACKUP_RAW',3:'LIMITED_5V',4:'USB_VALID',5:'AON_2V5',6:'BOOST_3V9',7:'BACKUP_RAW',8:None},3.36)
add('TPS62132RGT','U4','TPS62132RGTR',{1:'BUCK_SW',2:'BUCK_SW',3:'BUCK_SW',4:'BUCK_PG',5:G,6:G,7:G,8:G,9:'BUCK_SS',10:'BACKUP_RAW',11:'BACKUP_RAW',12:'BACKUP_RAW',13:'BUCK_EN',14:'SYS_3V3',15:G,16:G,17:G},9)
add('TPS7A0225DBV','U7','TPS7A0225PDBVR',{1:'AON_RAW',2:G,3:'AON_RAW',4:None,5:'AON_2V5'},4.64)
add('TPS3839DBZ','U9','TPS3839G25DBZR',{1:G,2:'AON_OK',3:'AON_2V5'},3.625)
for ref,ina,outa,inb,outb in [
 ('U8','CAP_SENSE','CAP_OK_OD','CAP_START_SENSE','CAP_START_N_OD'),
 ('U10','USB_SENSE','USB_UV_OK_OD','MAIN_SENSE','MAIN_NOT_READY_OD'),
 ('U20','RAW_SENSE','RAW_UV_OK_OD','RAW_PRESENT_SENSE','RAW_ABSENT_OD'),
 ('U21','CHGIN_SENSE','CHGIN_OK_OD','BOOST_SENSE','BOOST_NOT_READY_OD')]:
    add('TPS3700DDC',ref,'TPS3700DDCR',{1:outa,2:G,3:ina,4:inb,5:'AON_2V5',6:outb},4.64)
add('TPS3831DQN','U16','TPS3831K33DQNR',{1:'RESET_OK',2:'MANUAL_RESET_N',3:G,4:'SYS_3V3',5:G},1)
add('AT25SF161B_MHB','U2','AT25SF161B-MHB-T',{1:'SPI_CS_N',2:'SPI_MISO',3:'FLASH_WP_N',4:G,5:'SPI_MOSI',6:'SPI_SCK',7:'FLASH_HOLD_N',8:'SYS_3V3',9:G},30)
add('CC1352_MCU_RF_BOUNDARY','X_MCU','UNCHANGED MCU interface; boundary numbers are not package pins',{i+1:n for i,(n,t) in enumerate(mcunames)},0,'external_interface')
add('ISOW1412_SHEET_BOUNDARY','X_DMX','UNCHANGED isolated DMX sheet contract',{i+1:n for i,n in enumerate(dmxnames)},0,'external_interface')
add('FACTORY_PADS','J_FACTORY','VREF sense; no power injection',{i+1:n for i,n in enumerate(['SYS_3V3',G,'TMSC','TCKC','MANUAL_RESET_N','ROM_BOOT_STRAP'])},0,'external_interface')
# Raw AON current bounded by a resistor independent of the main limiter.
resistor('R_AON_USB',330,'VBUS_RAW','AON_USB_LIMITED',size='0603')
two('D','D_AON_USB','BAT54H,115','AON_RAW','AON_USB_LIMITED',3.6)
two('D','D_AON_BUF','BAT54H,115','AON_RAW','BOOST_3V9',3.6)
resistor('R_ILIM',61900,'ILIM_SET',G)
resistor('R_CC1',5100,'CC1',G);resistor('R_CC2',5100,'CC2',G)
resistor('R_RAW_BLEED',10000,'VBUS_RAW',G)
resistor('R_LIMIT_BLEED',100000,'LIMITED_5V',G)
resistor('R_BOOST_BLEED',100000,'BOOST_3V9',G)
resistor('R_ICHG_FILTER',100,'ICHG_PIN','ICHG_FILTER')
resistor('R_ICHG',11900,'ICHG_FILTER',G)
cap('C_ICHG','100n','ICHG_FILTER') # Prototype RC allocation; sum DC resistance12.0k.
resistor('R_VCHG_TOP',22500,'CAP_POS','VCHG_FB')
resistor('R_VCHG_BOTTOM',10000,'VCHG_FB',G)
resistor('R_BOOST_TOP',562000,'BOOST_3V9','BOOST_FB')
resistor('R_BOOST_BOTTOM',100000,'BOOST_FB',G)
for pre,top,rail,sense in [
 ('CAP',32400,'CAP_POS','CAP_SENSE'),('CAP_START',45300,'CAP_POS','CAP_START_SENSE'),
 ('USB',93100,'LIMITED_5V','USB_SENSE'),('MAIN',80600,'BACKUP_RAW','MAIN_SENSE'),
 ('RAW',89800,'VBUS_RAW','RAW_SENSE'),('RAW_PRESENT',10000,'VBUS_RAW','RAW_PRESENT_SENSE'),
 ('CHGIN',80600,'CHG_IN','CHGIN_SENSE'),('BOOST_MON',80600,'BOOST_3V9','BOOST_SENSE')]:
    resistor('R_'+pre+'_TOP',top,rail,sense);resistor('R_'+pre+'_BOTTOM',10000,sense,G)
# Exact passive selections, effective C is an explicit qualification allocation.
cap('C_RAW','100n','VBUS_RAW')
for pre,rail,n in [('LIMIT','LIMITED_5V',6),('BACKUP','BACKUP_RAW',2),
 ('BUCK_IN','BACKUP_RAW',2),('SYS','SYS_3V3',4),('BOOST_OUT','BOOST_3V9',2),('BOOST_IN','CAP_POS',2)]:
    for i in range(n):cap(f'C_{pre}{i+1}','10u',rail)
for pre,rail,n in [('CHG_IN','CHG_IN',2),('AON_IN','AON_RAW',2),('AON_OUT','AON_2V5',2),('FLASH_BULK','SYS_3V3',1)]:
    for i in range(n):cap(f'C_{pre}{i+1}','1u',rail)
cap('C_SS','100n','BUCK_SS')
cap('C_FLASH','100n','SYS_3V3')
# Existing2.2uH lies within TPS61023 effective0.37..2.9uH; current/ESR to qualify.
two('L','L_BOOST','XGL4020-222MEC 2.2uH 20%','BOOST_SW','CAP_POS',18.49)
two('L','L_BUCK','XFL4020-222MEC 2.2uH 20%','BUCK_SW','SYS_3V3',18.49)
two('C','C_BUF','HV1325-2R7156-R 15F 2.7V','CAP_POS',G,143.139,note='Existing cell retained:13.5mm maximum diameter;28.4mm maximum height per manufacturer current SKU/spec; separate mechanical fit gate')
for r,ohms,a,b in [('R_BUCK_PG',4700,'SYS_3V3','BUCK_PG'),('R_MR',10000,'SYS_3V3','MANUAL_RESET_N'),
 ('R_SERVICE',10000,'SYS_3V3','SERVICE_N_DISTINCT_GPIO'),('R_ROM',10000,'SYS_3V3','ROM_BOOT_STRAP'),
 ('R_DE',100000,'MCU_DE_REQUEST',G),('R_ISO',100000,'MCU_ISO_REQUEST',G),('R_RE',10000,'SYS_3V3','MCU_RE_N'),
 ('R_CS',10000,'SYS_3V3','SPI_CS_N'),('R_WP',10000,'SYS_3V3','FLASH_WP_N'),('R_HOLD',10000,'SYS_3V3','FLASH_HOLD_N'),
 ('R_SCK',100000,'SPI_SCK',G),('R_MOSI',100000,'SPI_MOSI',G)]:resistor(r,ohms,a,b)
two('SW_NO','S_SERVICE','PCB two-pad SERVICE contact, normally open','SERVICE_N_DISTINCT_GPIO',G,1.0)
two('SW_NO','S_RESET','PCB two-pad RESET contact, normally open','MANUAL_RESET_N',G,1.0)
metadata['S_SERVICE']['kind']='pcb_feature'
metadata['S_RESET']['kind']='pcb_feature'
# Domain-interface functionality remains on3.3V, so no AON-high injection at outputs.
# Their AND operations are added below with an explicit supply.
sheet='control'
and_ops=[('AON_OK','NO_FAULT','CONTROL_OK'),('RAW_UV_OK','AON_OK','FAULT_VALID'),
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
for i in range(0,len(and_ops),2):
    group=and_ops[i:i+2];nets={4:G,8:'AON_2V5'}
    for j in range(2):
        a,b,out=group[j] if j<len(group) else (G,G,None)
        for pin,net in zip((1,2,7) if j==0 else (5,6,3),(a,b,out)):nets[pin]=net
    add('SN74LVC2G08DCU','U'+str(30+i//2),'SN74LVC2G08DCUR',nets,4.6)
or_ops=[('RAW_ABSENT','AON_BAD','FAULT_RESET'),('CAP_BASE_BAD','LOSS_CUTOFF','CAP_RESET'),('USB_VALID','BACKUP_PATH','PATH_AVAILABLE')]
for i in range(0,len(or_ops),2):
    nets={4:G,8:'AON_2V5'}
    for j in range(2):
        a,b,out=or_ops[i+j] if i+j<len(or_ops) else (G,G,None)
        for pin,net in zip((1,2,7) if j==0 else (5,6,3),(a,b,out)):nets[pin]=net
    add('SN74LVC2G32DCU','U'+str(42+i//2),'SN74LVC2G32DCUR',nets,4.6)
# NOR SR latches: Q=NOR(reset,Qbar); Qbar=NOR(set,Q). No unimplemented state box.
for ref,setnet,resetnet,out,bar in [
 ('U22','FAULT_SET','FAULT_RESET','FAULT_Q','FAULT_BAR'),
 ('U11','CAP_SET','CAP_RESET','CAP_ARM','CAP_BAR'),
 ('U23','PROVEN_SET','CAP_ARM_NOT','BACKUP_PROVEN','PROVEN_BAR'),
 ('U25','CHG_SET','CHG_RESET','CHG_ARM','CHG_BAR')]:
    add('SN74LVC2G02DCU',ref,'SN74LVC2G02DCUR',{1:resetnet,2:bar,7:out,5:setnet,6:out,3:bar,4:G,8:'AON_2V5'},4.6)
inv_ops=[('AON_OK','AON_BAD'),('FAULTS_OK','FAULT_REQUEST'),('FAULT_Q','NO_FAULT'),
 ('MAIN_NOT_READY','MAIN_READY'),('CAP_START_N','CAP_START_OK'),('BOOST_NOT_READY','BOOST_READY'),
 ('BOOST_AND_MAIN','BACKUP_INVALID'),('USB_VALID','USB_INVALID'),('CAP_BASE_OK','CAP_BASE_BAD'),
 ('CAP_ARM','CAP_ARM_NOT'),('CHG_ALLOWED','CHARGE_DISABLE'),('CHG_HOLD_OK','CHG_RESET')]
for i in range(0,len(inv_ops),2):
    nets={2:G,5:'AON_2V5'}
    for j in range(2):
        a,out=inv_ops[i+j] if i+j<len(inv_ops) else (G,None)
        nets[1 if j==0 else 3]=a;nets[6 if j==0 else 4]=out
    add('SN74LVC2G04DCK','U'+str(50+i//2),'SN74LVC2G04DCKR',nets,2.5)
buf_ops=[('RAW_UV_OK_OD','RAW_UV_OK'),('RAW_ABSENT_OD','RAW_ABSENT'),
 ('USB_UV_OK_OD','USB_UV_OK'),('MAIN_NOT_READY_OD','MAIN_NOT_READY'),
 ('CAP_OK_OD','CAP_OK'),('CAP_START_N_OD','CAP_START_N'),
 ('CHGIN_OK_OD','CHGIN_OK'),('BOOST_NOT_READY_OD','BOOST_NOT_READY'),
 ('INPUT_FAULT_N','FAULTS_OK'),('BUCK_PG','BUCK_PG_BUF')]
for i in range(0,len(buf_ops),2):
    nets={2:G,5:'AON_2V5'}
    for j,(a,out) in enumerate(buf_ops[i:i+2]):nets[1 if j==0 else 3]=a;nets[6 if j==0 else 4]=out
    add('SN74LVC2G17DCK','U'+str(60+i//2),'SN74LVC2G17DCKR',nets,2.5)
# Preserve3.3V boundary signals and reset/service staging.
for ref,gates in [('U17',[('BUCK_EN','RESET_OK','SYS_READY'),('MCU_DE_REQUEST','SYS_READY','DMX_DE_SAFE')]),
                  ('U18',[('MCU_ISO_REQUEST','SYS_READY','DMX_POWER_EN'),('USB_VALID','SYS_READY','VBUS_GOOD_3V3')])]:
    nets={4:G,8:'SYS_3V3'}
    for j,(a,b,out) in enumerate(gates):
        for pin,net in zip((1,2,7) if j==0 else (5,6,3),(a,b,out)):nets[pin]=net
    add('SN74LVC2G08DCU',ref,'SN74LVC2G08DCUR',nets,4.6)
for a,b in buf_ops:
    if a!='BUCK_PG':resistor('R_PU_'+a,47000,'AON_2V5',a)
for net in ('MAIN_INPUT_EN','CHG_BRANCH_EN','CAP_BOOST_EN','BUCK_EN'):
    resistor('R_PD_'+net,47000,net,G)
resistor('R_CE_DEFAULT',100000,'AON_2V5','CHARGE_DISABLE')
# Every physical IC is bypassed on its actual supply, not merely at a boundary.
for name,ref,value,nets,x,y in list(parts):
    if not ref.startswith('U'):continue
    rail='SYS_3V3' if ref in ('U2','U16','U17','U18') else 'AON_2V5' if (
        name.startswith('SN74') or ref in ('U8','U9','U10','U20','U21')) else None
    if rail:
        sheet=metadata[ref]['sheet'];cap('C_'+ref,'100n',rail)
sheet='main'
for net,why in [('VBUS_RAW','External USB/barrel receptacle supply'),(G,'External return'),
 ('AON_RAW','Physical diode OR from resistor-limited raw source or cap boost'),
 ('SYS_3V3','TPS62132 switch output through actual buck inductor')]:
    add('DERIVED_POWER','#FLG'+str(['VBUS_RAW',G,'AON_RAW','SYS_3V3'].index(net)+1),'PHYSICAL POWER SOURCE',{1:net},0,'power_flag',why)
# Place physical ICs first; interfaces remain explicitly outside the power circuitry.
for sh in ('main','control'):
    indices=[i for i,p in enumerate(parts) if metadata[p[1]]['sheet']==sh]
    big=[i for i in indices if parts[i][0] not in ('R','C','L','D','SW_NO','DERIVED_POWER')]
    small=[i for i in indices if i not in big and parts[i][0]!='DERIVED_POWER']
    cols=7 if sh=='main' else 8
    for j,i in enumerate(big):
        n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,(60.96+(j%cols)*111.76) if sh=='main' else (53.34+(j%cols)*101.6),66.04+(j//cols)*99.06)
    y0=66.04+((len(big)+cols-1)//cols)*99.06
    for j,i in enumerate(small):
        n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,30.48+(j%13)*60.96,y0+(j//13)*30.48)
    for j,i in enumerate(i for i in indices if parts[i][0]=='DERIVED_POWER'):
        n,r,v,ns,_,_=parts[i];parts[i]=(n,r,v,ns,50.8+j*177.8,563.88)
assert len({p[1] for p in parts})==len(parts), 'Duplicate physical reference'
root=uid('root');child=uid('control-root');sheetid=uid('control-sheet')
used={p[0] for p in parts}
net_by_sheet={sh:{n for p in parts if metadata[p[1]]['sheet']==sh for n in p[3].values() if n is not None} for sh in ('main','control')}
cross=net_by_sheet['main'] & net_by_sheet['control']
for sh,filename,docuid in [('main','separated-candidate',root),('control','control',child)]:
    s=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{docuid}") (paper "A1") (title_block (title "NOVA separated power prototype - {sh}") (rev "SEP-PROTOTYPE-1")) (lib_symbols']
    for n in sorted(used):s.append(definition(n).replace('(symbol '+q(n)+' ','(symbol '+q('SEP:'+n)+' ',1))
    s.append(')')
    for name,ref,value,nets,x,y in parts:
        if metadata[ref]['sheet']!=sh:continue
        pins,w,h=lib[name];style='(effects (font (size 0.8 0.8)))'
        # Keep full exact MPN in Value and CSV; small type prevents passive overlap.
        display=value if len(value)<45 else value.split(' ')[0]
        s.append(f'(symbol (lib_id "SEP:{name}") (at {x} {y} 0) (unit 1) (in_bom {"no" if ref.startswith("#") or metadata[ref]["kind"]=="external_interface" else "yes"}) (on_board {"no" if ref.startswith("#") or metadata[ref]["kind"]=="external_interface" else "yes"}) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y-h-2.54} 0) {style}) (property "Value" {q(value)} (at {x} {y+h+2.54} 0) {style})')
        for pn,no,px,py,a,t in pins:s.append(f'(pin {q(no)} (uuid "{uid(ref+no)}"))')
        path='/'+root if sh=='main' else '/'+root+'/'+sheetid
        s.append(f'(instances (project "separated-candidate" (path "{path}" (reference {q(ref)}) (unit 1)))))')
        for pn,no,px,py,a,t in pins:
            xx,yy=round(x+px,4),round(y-py,4);net=nets[no]
            if net is None:s.append(f'(no_connect (at {xx} {yy}) (uuid "{uid(ref+no+"nc")}"))');continue
            dx,dy={0:(-5.08,0),270:(0,-5.08),90:(0,5.08)}[a];ex,ey=round(xx+dx,4),round(yy+dy,4)
            s.append(f'(wire (pts (xy {xx} {yy}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+no+"w")}"))')
            label='global_label' if net in cross else 'label'
            shape=' (shape bidirectional)' if label=='global_label' else ''
            s.append(f'({label} {q(net)}{shape} (at {ex} {ey} 0) (effects (font (size 0.8 0.8))) (uuid "{uid(ref+no+"l")}"))')
    if sh=='main':
        s.append(f'(sheet (at 670.56 294.64) (size 137.16 20.32) (fields_autoplaced yes) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid "{sheetid}") (property "Sheetname" "Control / real components" (at 670.56 293.37 0) (effects (font (size 1 1)) (justify left bottom))) (property "Sheetfile" "control.kicad_sch" (at 670.56 316.23 0) (effects (font (size 1 1)) (justify left top))) (instances (project "separated-candidate" (path "/{root}" (page "2")))))')
        notes=['SEPARATE PROTOTYPE: passive Rd; no CC decoder or new1.5A source restriction. 500mA engineering basis; not USB qualification.',
          'USB main -> mux -> buck. Charger branch ILIM=IN50..100mA; nominal25mA. Boost fed ONLY by15F cap.',
          'Independent resistor-limited raw AON. Every power/control path captured. INPUT_FAULT_N stays local; MCU translator NOT implemented.',
          'Effective-C, input transients, bootstrap/boost PFM/current, cap ESR and thermal are BENCH GATES; not manufacturing release.']
    else:
        notes=['FAULT SR latch holds all converter/load enables off after switch fault; raw-AON remains powered until external cycle.',
          'CAP SR latch arms only with qualified USB and cap-start. Loaded-cap UVLO or proven backup loss disarms; cap rebound cannot rearm.',
          'No status blanking. USB status senses RAW + LIMITED_5V, never the cap-fed common rail alone.',
          'Schmitt buffers condition all open-drain monitor inputs. Source/power-off/propagation timing remains physical validation.']
    for i,n in enumerate(notes):s.append(f'(text {q(n)} (at 20.32 {325.12+i*3.81} 0) (effects (font (size 0.8 0.8)) (justify left)) (uuid "{uid(sh+"note"+str(i))}"))')
    s.append(')');(P/(filename+'.kicad_sch')).write_text('\n'.join(s)+'\n')
(P/'separated-candidate.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(definition(n) for n in sorted(used))+'\n)\n')
(P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "SEP") (type "KiCad") (uri "${KIPRJMOD}/separated-candidate.kicad_sym") (options "") (descr "Source-backed separated power prototype symbols")))\n')
(P/'separated-candidate.kicad_pro').write_text('{"meta":{"filename":"separated-candidate.kicad_pro","version":1}}\n')
with (P/'component-ledger.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['reference','value','sheet','kind','body_area_mm2','note'])
    for n,r,v,ns,x,y in sorted(parts,key=lambda p:p[1]):
        m=metadata[r];w.writerow([r,v,m['sheet'],m['kind'],m['body_mm2'],m['note']])
print(json.dumps({'parts':len(parts),'physical':sum(m['kind']=='physical' for m in metadata.values()),'main_components':sum(m['sheet']=='main' for m in metadata.values()),'control_components':sum(m['sheet']=='control' for m in metadata.values()),'cross_sheet_nets':len(cross)},indent=2))
